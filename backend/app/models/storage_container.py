# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Storage Container Models
Track boxes, bins, shelves, and other storage locations for inventory
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class StorageContainer(Base, TenantMixin):
    """Storage container tracking table"""
    __tablename__ = "storage_containers"
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='idx_storage_containers_name_tenant'),
        Index('idx_storage_containers_barcode_tenant', 'barcode', 'tenant_id', unique=True, postgresql_where=text('barcode IS NOT NULL')),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # Removed unique - now unique per tenant
    container_type = Column(String(50), nullable=False, index=True)  # box, bin, shelf, cabinet, etc.

    # Location tracking - foreign keys to actual locations
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True, index=True)
    location = Column(String(200), nullable=True)  # Legacy free-text field for additional location info

    description = Column(Text, nullable=True)
    barcode = Column(String(100), nullable=True, index=True)  # Removed unique - now unique per tenant
    min_stock_threshold = Column(Integer, nullable=True, default=0, comment="Minimum stock level for reorder alerts")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assets = relationship("Asset", back_populates="storage_container")
    datacenter = relationship("Datacenter", foreign_keys=[datacenter_id])
    room = relationship("Room", foreign_keys=[room_id])
    stock_thresholds = relationship("ContainerStockThreshold", back_populates="storage_container", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StorageContainer(name='{self.name}', type='{self.container_type}')>"
