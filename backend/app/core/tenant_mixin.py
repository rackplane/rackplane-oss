# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Mixin
Base mixin for models that require tenant isolation

This mixin adds the tenant_id column to SQLAlchemy models, enabling
automatic tenant-based data isolation. All models that store tenant-specific
data should inherit from this mixin.

Usage:
    from app.core.tenant_mixin import TenantMixin
    from app.core.database import Base
    
    class Asset(Base, TenantMixin):
        # tenant_id is automatically added
        asset_tag = Column(String, nullable=False)
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declared_attr


class TenantMixin:
    """
    Mixin to add tenant_id column to models for multi-tenancy isolation.
    
    This mixin uses SQLAlchemy's declared_attr to add a tenant_id foreign key
    column to any model that inherits from it. The tenant_id is automatically
    set by database event listeners and filtered by query interceptors.
    
    Example:
        class Asset(Base, TenantMixin):
            __tablename__ = "assets"
            id = Column(Integer, primary_key=True)
            # tenant_id is automatically added here
    """
    
    @declared_attr
    def tenant_id(cls):
        """
        Declared attribute for tenant_id column.
        
        Returns:
            SQLAlchemy Column definition for tenant_id foreign key
        """
        return Column(
            Integer,
            ForeignKey("tenants.id"),
            nullable=False,
            index=True,
            comment="Tenant ID for multi-tenant isolation"
        )

