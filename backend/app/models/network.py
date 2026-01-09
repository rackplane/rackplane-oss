# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Network Connectivity Models
Ports, connections, VLANs, and cable management
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class PortType(str, enum.Enum):
    """Network port types"""
    RJ45 = "RJ45"
    SFP = "SFP"
    SFP_PLUS = "SFP_PLUS"
    SFP56 = "SFP56"
    QSFP = "QSFP"
    QSFP28 = "QSFP28"
    QSFP56 = "QSFP56"
    QSFP_DD = "QSFP_DD"
    QSFP112 = "QSFP112"  # 400G
    OSFP = "OSFP"  # 800G (legacy - use OSFP_FIN or OSFP_FLT)
    OSFP_FIN = "OSFP_FIN"  # 800G OSFP Finned (for switches)
    OSFP_FLT = "OSFP_FLT"  # 800G OSFP Flat (for network cards)
    FC = "FC"  # Fiber Channel
    CONSOLE = "CONSOLE"
    MGMT = "MGMT"
    OTHER = "OTHER"


class PortStatus(str, enum.Enum):
    """Port status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    FAILED = "failed"
    TESTING = "testing"


class LaneEncoding(str, enum.Enum):
    """
    Port lane encoding/signaling type.
    
    Determines what cables and transceivers are compatible with the port.
    - NRZ: Non-Return-to-Zero (28Gbps per lane) - Legacy, used in 100G QSFP28
    - PAM4: Pulse Amplitude Modulation 4-level (56/112/224 Gbps per lane) - Modern high-speed
    - BOTH: Port supports both NRZ and PAM4 (common in newer switches)
    - UNKNOWN: Encoding not specified
    """
    nrz = "nrz"          # 28G/lane (100G = 4x28G)
    pam4 = "pam4"        # 56G/112G/224G per lane (400G = 8x56G or 4x112G, 800G = 8x112G)
    both = "both"        # Supports both NRZ and PAM4
    unknown = "unknown"  # Not specified


class CableType(str, enum.Enum):
    """Cable types"""
    CAT5E = "cat5e"
    CAT6 = "cat6"
    CAT6A = "cat6a"
    CAT7 = "cat7"
    FIBER_SM = "fiber_singlemode"
    FIBER_MM = "fiber_multimode"
    DAC = "dac"  # Direct Attach Copper
    POWER = "power"
    OTHER = "other"


class NetworkPort(Base, TenantMixin):
    """Network ports on assets"""
    __tablename__ = "network_ports"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)

    # Port Identification
    port_number = Column(String(50), nullable=False)
    port_name = Column(String(200))
    port_label = Column(String(200))

    # Port Type and Specifications
    port_type = Column(SQLEnum(PortType), nullable=False)
    speed_mbps = Column(Integer)  # 100, 1000, 10000, 25000, 40000, 100000
    lane_encoding = Column(SQLEnum(LaneEncoding), default=LaneEncoding.unknown, nullable=True)  # nrz, pam4, both
    duplex = Column(String(20))  # full, half, auto

    # Status
    status = Column(SQLEnum(PortStatus), default=PortStatus.INACTIVE)
    enabled = Column(Boolean, default=True)

    # VLAN Assignment
    vlan_id = Column(Integer, ForeignKey("vlans.id"), nullable=True)
    native_vlan = Column(Integer, nullable=True)
    allowed_vlans = Column(JSON, default=[])

    # MAC Address
    mac_address = Column(String(17), nullable=True)

    # Transceiver Information
    transceiver_type = Column(String(100), nullable=True)
    transceiver_serial = Column(String(200), nullable=True)
    transceiver_vendor = Column(String(100), nullable=True)
    
    # Installed transceiver asset (for fiber connections with tracked transceivers)
    # Links to an optical_transceiver asset in the assets table
    installed_transceiver_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)

    # Connected To
    connected_port_id = Column(Integer, ForeignKey("network_ports.id"), nullable=True)
    connection_id = Column(Integer, ForeignKey("network_connections.id"), nullable=True)

    # PoE (Power over Ethernet)
    poe_capable = Column(Boolean, default=False)
    poe_enabled = Column(Boolean, default=False)
    poe_power_watts = Column(Float, nullable=True)

    # Statistics (from SNMP/API)
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)
    errors_in = Column(Integer, default=0)
    errors_out = Column(Integer, default=0)
    last_stats_update = Column(DateTime, nullable=True)

    # Metadata
    description = Column(Text)
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", foreign_keys=[asset_id], back_populates="network_ports")
    vlan = relationship("VLAN", back_populates="ports")
    
    # Installed transceiver relationship (for fiber connections)
    installed_transceiver = relationship("Asset", foreign_keys=[installed_transceiver_id])
    
    # Phase 2: Connection relationship (cables connected to this port)
    connections = relationship("Connection", back_populates="port", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NetworkPort {self.asset.hostname}:{self.port_number}>"


class NetworkConnection(Base, TenantMixin):
    """Physical network connections (cables)"""
    __tablename__ = "network_connections"

    id = Column(Integer, primary_key=True, index=True)

    # Connection Endpoints
    source_port_id = Column(Integer, ForeignKey("network_ports.id"), nullable=False)
    destination_port_id = Column(Integer, ForeignKey("network_ports.id"), nullable=False)

    # Cable Information
    cable_type = Column(SQLEnum(CableType), nullable=False)
    cable_length_m = Column(Float, nullable=True)
    cable_color = Column(String(50), nullable=True)
    cable_label = Column(String(200), nullable=True)
    cable_serial = Column(String(200), nullable=True)

    # Route
    cable_path = Column(JSON, default=[])  # Array of waypoints/conduits

    # Status
    is_active = Column(Boolean, default=True)
    tested = Column(Boolean, default=False)
    test_date = Column(DateTime, nullable=True)
    test_results = Column(JSON, default={})

    # Installation
    installed_by = Column(String(200))
    installed_at = Column(DateTime, nullable=True)

    # Documentation
    photos = Column(JSON, default=[])
    diagram_url = Column(String(500), nullable=True)

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NetworkConnection {self.id}: Port {self.source_port_id} -> Port {self.destination_port_id}>"


class VLAN(Base, TenantMixin):
    """VLAN definitions"""
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True, index=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=True)

    # VLAN Information
    vlan_id = Column(Integer, nullable=False, index=True)  # Now unique per tenant+datacenter
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Network
    network_address = Column(String(45))  # CIDR notation
    gateway = Column(String(45), nullable=True)
    subnet_mask = Column(String(45), nullable=True)

    # Purpose
    purpose = Column(String(100))  # management, production, storage, backup, etc.

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    notes = Column(Text)
    custom_fields = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ports = relationship("NetworkPort", back_populates="vlan")

    def __repr__(self):
        return f"<VLAN {self.vlan_id}: {self.name}>"
