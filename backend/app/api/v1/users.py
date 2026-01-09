# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
User Management API Endpoints
CRUD operations for users (requires authentication)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_password_hash, get_current_active_user, get_current_tenant_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PasswordReset
from app.utils.audit_helpers import audit_create, audit_update, audit_delete
from app.services.audit_service import get_model_dict

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all users (requires authentication)
    Super admins see all users, tenant admins and regular users see only users in their tenant
    Read-only users can view users but cannot modify them
    """
    from app.core.tenant_query import apply_tenant_filter
    from app.models.user_role import UserRole
    
    effective_role = current_user.effective_role
    if effective_role == UserRole.SUPER_ADMIN:
        # Super admin: return all users (bypass tenant filtering)
        users = db.query(User).execution_options(skip_tenant_filter=True).all()
    else:
        # Regular user, tenant admin, or read-only: return only users in their tenant
        query = db.query(User)
        query = apply_tenant_filter(query, User)
        users = query.all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific user by ID (requires authentication)
    Super admins can access any user, others are tenant-filtered
    """
    from app.models.user_role import UserRole
    
    effective_role = current_user.effective_role
    if effective_role == UserRole.SUPER_ADMIN:
        # Super admin: can access any user (bypass tenant filtering)
        user = db.query(User).execution_options(skip_tenant_filter=True).filter(User.id == user_id).first()
    else:
        # Regular users: tenant-filtered
        query = db.query(User).filter(User.id == user_id)
        query = apply_tenant_filter(query, User)
        user = query.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new user (requires authentication)
    """
    # Determine tenant_id - use provided or current user's tenant
    tenant_id = user_data.tenant_id if user_data.tenant_id else current_user.tenant_id
    
    # Check if username already exists in the tenant
    existing_user = db.query(User).filter(
        User.username == user_data.username,
        User.tenant_id == tenant_id
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists in this tenant"
        )

    # Check permissions: Only super admins and tenant admins can create users
    from app.models.user_role import UserRole
    effective_role = current_user.effective_role
    if effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins and tenant admins can create users"
        )
    
    # Super admins can create users in any tenant, tenant admins only in their tenant
    if effective_role == UserRole.TENANT_ADMIN and tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admins can only create users in their own tenant"
        )
    
    # Determine role: Use provided role or default to USER
    user_role = user_data.role.value if user_data.role else UserRole.USER.value
    
    # Only super admins can create super admin users
    if user_role == UserRole.SUPER_ADMIN.value and effective_role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create super admin users"
        )
    
    # Seat enforcement: Check license tier and user count
    from app.models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get subscription tier (normalize legacy names)
    subscription_tier = tenant.subscription_tier or "community"
    if subscription_tier == "standard":
        subscription_tier = "community"
    elif subscription_tier == "enterprise":
        subscription_tier = "msp"
    
    # For Community and Starter tiers, enforce 1-seat limit (hard block)
    if subscription_tier in ["community", "starter"]:
        # Count existing active users in the tenant
        user_count = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_active == True
        ).count()
        
        # Block if already at limit (1 user)
        if user_count >= 1:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "seat_limit_reached",
                    "message": f"Your {subscription_tier.title()} license allows only 1 user. Upgrade to Pro or MSP to add more users.",
                    "current_tier": subscription_tier,
                    "seats_used": user_count,
                    "seats_limit": 1,
                    "upgrade_url": "/settings/subscription"
                }
            )
    
    # Pro and MSP tiers allow unlimited users (no enforcement needed)
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        tenant_id=tenant_id,
        role=user_role,  # Already converted to string value
        is_active=True
    )
    new_user.sync_is_super_admin()  # Sync is_super_admin flag

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log the create operation
    audit_create(db, new_user, current_user, request)

    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a user (requires authentication)
    """
    from app.models.user_role import UserRole
    import logging
    logger = logging.getLogger(__name__)
    
    # Query user - super admins can access any user, others are tenant-filtered
    effective_role = current_user.effective_role
    logger.debug(f"update_user: current_user.effective_role={effective_role}, current_user.role={current_user.role}, current_user.is_super_admin={current_user.is_super_admin}")
    
    if effective_role == UserRole.SUPER_ADMIN:
        # Super admin: can access any user (bypass tenant filtering)
        user = db.query(User).execution_options(skip_tenant_filter=True).filter(User.id == user_id).first()
        logger.debug(f"update_user: Skipping tenant filter (super admin)")
    else:
        # Regular users: tenant-filtered
        from app.core.tenant_query import apply_tenant_filter
        query = db.query(User).filter(User.id == user_id)
        query = apply_tenant_filter(query, User)
        user = query.first()
        logger.debug(f"update_user: Applied tenant filter (not super admin)")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Capture old values BEFORE update for audit logging
    from app.services.audit_service import get_model_dict
    old_values = get_model_dict(user)

    # Check permissions: Only super admins and tenant admins can update users
    from app.models.user_role import UserRole
    effective_role = current_user.effective_role
    
    # Super admins can update any user, tenant admins only users in their tenant
    if effective_role == UserRole.TENANT_ADMIN:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admins can only update users in their own tenant"
            )
    elif effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins and tenant admins can update users"
        )
    
    # Update role if provided
    if user_data.role is not None:
        role_value = user_data.role.value if isinstance(user_data.role, UserRole) else user_data.role
        user_role_enum = UserRole(role_value) if isinstance(role_value, str) else role_value
        
        # Only super admins can change roles to/from super_admin
        if user_role_enum == UserRole.SUPER_ADMIN or user.role_enum == UserRole.SUPER_ADMIN:
            if effective_role != UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admins can change super admin role"
                )
        user.role = role_value
        user.sync_is_super_admin()  # Sync is_super_admin flag
    
    # Update password if provided
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

    # Update is_active if provided
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    
    # Re-query the user after commit to get a fresh instance (avoids detached instance errors)
    # Use the same tenant filtering logic as the initial query
    if effective_role == UserRole.SUPER_ADMIN:
        user = db.query(User).execution_options(skip_tenant_filter=True).filter(User.id == user_id).first()
    else:
        from app.core.tenant_query import apply_tenant_filter
        query = db.query(User).filter(User.id == user_id)
        query = apply_tenant_filter(query, User)
        user = query.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found after update")

    # Audit log the update operation
    audit_update(db, user, current_user, request, old_values)

    return user


@router.post("/{user_id}/reset-password", response_model=UserResponse)
async def reset_user_password(
    user_id: int,
    password_data: PasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reset a user's password
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Capture old values
    old_values = get_model_dict(user)
    
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    db.refresh(user)
    
    # Audit log
    # Note: hashed_password will change, exposing that password was reset
    audit_update(db, user, current_user, request, old_values)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)  # Only tenant admins and super admins can delete users
):
    """
    Delete a user (requires tenant admin or super admin)
    Prevents deletion if this is the last user in the system
    Super admins can delete users from any tenant, tenant admins can only delete users from their tenant
    """
    from app.core.tenant_query import apply_tenant_filter
    from app.models.user_role import UserRole
    
    effective_role = current_user.effective_role
    # Super admins can delete users from any tenant
    # Tenant admins can only delete users from their tenant
    if effective_role == UserRole.SUPER_ADMIN:
        # Super admin: query without tenant filter (bypass tenant filtering)
        user = db.query(User).execution_options(skip_tenant_filter=True).filter(User.id == user_id).first()
    else:
        # Tenant admin: query with tenant filter
        query = db.query(User).filter(User.id == user_id)
        query = apply_tenant_filter(query, User)
        user = query.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check total user count (across all tenants) - bypass tenant filtering
    total_users = db.query(User).execution_options(skip_tenant_filter=True).count()
    if total_users <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last user in the system"
        )

    # Prevent deleting yourself - always block self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user account. Please ask another admin to delete it."
        )

    # Audit log the delete operation BEFORE deleting
    audit_delete(db, user, current_user, request)

    db.delete(user)
    db.commit()

    return None
