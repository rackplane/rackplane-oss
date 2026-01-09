# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Authentication Utilities
JWT token creation/validation and password hashing

This module provides:
- Password hashing and verification (bcrypt)
- JWT token creation and validation
- User authentication
- FastAPI dependencies for protected endpoints

Security Features:
- Bcrypt password hashing with automatic salt generation
- JWT tokens with expiration
- Tenant ID included in JWT payload
- Optional and required authentication dependencies

Dependencies:
- get_current_user: Optional authentication (returns None if not authenticated)
- get_current_active_user: Required authentication (raises 401 if not authenticated)
- get_current_super_admin: Super admin only (raises 403 if not super admin)

Usage:
    from app.core.auth import get_current_active_user
    
    @router.get("/protected")
    def protected_endpoint(user: User = Depends(get_current_active_user)):
        return {"message": f"Hello {user.username}"}
"""

from datetime import datetime, timedelta
from typing import Optional
import logging
import warnings
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.user_role import UserRole
from app.schemas.user import TokenData

logger = logging.getLogger(__name__)

# Suppress harmless bcrypt version warning from passlib
# This is a known compatibility issue between passlib 1.7.4 and bcrypt 4.1.3+
# The error is caught by passlib and logged, but doesn't affect functionality
# Suppress at multiple levels to ensure it's caught
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
warnings.filterwarnings("ignore", message=".*bcrypt.*__about__.*")
warnings.filterwarnings("ignore", message=".*trapped.*error.*bcrypt.*")

# Suppress passlib logger warnings
passlib_logger = logging.getLogger("passlib.handlers.bcrypt")
passlib_logger.setLevel(logging.ERROR)

# Now import passlib after setting up suppression
from passlib.context import CryptContext

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
# auto_error=False allows endpoints to handle missing tokens gracefully
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its bcrypt hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hash of the password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with tenant_id.
    
    The token includes:
    - sub: Username (subject)
    - tenant_id: Tenant ID for multi-tenant isolation
    - exp: Expiration timestamp
    
    Args:
        data: Dictionary containing token payload (must include 'sub' and 'tenant_id')
        expires_delta: Optional expiration time delta. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_user_by_username(db: Session, username: str, tenant_id: Optional[int] = None) -> Optional[User]:
    """
    Get user by username, optionally filtered by tenant_id.
    
    Args:
        db: Database session
        username: Username to lookup
        tenant_id: Optional tenant ID to filter by
        
    Returns:
        User object if found, None otherwise
    """
    query = db.query(User).filter(User.username == username)
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    return query.first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password to verify
        
    Returns:
        User object if authentication succeeds, None otherwise
        
    Checks:
        - User exists
        - Password matches
        - User is active
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user from token
    Returns None if no token or invalid token (for optional authentication)
    Also sets tenant_id in context from token or user record
    """
    from app.core.tenant import set_current_tenant_id, get_current_tenant_id
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not token:
        logger.debug("get_current_user: No token provided")
        return None

    # Clean token - remove "Bearer " prefix if present (Swagger UI sometimes adds it)
    if token.startswith("Bearer "):
        token = token[7:]
        logger.debug("get_current_user: Removed 'Bearer ' prefix from token")
    
    # Check if this is an API key (starts with "rp_")
    if token.startswith("rp_"):
        return await get_user_from_api_key(token, db)

    # Otherwise, treat as JWT token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role_str = payload.get("role")  # Extract role from payload
        token_type = payload.get("type")  # Check if this is an agent token
        
        logger.debug(f"get_current_user: JWT decoded successfully - username={username}, tenant_id={tenant_id}, role={role_str}, type={token_type}")
        
        if username is None:
            logger.warning("get_current_user: JWT payload missing 'sub' (username)")
            return None
        
        # Handle agent tokens separately (agents are not Users)
        if token_type == "agent":
            agent_id = payload.get("agent_id") or username
            logger.info(f"get_current_user: Agent token detected - agent_id={agent_id}, tenant_id={tenant_id}")
            
            # Set tenant_id from token if present
            current_tenant_id = get_current_tenant_id()
            if tenant_id and not current_tenant_id:
                set_current_tenant_id(int(tenant_id))
                current_tenant_id = int(tenant_id)
                logger.info(f"Set tenant_id from agent token: {tenant_id}")
            elif not current_tenant_id:
                # Token missing tenant_id - fetch from agent record
                # Use a direct query without tenant filtering (bypassing our session)
                from sqlalchemy.orm import sessionmaker
                from app.core.database import engine
                from app.models.print_job import PrintAgent
                temp_db = sessionmaker(bind=engine)()
                try:
                    agent_lookup = temp_db.query(PrintAgent).filter(PrintAgent.agent_id == agent_id).first()
                    if agent_lookup and agent_lookup.tenant_id:
                        set_current_tenant_id(agent_lookup.tenant_id)
                        current_tenant_id = agent_lookup.tenant_id
                        logger.info(f"Set tenant_id from agent record: {agent_lookup.tenant_id}")
                    else:
                        logger.warning(f"get_current_user: Agent {agent_id} not found or missing tenant_id")
                finally:
                    temp_db.close()
            
            # Agents are not Users, so return None but tenant_id is now set in context
            # This allows agent-authenticated endpoints to work with tenant isolation
            return None
        
        # Convert role string to UserRole enum if present
        role = None
        if role_str:
            try:
                # UserRole is imported globally
                role = UserRole(role_str)
            except (ValueError, TypeError):
                logger.warning(f"get_current_user: Invalid role in token: {role_str}")
                role = None
        
        # Check if tenant_id is already set (should be set by middleware)
        current_tenant_id = get_current_tenant_id()
        logger.info(f"get_current_user: username={username}, token_tenant_id={tenant_id}, context_tenant_id={current_tenant_id}")
        
        # Set tenant_id in context if present in token and not already set
        if tenant_id and not current_tenant_id:
            set_current_tenant_id(int(tenant_id))
            current_tenant_id = int(tenant_id)
            logger.info(f"Set tenant_id from token: {tenant_id}")
        elif not current_tenant_id:
            # Token missing tenant_id and not in context - fetch from user record
            # Use a direct query without tenant filtering (bypassing our session)
            from sqlalchemy.orm import sessionmaker
            from app.core.database import engine
            temp_db = sessionmaker(bind=engine)()
            try:
                user_lookup = temp_db.query(User).filter(User.username == username).first()
                if user_lookup and user_lookup.tenant_id:
                    set_current_tenant_id(user_lookup.tenant_id)
                    current_tenant_id = user_lookup.tenant_id
                    logger.info(f"Set tenant_id from user record: {user_lookup.tenant_id}")
            finally:
                temp_db.close()
        
        token_data = TokenData(username=username)
        
        # Query user - first try without tenant filter to get user, then check role
        # This allows super admins to access users from any tenant
        user = get_user_by_username(db, username=token_data.username)
        
        if user is None or not user.is_active:
            return None

        # Ensure user object has the role from token (or DB if token missing)
        if role and user.role != role.value:
            user.role = role.value  # Update user object's role from token if different
        elif not user.role:
            # Default if not set
            # UserRole is imported globally
            user.role = UserRole.USER.value
        user.sync_is_super_admin()  # Sync legacy flag
        
        # Now check if user is super admin - if so, they can access any tenant
        # Otherwise, verify they're accessing their own tenant
        if user.effective_role != UserRole.SUPER_ADMIN:
            if current_tenant_id and user.tenant_id != current_tenant_id:
                logger.warning(f"get_current_user: User {username} is trying to access tenant {current_tenant_id} but belongs to tenant {user.tenant_id}")
                return None
            # Set tenant_id in context if not already set
            if not current_tenant_id and user.tenant_id:
                set_current_tenant_id(user.tenant_id)
                current_tenant_id = user.tenant_id
                logger.info(f"Set tenant_id from user object: {user.tenant_id}")

        # Ensure tenant_id is set in context (safety check)
        if not current_tenant_id and user.tenant_id:
            set_current_tenant_id(user.tenant_id)
            logger.info(f"Set tenant_id from user object: {user.tenant_id}")

        # Clear API key context (JWT auth, not API key)
        set_current_api_key_id(None)
        return user
        
    except JWTError as e:
        logger.warning(f"get_current_user: JWT decode error - {str(e)}")
        return None
    except (ValueError, TypeError) as e:
        # Invalid tenant_id format
        logger.warning(f"get_current_user: Invalid tenant_id format - {str(e)}")
        return None
    except Exception as e:
        logger.error(f"get_current_user: Unexpected error - {str(e)}", exc_info=True)
        return None


# Context variable to store current API key ID for audit logging
_api_key_id_context: Optional[int] = None

def get_current_api_key_id() -> Optional[int]:
    """Get the current API key ID from context (for audit logging)."""
    return _api_key_id_context

def set_current_api_key_id(token_id: Optional[int]) -> None:
    """Set the current API key ID in context (for audit logging)."""
    global _api_key_id_context
    _api_key_id_context = token_id


async def get_user_from_api_key(api_key: str, db: Session) -> Optional[User]:
    """
    Authenticate user from API key (Personal Access Token).
    
    API keys are prefixed with "rp_" and stored as bcrypt hashes.
    This allows headless services (Docker Relays) to authenticate without
    interactive login.
    
    Args:
        api_key: The API key string (should start with "rp_")
        db: Database session
        
    Returns:
        User object if key is valid and active, None otherwise
    """
    try:
        # Since we can't query by hash directly (bcrypt is one-way),
        # we need to check all active keys and verify each one.
        # This is acceptable for low-volume API key usage.
        # CRITICAL: Skip tenant filtering here because we don't have tenant_id yet
        # (we're authenticating to GET the tenant_id from the user)
        active_keys = db.query(ApiKey).execution_options(skip_tenant_filter=True).filter(
            ApiKey.is_active == True
        ).all()
        
        logger.info(f"get_user_from_api_key: Checking {len(active_keys)} active key(s) for key starting with {api_key[:10]}...")
        
        matching_key = None
        for key_obj in active_keys:
            logger.info(f"get_user_from_api_key: Checking key ID {key_obj.id} (tenant {key_obj.tenant_id}, label: {key_obj.label})")
            if verify_password(api_key, key_obj.key_hash):
                logger.info(f"get_user_from_api_key: ✓ Match found for key ID {key_obj.id}")
                matching_key = key_obj
                break
            else:
                logger.info(f"get_user_from_api_key: ✗ No match for key ID {key_obj.id}")
        
        if not matching_key:
            logger.warning(f"get_user_from_api_key: Invalid or inactive API key (checked {len(active_keys)} active key(s), key starts with: {api_key[:10]}...)")
            return None
        
        # Update last_used_at
        matching_key.last_used_at = datetime.utcnow()
        db.commit()
        
        # Get the user
        user = db.query(User).filter(User.id == matching_key.user_id).first()
        if not user or not user.is_active:
            logger.warning(f"get_user_from_api_key: User {matching_key.user_id} not found or inactive")
            return None
        
        # Set tenant context
        from app.core.tenant import set_current_tenant_id
        if user.tenant_id:
            set_current_tenant_id(user.tenant_id)
        
        # Store token_id in context for audit logging
        set_current_api_key_id(matching_key.id)
        
        # Store API key object in context for scope checking
        from app.core.scopes import set_current_api_key
        set_current_api_key(matching_key)
        
        logger.info(f"get_user_from_api_key: Authenticated user {user.username} via API key {matching_key.id} ({matching_key.label})")
        return user
        
    except Exception as e:
        logger.error(f"get_user_from_api_key: Error authenticating API key - {str(e)}", exc_info=True)
        return None


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require authenticated user (raises 401 if not authenticated).
    
    Use this as a dependency for protected endpoints that require authentication.
    Raises HTTPException if user is not authenticated.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User object (guaranteed to be not None)
        
    Raises:
        HTTPException: 401 Unauthorized if user is not authenticated
        
    Example:
        @router.get("/protected")
        def protected_endpoint(user: User = Depends(get_current_active_user)):
            return {"message": f"Hello {user.username}"}
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get the current super admin user.
    
    Raises HTTPException if user is not a super admin. Use this for endpoints
    that require super admin privileges (tenant management, etc.).
    
    Args:
        current_user: Authenticated user from get_current_active_user
        
    Returns:
        User object (guaranteed to be super admin)
        
    Raises:
        HTTPException: 403 Forbidden if user is not a super admin
    """
    # Check both role and legacy is_super_admin for backward compatibility
    effective_role = current_user.effective_role
    if effective_role != UserRole.SUPER_ADMIN and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_current_tenant_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get the current tenant admin user.
    
    Raises HTTPException if user is not a tenant admin or super admin.
    Use this for endpoints that require tenant management privileges.
    
    Args:
        current_user: Authenticated user from get_current_active_user
        
    Returns:
        User object (guaranteed to be tenant admin or super admin)
        
    Raises:
        HTTPException: 403 Forbidden if user is not a tenant admin or super admin
    """
    effective_role = current_user.effective_role
    if effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required"
        )
    return current_user


async def get_current_writable_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get a user with write permissions.
    
    Raises HTTPException if user is read-only. Use this for endpoints
    that require write/modify permissions (POST, PUT, DELETE operations).
    
    Args:
        current_user: Authenticated user from get_current_active_user
        
    Returns:
        User object (guaranteed to have write permissions)
        
    Raises:
        HTTPException: 403 Forbidden if user is read-only
    """
    effective_role = current_user.effective_role
    if not UserRole.can_write(effective_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required. Read-only users cannot modify data."
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Factory function to create a dependency that requires a specific role.
    
    Args:
        required_role: The minimum role required for access
        
    Returns:
        A FastAPI dependency function
        
    Example:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role(UserRole.TENANT_ADMIN))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        effective_role = current_user.effective_role
        if not UserRole.has_permission(effective_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required_role.value} access required"
            )
        return current_user
    return role_checker
