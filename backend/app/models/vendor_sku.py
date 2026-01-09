# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
# OSS Version - GlobalProductCatalog FK removed

"""
Vendor SKU Catalog Model
Stores product catalogs from vendors like FS.com, NVIDIA, etc. for auto-populating asset fields
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, Index, text
from datetime import datetime
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class VendorSKU(Base, TenantMixin):
    """
    Vendor product catalog for auto-populating asset information.
    
    Stores SKU/product information from vendors like FS.com, NVIDIA, etc.
    When creating an asset, if the SKU matches, fields are automatically populated.
    """
    __tablename__ = "vendor_skus"

    id = Column(Integer, primary_key=True, index=True)
    
    # Vendor and Product Identification
    vendor = Column(String(100), nullable=False, index=True, comment="Vendor name (e.g., FS.com, NVIDIA)")
    sku = Column(String(200), nullable=False, index=True, comment="Product SKU (vendor's internal SKU number)")
    part_number = Column(String(200), nullable=True, index=True, comment="Product part number (customer-facing identifier, e.g., OSFP-800G-PC01)")
    name = Column(String(500), nullable=False, comment="Product name/description")
    manufacturer = Column(String(100), nullable=True, index=True, comment="Manufacturer (may differ from vendor)")
    
    # Asset Classification
    asset_type = Column(String(100), nullable=True, index=True, comment="Asset type this SKU represents (dac_cable, optical_transceiver, etc.)")
    
    # Product Specifications (stored as JSON for flexibility)
    specifications = Column(JSON, nullable=True, comment="Product specifications (speed, length, connectors, etc.)")
    
    # Pricing Information (optional)
    price_usd = Column(Float, nullable=True, comment="Price in USD")
    currency = Column(String(10), default="USD", comment="Currency code")
    price_updated_at = Column(DateTime, nullable=True, comment="When price was last updated")
    
    # GlobalProductCatalog FK removed for OSS - not available in community edition
    
    # Compatibility Information
    compatibility = Column(JSON, nullable=True, comment="Compatible devices/models")
    
    # Additional Information
    description = Column(Text, nullable=True, comment="Detailed product description")
    datasheet_url = Column(String(500), nullable=True, comment="Link to product datasheet")
    vendor_url = Column(String(500), nullable=True, comment="Link to vendor product page")
    image_url = Column(String(500), nullable=True, comment="Link to product image")
    
    # Metadata
    is_active = Column(Boolean, default=True, index=True, comment="Whether this SKU is still available/active")
    is_sample = Column(Boolean, default=False, index=True, comment="Whether this is a sample/preview SKU from RackPlane (tenant_id=0)")
    last_verified = Column(DateTime, nullable=True, comment="When this SKU information was last verified")
    notes = Column(Text, nullable=True, comment="Internal notes about this SKU")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Index for fast SKU lookups
    __table_args__ = (
        Index('ix_vendor_skus_tenant_vendor_sku_unique', 'tenant_id', text('lower(vendor)'), text('lower(sku)'), unique=True),
    )
    
    def __repr__(self):
        return f"<VendorSKU {self.vendor} {self.sku} - {self.name}>"
    
    def to_asset_data(self) -> dict:
        """
        Convert VendorSKU to asset field data for auto-population.
        
        Returns:
            Dictionary of asset fields that can be used to pre-fill asset creation form
        """
        data = {
            "manufacturer": self.manufacturer or self.vendor,
            "model": self.name,
            "sku": self.sku,
            "asset_type": self.asset_type,
        }
        
        # Extract specifications into asset fields
        if self.specifications:
            specs = self.specifications
            
            # DAC Cable fields
            if self.asset_type == "dac_cable":
                data["custom_fields"] = {
                    "dac_speed": specs.get("speed"),
                    "cable_length": specs.get("length"),
                    "dac_connector_a": specs.get("connector_a"),
                    "dac_connector_b": specs.get("connector_b"),
                    "dac_breakout": specs.get("breakout"),
                }
            
            # Fiber Cable fields
            elif self.asset_type == "fiber_cable":
                data["custom_fields"] = {
                    "cable_length": specs.get("length"),
                    "fiber_type": specs.get("fiber_type"),
                    "fiber_connector_a": specs.get("connector_a"),
                    "fiber_connector_b": specs.get("connector_b"),
                    "fiber_breakout": specs.get("breakout"),
                }
            
            # Optical Transceiver fields
            elif self.asset_type == "optical_transceiver":
                data["custom_fields"] = {
                    # Form factor - plugs into port (OSFP, QSFP28, QSFP-DD, etc.)
                    "transceiver_type": specs.get("transceiver_type") or specs.get("connector_a"),
                    # Optical connector type (LC, MPO, MTP, SC, etc.)
                    "fiber_connector": specs.get("fiber_connector") or specs.get("connector_type"),
                    "wavelength": specs.get("wavelength"),
                    "fiber_type": specs.get("fiber_type"),
                    "speed": specs.get("speed"),
                    "reach": specs.get("reach"),
                }
            
            # Generic custom fields for other types
            else:
                data["custom_fields"] = specs.copy()
        
        # Add pricing if available
        if self.price_usd:
            data["purchase_cost"] = self.price_usd
            data["currency"] = self.currency
        
        return data
