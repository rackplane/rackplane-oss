# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog API Schemas
Pydantic models for Global Product Catalog responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class CatalogItem(BaseModel):
    """
    Standardized product item from the global catalog.
    """
    id: int = Field(..., description="Internal Catalog ID")
    vendor: str = Field(..., description="Vendor name (FS.com, etc)")
    vendor_product_id: str = Field(..., description="Vendor SKU/ID")
    name: str = Field(..., description="Product name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    part_number: Optional[str] = Field(None, description="Manufacturer Part Number")
    
    # Attributes
    category: Optional[str] = None
    speed: Optional[str] = None
    form_factor: Optional[str] = None
    interface: Optional[str] = None
    
    # Pricing
    price_usd: Optional[float] = None
    currency: str = "USD"
    
    # Attributes
    category: Optional[str] = None
    speed: Optional[str] = None
    form_factor: Optional[str] = None
    interface: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    
    # Pricing
    price_usd: Optional[float] = None
    currency: str = "USD"
    
    product_url: Optional[str] = None
    fetched_at: datetime = Field(..., description="Last sync timestamp")

    class Config:
        from_attributes = True

class CatalogSearchResponse(BaseModel):
    """
    Response for catalog search.
    """
    items: List[CatalogItem] = Field(..., description="Matching items")
    count: int = Field(..., description="Total items returned")

class RateLimitStatus(BaseModel):
    """
    Current API usage and limits.
    """
    hourly: Dict[str, int] = Field(..., description="Hourly details (used, limit, remaining)")
    daily: Dict[str, int] = Field(..., description="Daily details (used, limit, remaining)")
