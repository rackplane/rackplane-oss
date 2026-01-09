# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Connection Models
Double-ended cable connection tracking - Phase 2: Port-based connections
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class ConnectionEnd(str, enum.Enum):
    """Enum for cable connection end labels"""
    A = "A"
    B = "B"


class Connection(Base, TenantMixin):
    """
    Tracks connections between cables and ports.
    
    Phase 2: Now uses port_id for proper port-to-port connections.
    The device_asset_id is kept for backward compatibility but is deprecated.
    """
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys - CASCADE delete: when an asset is deleted, delete its connections
    cable_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # DEPRECATED: Kept for backward compatibility during transition
    device_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # NEW: Port-based connection (Phase 2)
    port_id = Column(Integer, ForeignKey("network_ports.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Which end of the cable ('A' or 'B')
    end_label = Column(SQLEnum(ConnectionEnd), nullable=False)
    
    # Relationships
    # Use passive_deletes=True to let the database handle cascade deletes
    cable_asset = relationship("Asset", foreign_keys=[cable_asset_id], back_populates="cable_connections", passive_deletes=True)
    device_asset = relationship("Asset", foreign_keys=[device_asset_id], back_populates="device_connections", passive_deletes=True)
    
    # NEW: Port relationship (Phase 2)
    port = relationship("NetworkPort", back_populates="connections")
    
    # Unique constraint: A cable can only have one connection for End 'A' and one for End 'B'
    __table_args__ = (
        UniqueConstraint('cable_asset_id', 'end_label', name='uq_cable_end'),
    )
    
    def __repr__(self):
        if self.port_id:
            return f"<Connection Cable {self.cable_asset_id} End {self.end_label} -> Port {self.port_id}>"
        return f"<Connection Cable {self.cable_asset_id} End {self.end_label} -> Device {self.device_asset_id}>"

