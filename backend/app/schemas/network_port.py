# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""NetworkPort Pydantic Schemas"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.network import PortType, PortStatus, LaneEncoding


class NetworkPortBase(BaseModel):
    """Base schema for NetworkPort"""
    port_number: str = Field(..., max_length=50, description="Port number (e.g., '1', '24')")
    port_name: Optional[str] = Field(None, max_length=200, description="Port name (e.g., 'GigabitEthernet0/1')")
    port_label: Optional[str] = Field(None, max_length=200, description="User-friendly label")
    port_type: PortType = Field(..., description="Port type (rj45, sfp, qsfp, etc.)")
    speed_mbps: Optional[int] = Field(None, description="Port speed in Mbps")
    lane_encoding: Optional[LaneEncoding] = Field(LaneEncoding.unknown, description="Lane encoding: nrz, pam4, both, or unknown")
    duplex: Optional[str] = Field(None, max_length=20, description="full, half, or auto")
    status: PortStatus = Field(PortStatus.INACTIVE, description="Port status")
    enabled: bool = Field(True, description="Port administratively enabled")
    poe_capable: bool = Field(False, description="Port supports PoE")
    poe_enabled: bool = Field(False, description="PoE currently enabled")
    poe_power_watts: Optional[float] = Field(None, description="PoE power in watts")
    description: Optional[str] = Field(None, description="Port description")

    @field_validator('lane_encoding', mode='before')
    @classmethod
    def normalize_lane_encoding(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class NetworkPortCreate(NetworkPortBase):
    """Schema for creating a NetworkPort"""
    asset_id: int = Field(..., description="Asset (device) this port belongs to")


class NetworkPortUpdate(BaseModel):
    """Schema for updating a NetworkPort (all fields optional)"""
    port_name: Optional[str] = None
    port_label: Optional[str] = None
    port_type: Optional[PortType] = None
    speed_mbps: Optional[int] = None
    lane_encoding: Optional[LaneEncoding] = None
    duplex: Optional[str] = None
    status: Optional[PortStatus] = None
    enabled: Optional[bool] = None
    poe_capable: Optional[bool] = None
    poe_enabled: Optional[bool] = None
    poe_power_watts: Optional[float] = None
    description: Optional[str] = None
    # Installed transceiver asset (for fiber connections)
    installed_transceiver_id: Optional[int] = None

    @field_validator('lane_encoding', mode='before')
    @classmethod
    def normalize_lane_encoding(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class NetworkPortResponse(NetworkPortBase):
    """Schema for NetworkPort response"""
    id: int
    asset_id: int
    tenant_id: int
    connected_port_id: Optional[int] = None
    connection_id: Optional[int] = None
    installed_transceiver_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NetworkPortListResponse(BaseModel):
    """Schema for list of NetworkPorts"""
    ports: List[NetworkPortResponse]
    total: int
