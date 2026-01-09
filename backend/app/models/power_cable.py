# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Power Cable Models
Track power cables with different connector types and voltages
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class PowerConnectorType(str, enum.Enum):
    """Power connector types (IEC 60320)"""
    C13 = "c13"  # Female (device side, 10A)
    C14 = "c14"  # Male (device side, 10A)
    C15 = "c15"  # Male (high temp, 10A)
    C19 = "c19"  # Female (device side, 16A)
    C20 = "c20"  # Male (device side, 16A)
    C21 = "c21"  # Male (high temp, 16A)
    NEMA_5_15P = "nema_5-15p"  # Standard US plug (15A, 125V)
    NEMA_5_15R = "nema_5-15r"  # Standard US receptacle (15A, 125V)
    NEMA_L5_20P = "nema_l5-20p"  # Twist-lock plug (20A, 125V)
    NEMA_L5_20R = "nema_l5-20r"  # Twist-lock receptacle (20A, 125V)
    NEMA_L6_20P = "nema_l6-20p"  # Twist-lock plug (20A, 250V)
    NEMA_L6_20R = "nema_l6-20r"  # Twist-lock receptacle (20A, 250V)
    NEMA_L6_30P = "nema_l6-30p"  # Twist-lock plug (30A, 250V)
    NEMA_L6_30R = "nema_l6-30r"  # Twist-lock receptacle (30A, 250V)
    CEE_7_7 = "cee_7-7"  # Schuko plug (European)
    BS_1363 = "bs_1363"  # UK plug


class PowerCable(Base, TenantMixin):
    """Power cable tracking table"""
    __tablename__ = "power_cables"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # e.g., "C13-C14 2m #1"

    # Connector types (both ends)
    connector_end_a = Column(SQLEnum(PowerConnectorType), nullable=False, index=True)
    connector_end_b = Column(SQLEnum(PowerConnectorType), nullable=False, index=True)

    # Cable specifications
    length_meters = Column(Float, nullable=True)  # Cable length in meters
    voltage = Column(String(20), nullable=False, index=True)  # e.g., "120V", "208V", "240V"
    amperage = Column(String(20), nullable=True)  # e.g., "10A", "15A", "20A"
    wire_gauge = Column(String(20), nullable=True)  # e.g., "14AWG", "12AWG"

    # Color coding (for organization)
    color = Column(String(50), nullable=True)  # Cable color

    # Storage location
    storage_container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=True)
    storage_container = relationship("StorageContainer")

    # Additional info
    manufacturer = Column(String(100), nullable=True, index=True)
    model = Column(String(200), nullable=True)
    part_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)  # How many of this exact cable

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PowerCable(name='{self.name}', {self.connector_end_a}-{self.connector_end_b}, {self.voltage})>"
