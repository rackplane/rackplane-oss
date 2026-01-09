# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Asset Type Model
Allows dynamic management of asset types
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class AssetTypeModel(Base, TenantMixin):
    """Dynamic asset type definitions"""
    __tablename__ = "asset_types"
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='idx_asset_types_name_tenant'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # Removed unique - now unique per tenant
    display_name = Column(String(200), nullable=False)  # e.g., "Server", "Network Switch"
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon name for UI
    color = Column(String(20), nullable=True)  # Color code for UI
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System types can't be deleted
    
    # Flexible feature flags stored as JSONB
    # Currently implemented flags:
    #   - networkable: Shows network ports, management interfaces, cable connections, hostname
    features = Column(JSONB, nullable=False, server_default='{}')

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<AssetType {self.name}>"
