# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Asset Type Pydantic Schemas"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AssetTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique identifier (lowercase, no spaces)")
    display_name: str = Field(..., min_length=1, max_length=200, description="Display name")
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict, description="Feature flags (e.g., networkable for network-capable assets)")


class AssetTypeCreate(AssetTypeBase):
    pass


class AssetTypeUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    features: Optional[Dict[str, Any]] = None


class AssetTypeResponse(AssetTypeBase):
    id: int
    is_active: bool
    is_system: bool
    features: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetTypeDeleteRequest(BaseModel):
    """Request schema for deleting asset types with options"""
    hard_delete: bool = Field(default=False, description="If true, permanently delete instead of soft delete")
    reassign_assets_to: Optional[int] = Field(None, description="Asset type ID to reassign assets to (if assets exist)")
    force_delete_system: bool = Field(default=False, description="Allow deletion of system types (admin only)")
