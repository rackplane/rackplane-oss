# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Container Stock Threshold Schemas
Pydantic schemas for managing per-item-type stock thresholds
"""

from pydantic import BaseModel, Field
from typing import Optional


class ContainerStockThresholdBase(BaseModel):
    """Base schema for container stock thresholds"""
    asset_type: str = Field(..., description="Asset type (e.g., 'dac_cable')")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name (optional - None means 'any manufacturer')")
    model: Optional[str] = Field(None, description="Model name (optional - None means 'any model')")
    min_threshold: int = Field(..., ge=1, description="Minimum stock level for this item type (must be >= 1)")
    max_quantity: Optional[int] = Field(None, ge=1, description="Maximum stock level (Par Level)")


class ContainerStockThresholdCreate(ContainerStockThresholdBase):
    """Schema for creating a new stock threshold"""
    storage_container_id: int = Field(..., description="Storage container ID")


class ContainerStockThresholdUpdate(BaseModel):
    """Schema for updating a stock threshold"""
    min_threshold: Optional[int] = Field(None, ge=1, description="Minimum stock level (must be >= 1)")
    max_quantity: Optional[int] = Field(None, ge=1, description="Maximum stock level (Par Level)")


class ContainerStockThresholdResponse(ContainerStockThresholdBase):
    """Schema for stock threshold response"""
    id: int
    storage_container_id: int
    
    class Config:
        from_attributes = True


