# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Container Stock Threshold Models
Track minimum stock levels per item type within storage containers
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class ContainerStockThreshold(Base, TenantMixin):
    """
    Tracks minimum stock threshold for a specific item type within a storage container.
    
    Example: "Box 1 should have at least 5 DAC cables (FS, 1m)"
    - storage_container_id: Box 1
    - asset_type: dac_cable
    - manufacturer: FS
    - model: 1m
    - min_threshold: 5
    """
    __tablename__ = "container_stock_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    storage_container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=False, index=True)
    
    # Item type specification (all must match for grouping)
    asset_type = Column(String(100), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=True, index=True)  # Optional - None means "any manufacturer"
    model = Column(String(200), nullable=True, index=True)  # Optional - None means "any model"
    
    min_threshold = Column(Integer, nullable=False, default=1, comment="Minimum stock level for this item type")
    max_quantity = Column(Integer, nullable=True, default=None, comment="Maximum stock level (Par Level) for this item type")
    
    # Unique constraint: one threshold per container + item type combination
    __table_args__ = (
        UniqueConstraint('storage_container_id', 'asset_type', 'manufacturer', 'model', 'tenant_id', 
                        name='uq_container_stock_threshold'),
    )
    
    # Relationships
    storage_container = relationship("StorageContainer", back_populates="stock_thresholds")

    def __repr__(self):
        return f"<ContainerStockThreshold(container={self.storage_container_id}, type={self.asset_type}, min={self.min_threshold})>"

