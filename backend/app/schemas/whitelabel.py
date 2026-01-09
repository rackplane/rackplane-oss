# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
White-Label Configuration Schemas
Pydantic models for tenant configuration API endpoints

These schemas define the structure for branding, terminology,
and vertical pack configuration in the white-label platform.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, HttpUrl
import re


class BrandingConfig(BaseModel):
    """Complete branding configuration for a tenant."""
    name: Optional[str] = Field(None, max_length=100, description="White-label product name")
    logo_url: Optional[HttpUrl] = Field(None, description="URL to custom logo")
    favicon_url: Optional[HttpUrl] = Field(None, description="URL to custom favicon")
    primary_color: str = Field("#6366f1", description="Primary brand color (hex)")
    secondary_color: str = Field("#4f46e5", description="Secondary brand color (hex)")
    accent_color: str = Field("#818cf8", description="Accent color (hex)")
    font_family: str = Field("Inter", description="Font family name")
    custom_domain: Optional[str] = Field(None, description="Custom domain for tenant")
    email_from_name: Optional[str] = Field(None, description="Email sender name")
    email_from_address: Optional[str] = Field(None, description="Email sender address")
    
    @validator('primary_color', 'secondary_color', 'accent_color')
    def validate_hex_color(cls, v):
        if v and not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #6366f1 or #63f)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "MercyTrack",
                "logo_url": "https://example.com/logo.png",
                "primary_color": "#0066CC",
                "secondary_color": "#004499",
                "accent_color": "#3399FF",
                "font_family": "Roboto",
                "custom_domain": "track.mercyhospital.org"
            }
        }


class BrandingConfigUpdate(BaseModel):
    """Partial update for branding configuration."""
    name: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[HttpUrl] = None
    favicon_url: Optional[HttpUrl] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    custom_domain: Optional[str] = None
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    
    @validator('primary_color', 'secondary_color', 'accent_color')
    def validate_hex_color(cls, v):
        if v and not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #6366f1 or #63f)')
        return v


class Terminology(BaseModel):
    """Complete terminology configuration for a tenant."""
    item: str = Field("Asset", description="Singular item term")
    items: str = Field("Assets", description="Plural items term")
    location: str = Field("Datacenter", description="Singular location term")
    locations: str = Field("Datacenters", description="Plural locations term")
    bin: str = Field("Rack", description="Singular bin term")
    bins: str = Field("Racks", description="Plural bins term")
    check_out: str = Field("Deploy", description="Check out action term")
    check_in: str = Field("Return", description="Check in action term")
    category: str = Field("Asset Type", description="Singular category term")
    categories: str = Field("Asset Types", description="Plural categories term")
    lifecycle: str = Field("Status", description="Lifecycle/status term")
    storage: str = Field("Storage", description="Storage area term")
    stock: str = Field("Inventory", description="Stock/inventory term")
    container: str = Field("Storage Container", description="Container term")
    containers: str = Field("Storage Containers", description="Containers term")
    
    class Config:
        json_schema_extra = {
            "example": {
                "item": "Supply",
                "items": "Supplies",
                "location": "Facility",
                "bin": "Cabinet",
                "check_out": "Dispense",
                "check_in": "Restock",
                "category": "Supply Category"
            }
        }


class TerminologyUpdate(BaseModel):
    """Partial update for terminology configuration."""
    item: Optional[str] = Field(None, max_length=50)
    items: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=50)
    locations: Optional[str] = Field(None, max_length=50)
    bin: Optional[str] = Field(None, max_length=50)
    bins: Optional[str] = Field(None, max_length=50)
    check_out: Optional[str] = Field(None, max_length=50)
    check_in: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    categories: Optional[str] = Field(None, max_length=50)
    lifecycle: Optional[str] = Field(None, max_length=50)
    storage: Optional[str] = Field(None, max_length=50)
    stock: Optional[str] = Field(None, max_length=50)
    container: Optional[str] = Field(None, max_length=50)
    containers: Optional[str] = Field(None, max_length=50)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class VerticalFeatures(BaseModel):
    """Vertical-specific feature flags."""
    # Healthcare/warehouse feature toggles
    expiration_tracking: bool = Field(False, description="Enable expiration date tracking")
    par_levels: bool = Field(False, description="Enable par level alerts")
    lot_tracking: bool = Field(False, description="Enable lot/batch number tracking")
    department_attribution: bool = Field(False, description="Enable department cost tracking")
    
    # Field visibility toggles (True = show field, datacenter default)
    show_power_watts: bool = Field(True, description="Show power consumption field")
    show_warranty_info: bool = Field(True, description="Show warranty start/end date fields")
    show_hostname: bool = Field(True, description="Show hostname field")
    show_rack_position: bool = Field(True, description="Show height (U) and rack position fields")
    show_datacenter_location: bool = Field(True, description="Show datacenter/rack location fields")
    show_sku_lookup: bool = Field(True, description="Show SKU field with catalog lookup")
    show_loan_tracking: bool = Field(True, description="Show loan tracking checkbox and fields")
    
    class Config:
        json_schema_extra = {
            "example": {
                "expiration_tracking": True,
                "par_levels": True,
                "lot_tracking": False,
                "department_attribution": True,
                "show_power_watts": False,
                "show_warranty_info": False,
                "show_hostname": False
            }
        }


class VerticalFeaturesUpdate(BaseModel):
    """Partial update for vertical features."""
    # Healthcare/warehouse feature toggles
    expiration_tracking: Optional[bool] = None
    par_levels: Optional[bool] = None
    lot_tracking: Optional[bool] = None
    department_attribution: Optional[bool] = None
    
    # Field visibility toggles
    show_power_watts: Optional[bool] = None
    show_warranty_info: Optional[bool] = None
    show_hostname: Optional[bool] = None
    show_rack_position: Optional[bool] = None
    show_datacenter_location: Optional[bool] = None
    show_sku_lookup: Optional[bool] = None
    show_loan_tracking: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class TenantConfigResponse(BaseModel):
    """Complete tenant configuration response."""
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    vertical_pack: str
    branding: BrandingConfig
    terminology: Terminology
    vertical_features: VerticalFeatures
    
    class Config:
        from_attributes = True


class VerticalPreset(BaseModel):
    """Vertical preset information."""
    name: str = Field(..., description="Vertical pack name")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Description of the vertical")
    terminology: Dict[str, str] = Field(..., description="Default terminology")
    default_features: Dict[str, bool] = Field(..., description="Default feature flags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "healthcare",
                "display_name": "Healthcare",
                "description": "Hospital supply room and medical equipment management",
                "terminology": {
                    "item": "Supply",
                    "bin": "Cabinet"
                },
                "default_features": {
                    "expiration_tracking": True,
                    "par_levels": True
                }
            }
        }


class VerticalPresetsResponse(BaseModel):
    """Response containing all available vertical presets."""
    presets: List[VerticalPreset]


class ApplyPresetRequest(BaseModel):
    """Request to apply a vertical preset to a tenant."""
    vertical: str = Field(..., description="Vertical pack name to apply")
    override_custom: bool = Field(False, description="Replace all custom terminology with preset defaults")
    
    @validator('vertical')
    def validate_vertical(cls, v):
        valid_verticals = ['datacenter', 'healthcare', 'warehouse']
        if v not in valid_verticals:
            raise ValueError(f"Invalid vertical. Options: {valid_verticals}")
        return v
