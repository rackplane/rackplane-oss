# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Network Cable Models
Track ethernet, DAC, fiber cables and optical modules
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Enum as SQLEnum, Index, text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class CableType(str, enum.Enum):
    """Network cable types"""
    COPPER = "copper"  # Ethernet copper cable
    DAC = "dac"  # Direct Attach Copper
    FIBER = "fiber"  # Fiber optic
    AOC = "aoc"  # Active Optical Cable


class ConnectorType(str, enum.Enum):
    """Connector/module types"""
    RJ45 = "rj45"
    SFP = "sfp"  # Small Form-factor Pluggable
    SFP_PLUS = "sfp+"  # SFP+ (10G)
    SFP28 = "sfp28"  # SFP28 (25G)
    QSFP = "qsfp"  # Quad SFP (40G)
    QSFP_PLUS = "qsfp+"  # QSFP+ (40G)
    QSFP28 = "qsfp28"  # QSFP28 (100G)
    QSFP56 = "qsfp56"  # QSFP56 (200G)
    QSFP_DD = "qsfp-dd"  # QSFP Double Density (400G)
    OSFP = "osfp"  # Octal SFP (400G/800G) - legacy, use OSFP_FIN or OSFP_FLT
    OSFP_FIN = "osfp-fin"  # 800G OSFP Finned (for switches)
    OSFP_FLT = "osfp-flt"  # 800G OSFP Flat (for network cards/NICs)
    LC = "lc"  # LC connector (fiber)
    SC = "sc"  # SC connector (fiber)
    MPO = "mpo"  # MPO/MTP connector (fiber)


class NetworkCable(Base, TenantMixin):
    """Network cable and module tracking table"""
    __tablename__ = "network_cables"
    __table_args__ = (
        Index('idx_network_cables_serial_tenant', 'serial_number', 'tenant_id', unique=True, postgresql_where=text('serial_number IS NOT NULL')),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # e.g., "10G DAC 3m #1"
    cable_type = Column(SQLEnum(CableType), nullable=False, index=True)
    connector_type = Column(SQLEnum(ConnectorType), nullable=False, index=True)
    connector_type_end_a = Column(String(50), nullable=True, index=True)
    connector_type_end_b = Column(String(50), nullable=True, index=True)

    # Speed and specifications
    speed = Column(String(20), nullable=False, index=True)  # e.g., "1G", "10G", "25G", "40G", "100G", "400G"
    length_meters = Column(Float, nullable=True)  # Cable length in meters

    # Breakout configuration (e.g., "4x10G" for 40G->10G breakout)
    breakout = Column(String(50), nullable=True)

    # Fiber specific fields
    fiber_mode = Column(String(20), nullable=True)  # "singlemode" or "multimode"
    wavelength = Column(String(20), nullable=True)  # e.g., "850nm", "1310nm", "1550nm"

    # Storage location
    storage_container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=True)
    storage_container = relationship("StorageContainer")

    # Additional info
    manufacturer = Column(String(100), nullable=True, index=True)
    model = Column(String(200), nullable=True)
    serial_number = Column(String(200), nullable=True, index=True)  # Removed unique - now unique per tenant
    part_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)  # How many of this exact cable

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<NetworkCable(name='{self.name}', type='{self.cable_type}', speed='{self.speed}')>"
