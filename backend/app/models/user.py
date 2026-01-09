# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
User Model
Authentication and user management

This model represents a user account in the system. Users belong to a tenant
and are used for authentication and authorization. Each user has a username
that is unique within their tenant (not globally unique).

Key Features:
- Tenant-scoped username (unique per tenant, not globally)
- Bcrypt-hashed passwords
- Active/inactive status
- Role-based access control (SUPER_ADMIN, TENANT_ADMIN, USER, READ_ONLY)
- Automatic tenant_id assignment via TenantMixin

Security:
- Passwords are stored as bcrypt hashes (never plain text)
- Username uniqueness is enforced per tenant (not globally)
- Role-based permissions control access to features
- Super admins can manage multiple tenants
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin
from app.models.user_role import UserRole


class User(Base, TenantMixin):
    """
    User model for authentication and authorization.
    
    Represents a user account that can log in and access the system. Users
    belong to a tenant and their data is automatically filtered by tenant_id.
    
    Attributes:
        id: Primary key
        username: Login username (unique per tenant)
        hashed_password: Bcrypt hash of the password (never store plain text!)
        tenant_id: Foreign key to tenants table (from TenantMixin)
        role: User role (SUPER_ADMIN, TENANT_ADMIN, USER, READ_ONLY)
        is_active: Whether the user account is active
        is_super_admin: Legacy flag for backward compatibility (derived from role)
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        
    Relationships:
        tenant: Reference to the Tenant this user belongs to
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('username', 'tenant_id', name='idx_users_username_tenant'),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, index=True, comment="Login username (unique per tenant)")
    hashed_password = Column(String(255), nullable=False, comment="Bcrypt hash of password")
    email = Column(String(255), nullable=True, index=True, comment="Email address for notifications")
    # tenant_id is inherited from TenantMixin
    role = Column(String(20), default=UserRole.USER.value, nullable=False, index=True, comment="User role (super_admin, tenant_admin, user, read_only)")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether user account is active")
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True, comment="Legacy flag for backward compatibility (derived from role)")
    notification_preferences = Column(JSON, default=lambda: {
        "low_stock": True,
        "maintenance": True,
        "warranty": True,
        "email_enabled": True
    }, nullable=True, comment="Email notification preferences")
    ui_preferences = Column(JSON, default=lambda: {}, nullable=True, 
        comment="UI preferences (nav bar layout, theme, etc.)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def role_enum(self) -> UserRole:
        """Get role as UserRole enum."""
        if isinstance(self.role, str):
            try:
                return UserRole(self.role)
            except ValueError:
                return UserRole.USER
        return self.role if isinstance(self.role, UserRole) else UserRole.USER
    
    @property
    def effective_role(self) -> UserRole:
        """Get effective role, using is_super_admin for backward compatibility if role is not set."""
        if self.role:
            return self.role_enum
        # Backward compatibility: if role is None but is_super_admin is True, return SUPER_ADMIN
        if self.is_super_admin:
            return UserRole.SUPER_ADMIN
        return UserRole.USER
    
    def sync_is_super_admin(self):
        """Sync is_super_admin flag with role for backward compatibility."""
        role_enum = self.role_enum
        if role_enum == UserRole.SUPER_ADMIN:
            self.is_super_admin = True
        else:
            self.is_super_admin = False

    # Relationships
    tenant = relationship("Tenant", backref="users")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', tenant_id={self.tenant_id}, is_active={self.is_active})>"
