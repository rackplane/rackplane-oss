# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Authentication API Endpoints
User login and authentication management

This module provides authentication endpoints for user login and token management.
All endpoints use OAuth2 password flow for compatibility with standard OAuth2 clients.

Endpoints:
- POST /api/v1/auth/login: User login (returns JWT token)
- GET /api/v1/auth/me: Get current user information
- POST /api/v1/auth/logout: Logout (client-side token removal)

Security:
- Passwords are verified using bcrypt
- JWT tokens include tenant_id for multi-tenant isolation
- Tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES
- All endpoints require authentication except /login
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_user_by_username
)
from app.services.audit_service import log_security_event
from app.core.config import settings
from app.schemas.user import Token, UserResponse
from app.schemas.print_job import AgentLoginRequest, AgentLoginResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request = None,  # Optional to avoid breaking existing calls if any
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token with tenant_id.
    
    OAuth2 compatible endpoint that accepts username and password via form data.
    Returns a JWT access token that includes the user's tenant_id for automatic
    tenant isolation in subsequent requests.
    
    Args:
        form_data: OAuth2 password request form (username, password)
        db: Database session
        
    Returns:
        Token object with access_token and token_type
        
    Raises:
        HTTPException: 401 if authentication fails
        
    Example:
        POST /api/v1/auth/login
        Content-Type: application/x-www-form-urlencoded
        username=admin&password=secret
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Log failure (non-blocking - don't let audit errors prevent login failure response)
        ip_address = request.client.host if request.client else "unknown"
        logger.warning(
            f"Login failed: username={form_data.username}, ip={ip_address}"
        )
        try:
            attempted_user = get_user_by_username(db, form_data.username)
            tenant_id = attempted_user.tenant_id if attempted_user else 0
            
            log_security_event(
                db=db,
                action="login_failed",
                username=form_data.username,
                tenant_id=tenant_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                notes="Invalid credentials"
            )
        except Exception as e:
            logger.warning(f"Failed to log login failure: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log success (non-blocking - don't let audit errors prevent successful login)
    try:
        log_security_event(
            db=db,
            action="login_success",
            user_id=user.id,
            username=user.username,
            tenant_id=user.tenant_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            notes="Login successful"
        )
    except Exception as e:
        logger.warning(f"Failed to log login success: {e}")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Include role in token for authorization checks
    effective_role = user.effective_role
    
    # Log successful login with user details
    ip_address = request.client.host if request.client else "unknown"
    logger.info(
        f"Login successful: username={user.username}, user_id={user.id}, "
        f"tenant_id={user.tenant_id}, role={effective_role.value}, "
        f"ip={ip_address}"
    )
    
    access_token = create_access_token(
        data={
            "sub": user.username,
            "tenant_id": user.tenant_id,
            "role": effective_role.value
        },
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """
    Get current authenticated user information
    """
    return current_user


@router.patch("/me/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's UI preferences.
    
    Saves UI preferences like navigation bar layout, theme settings, etc.
    These preferences persist across login sessions and devices.
    
    Args:
        preferences: Dict containing UI preferences to save
        
    Returns:
        Updated preferences dict
        
    Example:
        PATCH /api/v1/auth/me/preferences
        {"nav_items": ["dashboard", "inventory", "storage"]}
    """
    # Merge with existing preferences (don't overwrite unrelated keys)
    existing = current_user.ui_preferences or {}
    existing.update(preferences)
    current_user.ui_preferences = existing
    db.commit()
    db.refresh(current_user)
    
    return {"status": "ok", "ui_preferences": current_user.ui_preferences}


@router.post("/agent-login", response_model=AgentLoginResponse)
async def agent_login(
    request: AgentLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate a print agent and return a JWT token.
    
    Print agents use this endpoint to authenticate and receive a token
    for accessing print job endpoints. The agent_id and agent_secret are
    required for authentication.
    
    Security:
    - agent_secret is validated against stored bcrypt hash
    - If agent doesn't have a secret_hash set, the provided secret is stored (first-time setup)
    - Subsequent logins require matching secret
    
    Args:
        request: Agent login request with agent_id, agent_secret, and optional metadata
        db: Database session
        
    Returns:
        AgentLoginResponse with access_token and agent_id
        
    Raises:
        HTTPException: 401 if authentication fails (invalid secret)
        
    Example:
        POST /api/v1/auth/agent-login
        {
            "agent_id": "printer-agent-001",
            "agent_secret": "secure-secret-key",
            "agent_name": "Main Office Printer",
            "agent_version": "1.0.0"
        }
    """
    from app.models.print_job import PrintAgent
    from app.core.auth import get_password_hash, verify_password
    from datetime import datetime
    
    # Find existing agent or create new one
    # CRITICAL: Skip tenant filter during authentication (similar to User queries)
    # We don't have tenant_id yet - we'll get it from the agent record after authentication
    agent = db.query(PrintAgent).execution_options(skip_tenant_filter=True).filter(
        PrintAgent.agent_id == request.agent_id
    ).first()
    
    if not agent:
        # Create new agent record with secret hash
        # NOTE: tenant_id will be auto-set by before_flush event if available in context
        # If not available, we require tenant_id to be provided or agents must be pre-registered
        from app.core.tenant import get_current_tenant_id
        current_tenant_id = get_current_tenant_id()
        
        agent = PrintAgent(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            agent_version=request.agent_version,
            is_active=True,
            secret_hash=get_password_hash(request.agent_secret),  # Store secret on creation
            last_heartbeat=datetime.utcnow()
        )
        # Set tenant_id if available in context (from authenticated request creating agent)
        # If not available, before_flush will try to set it, but if still None, commit will fail
        # This means agents should be created through authenticated endpoints, not agent_login
        if current_tenant_id:
            agent.tenant_id = current_tenant_id
        
        db.add(agent)
        try:
            db.commit()
            db.refresh(agent)
        except Exception as e:
            db.rollback()
            # If commit failed due to missing tenant_id, provide helpful error
            if "tenant_id" in str(e).lower() or "null" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent registration requires tenant context. "
                           "Agents must be created through an authenticated endpoint first, "
                           "or agent_login must be called from an authenticated context."
                )
            raise
    else:
        # Existing agent: validate secret
        if not agent.secret_hash:
            # First-time setup: store provided secret
            agent.secret_hash = get_password_hash(request.agent_secret)
            db.commit()
            db.refresh(agent)
        elif not verify_password(request.agent_secret, agent.secret_hash):
            # Invalid secret
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent secret"
            )
        
        # Update agent metadata and heartbeat
        if request.agent_name:
            agent.agent_name = request.agent_name
        if request.agent_version:
            agent.agent_version = request.agent_version
        agent.last_heartbeat = datetime.utcnow()
        db.commit()
        db.refresh(agent)
    
    # Create access token for agent
    # Agents get a longer-lived token (24 hours) since they run continuously
    access_token_expires = timedelta(hours=24)
    
    # CRITICAL: Include tenant_id in token payload for tenant isolation
    # Without this, get_current_user cannot set tenant context, causing
    # fail-closed tenant isolation to reject tenant-scoped queries
    if not agent.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent must have tenant_id set. Agents must be created through an authenticated endpoint first."
        )
    
    access_token = create_access_token(
        data={
            "sub": request.agent_id,
            "type": "agent",  # Mark as agent token
            "agent_id": request.agent_id,
            "tenant_id": agent.tenant_id  # Include tenant_id for tenant isolation
        },
        expires_delta=access_token_expires
    )
    
    return AgentLoginResponse(
        access_token=access_token,
        token_type="bearer",
        agent_id=request.agent_id,
        expires_in=int(access_token_expires.total_seconds())
    )


@router.get("/demo-login", response_model=Token)
async def demo_login(
    key: str,
    tenant: str = "datacenter",
    db: Session = Depends(get_db)
):
    """
    Auto-login for demo environments using a shared demo key.
    
    This endpoint allows automatic login to demo instances without requiring
    username/password. The demo key is configured via DEMO_LOGIN_KEY environment variable.
    
    Supports multiple demo tenants for showcasing different industry verticals:
    - datacenter: Velocity Technologies (IT infrastructure)
    - healthcare: City General Hospital (medical supplies)
    - warehouse: FastShip Fulfillment (logistics)
    
    Security:
    - Only works if DEMO_LOGIN_KEY is set
    - Key must match exactly
    - Token expires after ACCESS_TOKEN_EXPIRE_MINUTES
    
    Args:
        key: Demo login key (must match DEMO_LOGIN_KEY)
        tenant: Demo tenant to login to (datacenter, healthcare, warehouse)
        db: Database session
        
    Returns:
        Token object with access_token and token_type
        
    Raises:
        HTTPException: 401 if key is invalid or demo login is disabled
        HTTPException: 404 if no demo user found
        
    Example:
        GET /api/v1/auth/demo-login?key=your-demo-key-here&tenant=healthcare
    """
    from app.models.user import User
    from app.models.tenant import Tenant
    
    # Check if demo login feature is enabled
    demo_enabled = getattr(settings, 'DEMO_LOGIN_ENABLED', False)
    if not demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo login is not available"
        )
    
    # Check if demo key is configured
    demo_key = getattr(settings, 'DEMO_LOGIN_KEY', None)
    if not demo_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo login is not configured"
        )
    # Validate key
    if key != demo_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo key"
        )
    
    # Valid verticals - explicit validation
    VALID_VERTICALS = {"datacenter", "healthcare", "warehouse"}
    vertical_lower = tenant.lower() if tenant else "datacenter"
    
    # Validate vertical parameter explicitly
    if vertical_lower not in VALID_VERTICALS:
        logger.warning(f"Invalid vertical requested: {tenant}, valid options: {VALID_VERTICALS}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid vertical '{tenant}'. Valid options: {', '.join(sorted(VALID_VERTICALS))}"
        )
    
    vertical_pack = vertical_lower
    
    # Find tenant with matching vertical_pack
    target_tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
        Tenant.vertical_pack == vertical_pack,
        Tenant.is_active == True
    ).first()
    
    # Fallback to datacenter (tenant 1) if not found
    if not target_tenant:
        target_tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
            Tenant.id == 1
        ).first()
    
    if not target_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No demo tenant found for vertical '{tenant}'"
        )
    
    target_tenant_id = target_tenant.id
    
    # Find first admin user in this tenant
    user = db.query(User).execution_options(skip_tenant_filter=True).filter(
        User.tenant_id == target_tenant_id,
        User.role.in_(['tenant_admin', 'admin']),
        User.is_active == True
    ).order_by(User.id).first()
    
    # Fallback to any active user
    if not user:
        user = db.query(User).execution_options(skip_tenant_filter=True).filter(
            User.tenant_id == target_tenant_id,
            User.is_active == True
        ).order_by(User.id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active demo user found for tenant '{tenant}'"
        )
    
    # Create access token with standard expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    effective_role = user.effective_role
    access_token = create_access_token(
        data={
            "sub": user.username,
            "tenant_id": user.tenant_id,
            "role": effective_role.value
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/demo-info")
async def get_demo_info():
    """
    Get demo login information.
    
    Returns demo login status, key, and available demo tenants.
    Used by the demo landing page to display vertical options.
    
    Returns:
        Dict with demo_login_enabled, demo_key, tenants list, and auto_login_url
    """
    # Demo tenant configuration (must match demo_login endpoint)
    DEMO_TENANTS = [
        {
            "slug": "datacenter",
            "name": "Velocity Technologies",
            "vertical": "datacenter",
            "description": "IT infrastructure and data center management",
            "icon": "🖥️"
        },
        {
            "slug": "healthcare",
            "name": "City General Hospital",
            "vertical": "healthcare",
            "description": "Medical supplies and equipment tracking",
            "icon": "🏥"
        },
        {
            "slug": "warehouse",
            "name": "FastShip Fulfillment",
            "vertical": "warehouse",
            "description": "Warehouse and logistics inventory",
            "icon": "📦"
        },
    ]
    
    # Check if demo login feature is enabled
    demo_enabled = getattr(settings, 'DEMO_LOGIN_ENABLED', False)
    if not demo_enabled:
        return {
            "demo_login_enabled": False,
            "demo_key": None,
            "auto_login_url": None,
            "tenants": []
        }
    
    demo_key = getattr(settings, 'DEMO_LOGIN_KEY', None)
    
    if not demo_key:
        return {
            "demo_login_enabled": False,
            "demo_key": None,
            "auto_login_url": None,
            "tenants": []
        }
    
    return {
        "demo_login_enabled": True,
        "demo_key": demo_key,
        "auto_login_url": f"?demo_key={demo_key}",
        "tenants": DEMO_TENANTS
    }


@router.get("/check")
async def check_auth(current_user = Depends(get_current_user)):
    """
    Check if user is authenticated (returns user or null)
    Does not raise 401 error
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "is_active": current_user.is_active,
                "role": current_user.effective_role.value,
                "is_super_admin": getattr(current_user, 'is_super_admin', False)
            }
        }
    return {"authenticated": False, "user": None}
