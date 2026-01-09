# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Asset Models
Core inventory tracking for all hardware assets

This module defines the primary Asset model and related classes for tracking
all hardware inventory in the datacenter. Assets can be servers, switches,
cables, storage boxes, or any other physical hardware.

Key Features:
- Complete lifecycle tracking (ordered -> disposed)
- Multi-tenant isolation via TenantMixin
- Storage container support (boxes/bins)
- Stock level tracking for storage boxes
- Physical specifications (dimensions, weight, power)
- Network and management interface tracking
- Financial and warranty information
- NetBox integration support

Stock Management:
- Assets with status=IN_STORAGE and container_id set are considered "in stock"
- Storage boxes (asset_type='storage_box') can have min_stock_threshold
- Stock counts are calculated by grouping assets by type (manufacturer+model+asset_type)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum, TypeDecorator, UniqueConstraint, Index, text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class AssetStatus(str, enum.Enum):
    """
    Asset lifecycle status enumeration.
    
    Tracks the current state of an asset through its entire lifecycle from
    ordering to disposal. Status changes are logged in AssetLifecycleEvent.
    
    Status Flow:
        ORDERED -> IN_TRANSIT -> RECEIVED -> STAGING -> IN_STORAGE/DEPLOYED -> ACTIVE
        -> MAINTENANCE/FAILED -> DECOMMISSIONED -> RETIRED -> DISPOSED
    
    Values:
        ORDERED: Asset has been ordered but not yet received
        IN_TRANSIT: Asset is being shipped
        RECEIVED: Asset has been received at the datacenter
        STAGING: Asset is being prepared for deployment
        IN_STORAGE: Asset is stored in a container/box (used for stock tracking)
        DEPLOYED: Asset is in a rack or connected (but may not be active)
        ACTIVE: Asset is deployed and operational
        MAINTENANCE: Asset is undergoing maintenance
        FAILED: Asset has failed and needs replacement
        RMA: Asset is being returned/repaired
        DECOMMISSIONED: Asset has been removed from service
        RETIRED: Asset is no longer in use but not yet disposed
        DISPOSED: Asset has been disposed of/recycled
    """
    ORDERED = "ordered"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    STAGING = "staging"
    IN_STORAGE = "in_storage"  # Inside a box/bin - used for stock tracking
    DEPLOYED = "deployed"       # In a rack or connected
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    RMA = "rma"                 # Broken/Returned
    DECOMMISSIONED = "decommissioned"
    RETIRED = "retired"
    DISPOSED = "disposed"
    
    def __str__(self):
        """Return the enum value (lowercase) instead of the name"""
        return self.value


class AssetStatusType(TypeDecorator):
    """
    Custom SQLAlchemy type decorator that ensures enum values are used, not names.
    
    This fixes an issue where SQLAlchemy was storing enum names (e.g., "IN_STORAGE")
    instead of enum values (e.g., "in_storage"). The decorator ensures that:
    - When saving to database: converts enum to lowercase string value
    - When reading from database: converts string back to enum
    
    This ensures consistency in the database and proper enum handling in Python.
    """
    impl = String
    cache_ok = True
    
    def __init__(self):
        super().__init__(length=50)
    
    def process_bind_param(self, value, dialect):
        """
        Convert enum to its value when binding to database.
        
        Args:
            value: AssetStatus enum, string, or None
            dialect: SQLAlchemy dialect
            
        Returns:
            Lowercase string value of the enum, or None
        """
        if value is None:
            return None
        if isinstance(value, AssetStatus):
            return value.value  # Return the enum value, not the name
        if isinstance(value, str):
            # If it's already a string, try to normalize it
            return value.lower()
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        """
        Convert database value back to enum.
        
        Args:
            value: String value from database
            dialect: SQLAlchemy dialect
            
        Returns:
            AssetStatus enum or original value if conversion fails
        """
        if value is None:
            return None
        if isinstance(value, AssetStatus):
            return value
        try:
            return AssetStatus(value.lower())
        except ValueError:
            # If value doesn't match any enum, return as-is (shouldn't happen)
            return value


class Asset(Base, TenantMixin):
    """
    Primary asset tracking table for all hardware inventory.
    
    This is the core model for tracking all physical hardware assets in the
    datacenter, including servers, switches, cables, storage boxes, and more.
    All assets are automatically tenant-scoped via TenantMixin.
    
    Key Features:
    - Unique asset_tag and serial_number per tenant
    - Complete lifecycle status tracking
    - Physical location tracking (datacenter, rack, storage container)
    - Stock management for storage boxes (min_stock_threshold)
    - Physical specifications (dimensions, weight, power)
    - Network and management interface tracking
    - Financial and warranty information
    - NetBox integration support
    
    Stock Tracking:
    - Assets with status=IN_STORAGE and container_id set are "in stock"
    - Storage boxes (asset_type='storage_box') can have min_stock_threshold
    - Stock counts group by manufacturer+model+asset_type
    
    Location Hierarchy:
    - datacenter_id -> rack_id -> rack_position (for deployed assets)
    - storage_container_id -> container_id (for stored assets)
    """
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint('asset_tag', 'tenant_id', name='idx_assets_tag_tenant'),
        UniqueConstraint('serial_number', 'tenant_id', name='idx_assets_serial_tenant'),
        Index('idx_assets_hostname_tenant', 'hostname', 'tenant_id', unique=True, postgresql_where=text('hostname IS NOT NULL')),
    )

    id = Column(Integer, primary_key=True, index=True)
    asset_tag = Column(String(100), index=True, nullable=False, comment="Unique asset tag per tenant")
    serial_number = Column(String(200), index=True, nullable=False, comment="Serial number (unique per tenant)")
    original_serial_number = Column(String(200), nullable=True, comment="Original/initial serial number (for QR code matching after updates)")

    # Asset Classification
    asset_type = Column(String(100), nullable=False, index=True, comment="Asset type (validated against asset_types table)")
    manufacturer = Column(String(100), index=True, comment="Manufacturer name")
    model = Column(String(200), index=True, comment="Model number")
    sku = Column(String(100), comment="SKU/part number")

    # Status and Lifecycle
    # Use custom TypeDecorator to ensure enum values are used, not names
    # This fixes the issue where SQLAlchemy was using enum names (IN_STORAGE) instead of values (in_storage)
    status = Column(AssetStatusType(), default=AssetStatus.RECEIVED, index=True, comment="Current lifecycle status")
    on_loan = Column(Boolean, default=False, index=True, comment="Asset is on loan (to us or from us)")
    loan_direction = Column(String(20), nullable=True, comment="Loan direction: 'to_us' or 'from_us'")
    loan_party = Column(String(200), nullable=True, comment="Who we loaned it to, or who loaned it to us")
    loan_source = Column(String(200), nullable=True, comment="DEPRECATED: Legacy field for backward compatibility")

    # Location
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=True, comment="Datacenter location")
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True, comment="Rack location")
    rack_position_start = Column(Integer, nullable=True, comment="Starting U position in rack")
    rack_position_end = Column(Integer, nullable=True, comment="Ending U position (for multi-U devices)")
    storage_container_id = Column(Integer, ForeignKey("storage_containers.id"), nullable=True, comment="Storage container (room/shelf)")
    storage_location = Column(String(200), nullable=True, comment="Legacy free-text storage location")
    container_id = Column(Integer, ForeignKey("assets.id"), nullable=True, comment="Parent asset (box/bin) containing this asset")
    
    # Inventory Management (for storage containers/boxes)
    min_stock_threshold = Column(Integer, nullable=True, default=0, comment="Minimum stock level for reorder alerts (storage boxes only)")

    # Physical Specifications
    height_u = Column(Integer, comment="Height in rack units (U)")
    width_mm = Column(Float, comment="Width in millimeters")
    depth_mm = Column(Float, comment="Depth in millimeters")
    weight_kg = Column(Float, comment="Weight in kilograms")

    # Power Specifications
    power_consumption_watts = Column(Float, comment="Power consumption in watts")
    power_voltage = Column(String(20), comment="Power voltage (e.g., '110V', '220V')")
    power_connector_type = Column(String(50), comment="Power connector type")
    redundant_psu = Column(Integer, default=0, comment="Number of redundant power supplies")

    # Thermal Specifications
    btu_per_hour = Column(Float, comment="Heat output in BTU per hour")
    max_operating_temp_c = Column(Float, comment="Maximum operating temperature in Celsius")

    # Financial Information
    purchase_date = Column(DateTime, nullable=True, comment="Date of purchase")
    purchase_cost = Column(Float, comment="Purchase cost")
    currency = Column(String(10), default="USD", comment="Currency code (ISO 4217)")
    supplier = Column(String(200), comment="Supplier/vendor name")
    po_number = Column(String(100), comment="Purchase order number")

    # Warranty and Lifecycle
    warranty_start_date = Column(DateTime, nullable=True, comment="Warranty start date")
    warranty_end_date = Column(DateTime, nullable=True, comment="Warranty end date")
    eol_date = Column(DateTime, nullable=True, comment="End of Life date")
    eos_date = Column(DateTime, nullable=True, comment="End of Support date")

    # Network Information
    hostname = Column(String(255), nullable=True, comment="Hostname (unique per tenant)")
    primary_ip = Column(String(45), nullable=True, comment="Primary IP address (IPv4 or IPv6)")
    management_ip = Column(String(45), nullable=True, comment="Management IP address")
    mac_address = Column(String(17), nullable=True, comment="MAC address")

    # Management Interface Tracking
    has_console = Column(Boolean, default=False, comment="Has console access (switches)")
    has_ipmi = Column(Boolean, default=False, comment="Has IPMI/BMC access (servers)")
    has_pdu = Column(Boolean, default=False, comment="Connected to PDU")
    console_link = Column(String(500), nullable=True, comment="Link to console interface")
    ipmi_link = Column(String(500), nullable=True, comment="Link to IPMI/BMC interface")
    pdu_link = Column(String(500), nullable=True, comment="Link to PDU interface")

    # Management Interface Credentials
    ipmi_username = Column(String(100), nullable=True, comment="IPMI/BMC username")
    ipmi_password = Column(String(200), nullable=True, comment="IPMI/BMC password (plain text, internal use only - for debugging/emergency access)")
    console_username = Column(String(100), nullable=True, comment="Console username")
    console_password = Column(String(200), nullable=True, comment="Console password (plain text, internal use only - for debugging/emergency access)")

    # Additional Metadata
    description = Column(Text, nullable=True, comment="Asset description")
    notes = Column(Text, nullable=True, comment="Internal notes")
    custom_fields = Column(JSON, default={}, comment="Custom fields (JSON object)")

    # Photo and Documentation
    photo_urls = Column(JSON, default=[], comment="Array of photo URLs")
    barcode_data = Column(String(200), nullable=True, comment="Barcode data")
    qr_code_data = Column(String(500), nullable=True, comment="QR code data")
    documentation_urls = Column(JSON, default=[], comment="Array of documentation URLs")

    # NetBox Sync
    netbox_id = Column(Integer, nullable=True, index=True, comment="NetBox device ID (for sync)")
    netbox_last_sync = Column(DateTime, nullable=True, comment="Last NetBox sync timestamp")
    
    # NetBox Bidirectional Sync (Premium Feature)
    last_synced_at = Column(DateTime, nullable=True, comment="Last successful bidirectional sync (premium)")
    last_modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last modification time (for conflict detection)")
    sync_metadata = Column(JSON, default={}, comment="Sync metadata: conflicts, etags, sync source")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, comment="Creation timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last update timestamp")
    deployed_at = Column(DateTime, nullable=True, comment="Deployment timestamp")
    decommissioned_at = Column(DateTime, nullable=True, comment="Decommission timestamp")

    # Relationships
    datacenter = relationship("Datacenter", back_populates="assets")
    rack = relationship("Rack", back_populates="assets")
    storage_container = relationship("StorageContainer", back_populates="assets")
    lifecycle_events = relationship("AssetLifecycleEvent", back_populates="asset", cascade="all, delete-orphan")
    container = relationship("Asset", remote_side=[id], backref="contained_assets")  # Self-referential: parent container
    maintenance_records = relationship("MaintenanceRecord", back_populates="asset", cascade="all, delete-orphan")
    maintenance_predictions = relationship("MaintenancePrediction", back_populates="asset", cascade="all, delete-orphan")
    network_ports = relationship("NetworkPort", foreign_keys="NetworkPort.asset_id", back_populates="asset", cascade="all, delete-orphan")
    # Connection relationships - use passive_deletes=True to let database handle cascade deletes
    cable_connections = relationship("Connection", foreign_keys="Connection.cable_asset_id", back_populates="cable_asset", passive_deletes=True)
    device_connections = relationship("Connection", foreign_keys="Connection.device_asset_id", back_populates="device_asset", passive_deletes=True)

    def __repr__(self):
        return f"<Asset {self.asset_tag} - {self.manufacturer} {self.model}>"


class AssetLifecycleEvent(Base, TenantMixin):
    """
    Track all lifecycle events for assets.
    
    This model maintains an audit trail of all status changes, location changes,
    and other lifecycle events for assets. Events are automatically created
    when assets are updated.
    
    Event Types:
        - received: Asset was received
        - deployed: Asset was deployed to a rack
        - moved: Asset location changed
        - maintenance: Asset entered/left maintenance
        - decommissioned: Asset was decommissioned
        - status_change: Asset status changed
        - etc.
    """
    __tablename__ = "asset_lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, comment="Reference to asset")

    event_type = Column(String(50), nullable=False, comment="Event type (received, deployed, moved, etc.)")
    event_timestamp = Column(DateTime, default=datetime.utcnow, index=True, comment="When the event occurred")

    old_status = Column(String(50), nullable=True, comment="Previous status (if status changed)")
    new_status = Column(String(50), nullable=True, comment="New status (if status changed)")

    old_location = Column(String(200), nullable=True, comment="Previous location (if location changed)")
    new_location = Column(String(200), nullable=True, comment="New location (if location changed)")

    performed_by = Column(String(100), nullable=True, comment="User who performed the action")
    notes = Column(Text, nullable=True, comment="Additional notes about the event")
    event_metadata = Column(JSON, default={}, comment="Additional event metadata (JSON)")

    created_at = Column(DateTime, default=datetime.utcnow, comment="Record creation timestamp")

    # Relationships
    asset = relationship("Asset", back_populates="lifecycle_events")

    def __repr__(self):
        return f"<LifecycleEvent {self.event_type} for Asset {self.asset_id}>"
