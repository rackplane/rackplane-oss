# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Location Models
Datacenter, Room, Rack, and Position tracking
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class Datacenter(Base, TenantMixin):
    """Datacenter/Site information"""
    __tablename__ = "datacenters"
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='idx_datacenters_name_tenant'),
        UniqueConstraint('code', 'tenant_id', name='idx_datacenters_code_tenant'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # Removed unique - now unique per tenant
    code = Column(String(100), nullable=False)  # Removed unique - now unique per tenant

    # Location
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)

    # Capacity
    total_power_capacity_kw = Column(Float)
    total_cooling_capacity_btu = Column(Float)
    total_floor_space_sqm = Column(Float)

    # Environmental
    target_temperature_c = Column(Float, default=22.0)
    target_humidity_percent = Column(Float, default=50.0)

    # Metadata
    facility_manager = Column(String(200))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True)

    # NetBox Integration
    netbox_id = Column(String(50), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rooms = relationship("Room", back_populates="datacenter", cascade="all, delete-orphan")
    racks = relationship("Rack", back_populates="datacenter")
    assets = relationship("Asset", back_populates="datacenter")
    environmental_sensors = relationship("EnvironmentalSensor", back_populates="datacenter")

    def __repr__(self):
        return f"<Datacenter {self.code} - {self.name}>"


class Room(Base, TenantMixin):
    """Rooms within a datacenter"""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=False)

    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), nullable=False)  # e.g., ROOM-A, MDF, IDF-1

    # Physical Properties
    floor_number = Column(Integer)
    floor_space_sqm = Column(Float)
    ceiling_height_m = Column(Float)

    # Capacity
    power_capacity_kw = Column(Float)
    cooling_capacity_btu = Column(Float)

    # Configuration
    aisle_configuration = Column(String(50))  # hot_aisle, cold_aisle, containment
    notes = Column(Text)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datacenter = relationship("Datacenter", back_populates="rooms")
    racks = relationship("Rack", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Room {self.code} in {self.datacenter.code}>"


class Rack(Base, TenantMixin):
    """Rack/Cabinet tracking"""
    __tablename__ = "racks"
    __table_args__ = (
        UniqueConstraint('code', 'tenant_id', name='idx_racks_code_tenant'),
    )

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)

    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), nullable=False)  # Removed unique - now unique per tenant

    # Physical Properties
    height_u = Column(Integer, default=42)  # Standard rack is 42U
    width_mm = Column(Float, default=600)
    depth_mm = Column(Float, default=1000)

    # Location within room
    row = Column(String(20))
    position = Column(String(20))

    # Power
    power_capacity_watts = Column(Float)
    pdu_count = Column(Integer, default=0)
    pdu_models = Column(JSON, default=[])

    # Cooling
    cooling_capacity_btu = Column(Float)

    # Configuration
    numbering_scheme = Column(String(20), default="bottom_up")  # bottom_up, top_down
    front_facing = Column(String(20))  # north, south, east, west

    # Metadata
    manufacturer = Column(String(100))
    model = Column(String(100))
    serial_number = Column(String(200))
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True)

    # NetBox Integration
    netbox_id = Column(String(50), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datacenter = relationship("Datacenter")
    room = relationship("Room", back_populates="racks")
    assets = relationship("Asset", back_populates="rack")
    positions = relationship("RackPosition", back_populates="rack", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Rack {self.code}>"


class RackPosition(Base, TenantMixin):
    """Individual U-position tracking within racks"""
    __tablename__ = "rack_positions"

    id = Column(Integer, primary_key=True, index=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=False)

    u_position = Column(Integer, nullable=False)  # 1-42 for standard rack
    is_occupied = Column(Boolean, default=False)

    # Occupied by
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)

    # Power at this position
    power_usage_watts = Column(Float, default=0)

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rack = relationship("Rack", back_populates="positions")

    def __repr__(self):
        return f"<RackPosition {self.rack.code} U{self.u_position}>"
