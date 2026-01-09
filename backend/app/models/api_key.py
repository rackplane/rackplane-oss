# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Key Model
Personal Access Tokens (PATs) for headless/automated access

This model provides long-lived API keys for headless services like Docker Relays.
Keys are prefixed with "rp_" and stored as hashes (never plain text).

Key Features:
- User-scoped keys (each key belongs to a user)
- Hashed storage (bcrypt, same as passwords)
- Active/inactive toggle (kill switch for compromised keys)
- Last used tracking
- Label for identification (e.g., "Warehouse Relay")

Security:
- Keys are hashed using bcrypt before storage
- Raw key is shown only once during generation
- Keys can be revoked without affecting user account
- Tenant-scoped (keys inherit user's tenant)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class ApiKey(Base, TenantMixin):
    """
    API Key model for Personal Access Tokens (PATs).
    
    Provides long-lived authentication tokens for headless services,
    Docker containers, and automated systems that cannot use interactive login.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to users table (owner of the key)
        key_hash: Bcrypt hash of the API key (never store raw key!)
        label: Human-readable label for the key (e.g., "Warehouse Relay")
        last_used_at: Timestamp when key was last used (for monitoring)
        is_active: Whether the key is active (kill switch for compromised keys)
        tenant_id: Foreign key to tenants table (from TenantMixin, inherited from user)
        created_at: Timestamp when key was created
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        Index('idx_api_keys_user_label_tenant', 'user_id', 'label', 'tenant_id', unique=True, postgresql_where=text('label IS NOT NULL')),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="Owner of the API key")
    key_hash = Column(String(255), nullable=False, comment="Bcrypt hash of the API key (never store raw key!)")
    label = Column(String(100), nullable=True, comment="Human-readable label (e.g., 'Warehouse Relay')")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp when key was last used")
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="Kill switch for compromised keys")
    scopes = Column(JSON, default=list, nullable=True, comment="List of allowed scopes (e.g., ['print_jobs:read', 'print_jobs:write']). Empty list = all scopes")
    # tenant_id is inherited from TenantMixin
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Timestamp when key was created")

    # Relationship to user
    user = relationship("User", backref="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, label='{self.label}', is_active={self.is_active})>"

