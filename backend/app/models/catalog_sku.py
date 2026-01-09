# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Global Catalog SKU Model
Source of truth for premium SKU data (Global Master Catalog).
Separated from tenant-specific VendorSKU table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, Index
from datetime import datetime
from app.core.database import Base

class CatalogSKU(Base):
    """
    Global Product Catalog (Read-Only for Users).
    Source of truth for premium SKU data.
    
    This table stores the master copy of all SKUs available in the RackPlane Global Catalog.
    It is NOT tenant-scoped.
    """
    __tablename__ = "catalog_skus"

    id = Column(Integer, primary_key=True, index=True)
    
    # Vendor and Product Identification
    vendor = Column(String(100), nullable=False, index=True, comment="Vendor name (e.g., FS.com, NVIDIA)")
    sku = Column(String(200), nullable=False, index=True, comment="Product SKU (vendor's internal SKU number)")
    part_number = Column(String(200), nullable=True, index=True, comment="Product part number (customer-facing identifier)")
    name = Column(String(500), nullable=False, comment="Product name/description")
    manufacturer = Column(String(100), nullable=True, index=True, comment="Manufacturer")
    
    # Asset Classification
    asset_type = Column(String(100), nullable=True, index=True, comment="Asset type (dac_cable, optical_transceiver, etc.)")
    
    # Product Specifications
    specifications = Column(JSON, nullable=True, comment="Product specifications (speed, length, connectors, etc.)")
    
    # Pricing
    price_usd = Column(Float, nullable=True, comment="Price in USD")
    currency = Column(String(10), default="USD", comment="Currency code")
    price_updated_at = Column(DateTime, nullable=True, comment="When price was last updated")
    
    # Compatibility
    compatibility = Column(JSON, nullable=True, comment="Compatible devices/models")
    
    # Additional Info
    description = Column(Text, nullable=True, comment="Detailed product description")
    datasheet_url = Column(String(500), nullable=True, comment="Link to product datasheet")
    vendor_url = Column(String(500), nullable=True, comment="Link to vendor product page")
    image_url = Column(String(500), nullable=True, comment="Link to product image")
    
    # Premium enrichment fields (available with sku_lookup feature)
    lead_time_days = Column(Integer, nullable=True, comment="Estimated lead time in days")
    in_stock = Column(Boolean, nullable=True, comment="Whether item is in stock")
    spec_sheet_url = Column(String(500), nullable=True, comment="Premium detailed spec sheet PDF")
    warranty_months = Column(Integer, nullable=True, comment="Warranty period in months")
    
    # System Metadata
    is_active = Column(Boolean, default=True, index=True, comment="Whether this SKU is visible")
    vertical = Column(String(50), default="datacenter", index=True, comment="Industry vertical (datacenter, healthcare, warehouse)")
    source_id = Column(String(100), nullable=True, index=True, comment="ID in the upstream RackPlane API (if synced)")
    last_synced_at = Column(DateTime, nullable=True, comment="When this record was last synced from upstream")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Index for fast lookups
    __table_args__ = (
        Index('ix_catalog_sku_vendor_sku', 'vendor', 'sku', unique=True),
    )
    
    def __repr__(self):
        return f"<CatalogSKU {self.vendor} {self.sku} - {self.name}>"

    def to_asset_data(self) -> dict:
        """
        Convert CatalogSKU to asset field data for auto-population.
        Duplicate logic from VendorSKU to ensure consistency.
        """
        data = {
            "manufacturer": self.manufacturer or self.vendor,
            "model": self.name,
            "sku": self.sku,
            "asset_type": self.asset_type,
        }
        
        if self.specifications:
            specs = self.specifications
            if self.asset_type == "dac_cable":
                data["custom_fields"] = {
                    "dac_speed": specs.get("speed"),
                    "cable_length": specs.get("length"),
                    "dac_connector_a": specs.get("connector_a"),
                    "dac_connector_b": specs.get("connector_b"),
                    "dac_breakout": specs.get("breakout"),
                }
            elif self.asset_type == "fiber_cable":
                data["custom_fields"] = {
                    "cable_length": specs.get("length"),
                    "fiber_type": specs.get("fiber_type"),
                    "fiber_connector_a": specs.get("connector_a"),
                    "fiber_connector_b": specs.get("connector_b"),
                    "fiber_breakout": specs.get("breakout"),
                }
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
            else:
                data["custom_fields"] = specs.copy()
        
        if self.price_usd:
            data["purchase_cost"] = self.price_usd
            data["currency"] = self.currency
            
        return data
