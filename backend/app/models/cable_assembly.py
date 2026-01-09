# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
CableAssembly Model

Pre-configured fiber cable with transceivers - bundle of:
- 1x Fiber Cable
- 1x Transceiver A (End A)
- 1x Transceiver B (End B)

Can be deployed as a single unit like a DAC cable.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class AssemblyStatus(str, enum.Enum):
    """Cable assembly status"""
    AVAILABLE = "available"      # Ready to deploy
    DEPLOYED = "deployed"        # Currently in use
    RESERVED = "reserved"        # Reserved for future use
    MAINTENANCE = "maintenance"  # Being serviced


class CableAssembly(Base, TenantMixin):
    """Pre-configured fiber cable with transceivers"""
    __tablename__ = "cable_assemblies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Assembly identification
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    
    # Components (all link to assets table)
    fiber_cable_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    transceiver_a_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    transceiver_b_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    
    # Status
    status = Column(SQLEnum(AssemblyStatus), default=AssemblyStatus.AVAILABLE, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fiber_cable = relationship("Asset", foreign_keys=[fiber_cable_id])
    transceiver_a = relationship("Asset", foreign_keys=[transceiver_a_id])
    transceiver_b = relationship("Asset", foreign_keys=[transceiver_b_id])

    def __repr__(self):
        return f"<CableAssembly {self.id}: {self.name}>"
