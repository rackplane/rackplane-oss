# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""PortTemplate Pydantic Schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PortDefinition(BaseModel):
    """Schema for a single port definition in a template"""
    port_number: str = Field(..., description="Port number")
    port_type: str = Field(..., description="Port type (rj45, sfp, qsfp, etc.)")
    speed_mbps: int = Field(..., description="Port speed in Mbps")
    duplex: str = Field("full", description="Duplex mode")
    poe_capable: bool = Field(False, description="Supports PoE")
    poe_max_watts: float = Field(0.0, description="Max PoE watts")


class PortTemplateBase(BaseModel):
    """Base schema for PortTemplate"""
    manufacturer: str = Field(..., max_length=100)
    model: str = Field(..., max_length=200)
    description: Optional[str] = None
    port_definitions: List[PortDefinition] = Field(default_factory=list)


class PortTemplateCreate(PortTemplateBase):
    """Schema for creating a PortTemplate"""
    pass


class PortTemplateUpdate(BaseModel):
    """Schema for updating a PortTemplate"""
    description: Optional[str] = None
    port_definitions: Optional[List[PortDefinition]] = None


class PortTemplateResponse(PortTemplateBase):
    """Schema for PortTemplate response"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    """Schema for applying a template to a device"""
    asset_id: int = Field(..., description="Device to apply template to")
    template_id: int = Field(..., description="Template to apply")
    overwrite: bool = Field(False, description="Overwrite existing ports")
