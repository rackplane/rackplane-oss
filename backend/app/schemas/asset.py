# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Asset Schemas
Pydantic models for asset management

This module defines Pydantic schemas for asset (hardware inventory) management.
Schemas are used for request/response validation in asset endpoints.

Key Schemas:
- AssetBase: Base fields shared across asset schemas
- AssetCreate: Schema for creating new assets
- AssetUpdate: Schema for updating existing assets
- AssetResponse: Schema for API responses
- AssetListResponse: Paginated list response

Validation:
- Asset tag and serial number are required
- Status is validated against AssetStatus enum
- min_stock_threshold must be >= 1 if set (0 is converted to None)
- Custom field validators normalize status values
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from app.models.asset import AssetStatus


class AssetBase(BaseModel):
    """
    Base asset schema with common fields.
    
    This is the base class for all asset-related schemas. It contains
    fields that are common across create, update, and response schemas.
    
    Key Fields:
    - asset_tag: Unique identifier per tenant
    - serial_number: Serial number (unique per tenant)
    - asset_type: Type of asset (validated against asset_types table)
    - status: Lifecycle status (AssetStatus enum)
    - min_stock_threshold: Minimum stock level for storage boxes (>= 1 if set)
    """
    asset_tag: Optional[str] = Field(None, description="Unique asset tag per tenant (auto-generated if not provided)")
    serial_number: Optional[str] = Field(None, description="Serial number (unique per tenant, auto-generated if not provided)")
    asset_type: str = Field(..., description="Asset type (validated against asset_types table)")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    model: Optional[str] = Field(None, description="Model number")
    sku: Optional[str] = Field(None, description="SKU/part number")
    status: AssetStatus = Field(default=AssetStatus.RECEIVED, description="Lifecycle status")
    on_loan: Optional[bool] = Field(False, description="Whether asset is on loan")
    loan_direction: Optional[str] = Field(None, description="Loan direction: 'to_us' or 'from_us'")
    loan_party: Optional[str] = Field(None, description="Who we loaned it to, or who loaned it to us")
    loan_source: Optional[str] = Field(None, description="DEPRECATED: Legacy field for backward compatibility")
    height_u: Optional[int] = Field(None, description="Height in rack units (U)")
    power_consumption_watts: Optional[float] = Field(None, description="Power consumption in watts")
    hostname: Optional[str] = Field(None, description="Hostname (unique per tenant)")
    description: Optional[str] = Field(None, description="Asset description")
    datacenter_id: Optional[int] = Field(None, description="Datacenter location ID")
    rack_id: Optional[int] = Field(None, description="Rack location ID")
    rack_position_start: Optional[int] = Field(None, description="Starting U position in rack")
    rack_position_end: Optional[int] = Field(None, description="Ending U position (for multi-U devices)")
    storage_container_id: Optional[int] = Field(None, description="Storage container ID")
    storage_location: Optional[str] = Field(None, description="Legacy free-text storage location")
    container_id: Optional[int] = Field(None, description="Parent asset (box/bin) containing this asset")
    min_stock_threshold: Optional[int] = Field(None, ge=1, description="Minimum stock level for reorder alerts (storage boxes only). Must be >= 1 if set.")
    
    # Cable specific fields (transitional - mapped to custom_fields for Asset model, or network_cables table)
    connector_type_end_a: Optional[str] = Field(None, description="Connector type for End A (e.g. RJ45, LC, MPO)")
    connector_type_end_b: Optional[str] = Field(None, description="Connector type for End B (e.g. RJ45, LC, MPO)")
    
    @field_validator('min_stock_threshold', mode='before')
    @classmethod
    def validate_min_stock_threshold(cls, v):
        """
        Validate min_stock_threshold: allow None, but if set, must be >= 1.
        
        Converts 0 to None since 0 is not a valid threshold value.
        Only storage boxes should have this field set.
        """
        if v is None:
            return None
        if v == 0:
            return None  # Convert 0 to None (0 is not allowed)
        if isinstance(v, (int, float)) and v < 1:
            raise ValueError("min_stock_threshold must be >= 1 if set")
        return v
    
    # Financial fields
    purchase_cost: Optional[float] = None
    purchase_date: Optional[datetime] = None
    currency: Optional[str] = "USD"
    supplier: Optional[str] = None
    po_number: Optional[str] = None
    # Warranty fields
    warranty_start_date: Optional[datetime] = Field(None, description="Warranty start date")
    warranty_end_date: Optional[datetime] = Field(None, description="Warranty expiration/end date")
    # Custom fields (for cables, transceivers, etc.)
    custom_fields: Optional[Dict[str, Any]] = {}

    # Management interface tracking
    has_console: Optional[bool] = False
    has_ipmi: Optional[bool] = False
    has_pdu: Optional[bool] = False
    console_link: Optional[str] = None
    ipmi_link: Optional[str] = None
    pdu_link: Optional[str] = None
    # Management interface credentials
    # Note: Passwords stored in plain text for internal debugging/emergency access only
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None  # Plain text, internal use only
    console_username: Optional[str] = None
    console_password: Optional[str] = None  # Plain text, internal use only
    # Images
    photo_urls: Optional[List[str]] = []
    # Note: Base64 data URLs are allowed for backup/restore purposes (JSON format)
    
    @field_validator('status', mode='before')
    @classmethod
    def normalize_status(cls, v):
        """Normalize status value to lowercase to match enum values"""
        if isinstance(v, str):
            # Convert to lowercase and try to match enum value
            v_lower = v.lower()
            # Map common variations to correct enum values
            status_map = {
                'in_storage': AssetStatus.IN_STORAGE,
                'in-storage': AssetStatus.IN_STORAGE,
                'instorage': AssetStatus.IN_STORAGE,
                'rma': AssetStatus.RMA,
                'retired': AssetStatus.RETIRED,
                'ordered': AssetStatus.ORDERED,
                'in_transit': AssetStatus.IN_TRANSIT,
                'in-transit': AssetStatus.IN_TRANSIT,
                'received': AssetStatus.RECEIVED,
                'staging': AssetStatus.STAGING,
                'deployed': AssetStatus.DEPLOYED,
                'active': AssetStatus.ACTIVE,
                'maintenance': AssetStatus.MAINTENANCE,
                'failed': AssetStatus.FAILED,
                'decommissioned': AssetStatus.DECOMMISSIONED,
                'disposed': AssetStatus.DISPOSED,
            }
            if v_lower in status_map:
                return status_map[v_lower]
            # Try to find matching enum by value
            try:
                return AssetStatus(v_lower)
            except ValueError:
                # If not found, try by name (case-insensitive)
                for status in AssetStatus:
                    if status.name.upper() == v.upper():
                        return status
                raise ValueError(f"Invalid status: {v}")
        return v


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    asset_tag: Optional[str] = None
    serial_number: Optional[str] = None
    asset_type: Optional[str] = None  # Dynamic type validated against asset_types table
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    status: Optional[AssetStatus] = None
    
    @field_validator('status', mode='before')
    @classmethod
    def normalize_status(cls, v):
        """Normalize status value to lowercase to match enum values"""
        if v is None:
            return v
        if isinstance(v, str):
            # Convert to lowercase and try to match enum value
            v_lower = v.lower()
            # Map common variations to correct enum values
            status_map = {
                'in_storage': AssetStatus.IN_STORAGE,
                'in-storage': AssetStatus.IN_STORAGE,
                'instorage': AssetStatus.IN_STORAGE,
                'rma': AssetStatus.RMA,
                'retired': AssetStatus.RETIRED,
                'ordered': AssetStatus.ORDERED,
                'in_transit': AssetStatus.IN_TRANSIT,
                'in-transit': AssetStatus.IN_TRANSIT,
                'received': AssetStatus.RECEIVED,
                'staging': AssetStatus.STAGING,
                'deployed': AssetStatus.DEPLOYED,
                'active': AssetStatus.ACTIVE,
                'maintenance': AssetStatus.MAINTENANCE,
                'failed': AssetStatus.FAILED,
                'decommissioned': AssetStatus.DECOMMISSIONED,
                'disposed': AssetStatus.DISPOSED,
            }
            if v_lower in status_map:
                return status_map[v_lower]
            # Try to find matching enum by value
            try:
                return AssetStatus(v_lower)
            except ValueError:
                # If not found, try by name (case-insensitive)
                for status in AssetStatus:
                    if status.name.upper() == v.upper():
                        return status
                raise ValueError(f"Invalid status: {v}")
        return v
    on_loan: Optional[bool] = None
    loan_direction: Optional[str] = None
    loan_party: Optional[str] = None
    loan_source: Optional[str] = None
    hostname: Optional[str] = None
    primary_ip: Optional[str] = None
    height_u: Optional[int] = None
    power_consumption_watts: Optional[float] = None
    description: Optional[str] = None
    rack_id: Optional[int] = None
    datacenter_id: Optional[int] = None
    rack_position_start: Optional[int] = None
    storage_container_id: Optional[int] = None
    storage_location: Optional[str] = None
    container_id: Optional[int] = None  # Self-referential: asset inside another asset (box/bin)
    
    # Cable specific fields
    connector_type_end_a: Optional[str] = None
    connector_type_end_b: Optional[str] = None

    min_stock_threshold: Optional[int] = Field(None, ge=1, description="Minimum stock level for reorder alerts (for storage boxes). Must be >= 1 if set.")
    
    @field_validator('min_stock_threshold', mode='before')
    @classmethod
    def validate_update_min_stock_threshold(cls, v):
        """Allow None, but if set, must be >= 1"""
        if v is None:
            return None
        if v == 0:
            return None  # Convert 0 to None (0 is not allowed)
        if isinstance(v, (int, float)) and v < 1:
            raise ValueError("min_stock_threshold must be >= 1 if set")
        return v
    
    notes: Optional[str] = None
    # Financial fields
    purchase_cost: Optional[float] = None
    purchase_date: Optional[datetime] = None
    currency: Optional[str] = None
    supplier: Optional[str] = None
    po_number: Optional[str] = None
    # Warranty fields
    warranty_start_date: Optional[datetime] = Field(None, description="Warranty start date")
    warranty_end_date: Optional[datetime] = Field(None, description="Warranty expiration/end date")
    # Custom fields (for cables, transceivers, etc.)
    custom_fields: Optional[Dict[str, Any]] = None
    # Management interface tracking
    has_console: Optional[bool] = None
    has_ipmi: Optional[bool] = None
    has_pdu: Optional[bool] = None
    console_link: Optional[str] = None
    ipmi_link: Optional[str] = None
    pdu_link: Optional[str] = None
    # Management interface credentials
    # Note: Passwords stored in plain text for internal debugging/emergency access only
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None  # Plain text, internal use only
    console_username: Optional[str] = None
    console_password: Optional[str] = None  # Plain text, internal use only
    # Images
    photo_urls: Optional[List[str]] = None
    
    @field_validator('status', mode='before')
    @classmethod
    def normalize_update_status(cls, v):
        """Normalize status value to lowercase to match enum values"""
        if v is None:
            return v
        if isinstance(v, str):
            # Convert to lowercase and try to match enum value
            v_lower = v.lower()
            # Map common variations to correct enum values
            status_map = {
                'in_storage': AssetStatus.IN_STORAGE,
                'in-storage': AssetStatus.IN_STORAGE,
                'instorage': AssetStatus.IN_STORAGE,
                'rma': AssetStatus.RMA,
                'retired': AssetStatus.RETIRED,
                'ordered': AssetStatus.ORDERED,
                'in_transit': AssetStatus.IN_TRANSIT,
                'in-transit': AssetStatus.IN_TRANSIT,
                'received': AssetStatus.RECEIVED,
                'staging': AssetStatus.STAGING,
                'deployed': AssetStatus.DEPLOYED,
                'active': AssetStatus.ACTIVE,
                'maintenance': AssetStatus.MAINTENANCE,
                'failed': AssetStatus.FAILED,
                'decommissioned': AssetStatus.DECOMMISSIONED,
                'disposed': AssetStatus.DISPOSED,
            }
            if v_lower in status_map:
                return status_map[v_lower]
            # Try to find matching enum by value
            try:
                return AssetStatus(v_lower)
            except ValueError:
                # If not found, try by name (case-insensitive)
                for status in AssetStatus:
                    if status.name.upper() == v.upper():
                        return status
                raise ValueError(f"Invalid status: {v}")
        return v


class AssetResponse(AssetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    assets: List[AssetResponse]


class EOLWarningResponse(BaseModel):
    asset: AssetResponse
    eol_date: datetime
    days_remaining: int
