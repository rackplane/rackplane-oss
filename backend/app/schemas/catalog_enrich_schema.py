# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog Enrichment Schema
For manually enriching CatalogSKU products with additional data.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CatalogEnrichSchema(BaseModel):
    """Schema for enriching a CatalogSKU with manual data."""
    
    # Pricing
    price_usd: Optional[float] = Field(None, description="Price in USD")
    
    # Availability
    stock_status: Optional[str] = Field(None, description="Stock status (e.g., 'In Stock', '14 left')")
    lead_time: Optional[str] = Field(None, description="Delivery estimate (e.g., 'Ships Jan 3')")
    
    # Compatibility - list of compatible part numbers
    compatibility: Optional[List[str]] = Field(None, description="Compatible parts (e.g., ['Cisco QSFP-40G-LR4-S'])")
    
    # Additional specs to merge into specifications JSON
    specifications: Optional[Dict[str, Any]] = Field(None, description="Additional specifications")
    
    # Descriptive info
    description: Optional[str] = Field(None, description="Product description")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    
    # URLs
    datasheet_url: Optional[str] = Field(None, description="Link to datasheet")
    vendor_url: Optional[str] = Field(None, description="Link to vendor product page")
    image_url: Optional[str] = Field(None, description="Link to product image")

    class Config:
        json_schema_extra = {
            "example": {
                "price_usd": 225.00,
                "stock_status": "10 left",
                "lead_time": "Ships Jan 3",
                "compatibility": ["Cisco QSFP-40G-LR4-S", "Arista 7260QX"],
                "specifications": {"wavelength": "1310nm", "reach": "10km"},
                "description": "40GBASE-LR4 QSFP+ transceiver for single-mode fiber",
                "manufacturer": "HPC Optics"
            }
        }


class CatalogEnrichResponse(BaseModel):
    """Response after enriching a catalog product."""
    
    id: int
    vendor: str
    sku: str
    name: str
    price_usd: Optional[float]
    stock_status: Optional[str]
    lead_time: Optional[str]
    compatibility: Optional[List[str]]
    specifications: Optional[Dict[str, Any]]
    description: Optional[str]
    manufacturer: Optional[str]
    message: str = "Product enriched successfully"
