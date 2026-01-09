# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
CableAssembly Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AssemblyStatus(str, Enum):
    """Cable assembly status"""
    available = "available"
    deployed = "deployed"
    reserved = "reserved"
    maintenance = "maintenance"


class CableAssemblyCreate(BaseModel):
    """Schema for creating a cable assembly"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    fiber_cable_id: int
    transceiver_a_id: int
    transceiver_b_id: int


class CableAssemblyUpdate(BaseModel):
    """Schema for updating a cable assembly"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[AssemblyStatus] = None


class AssetSummary(BaseModel):
    """Summary of an asset for embedding in responses"""
    id: int
    asset_tag: str
    asset_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class CableAssemblyResponse(BaseModel):
    """Schema for cable assembly response"""
    id: int
    name: str
    description: Optional[str] = None
    status: AssemblyStatus
    fiber_cable_id: int
    transceiver_a_id: int
    transceiver_b_id: int
    fiber_cable: Optional[AssetSummary] = None
    transceiver_a: Optional[AssetSummary] = None
    transceiver_b: Optional[AssetSummary] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeployAssemblyRequest(BaseModel):
    """Request to deploy a cable assembly to two ports"""
    port_a_id: int
    port_b_id: int
