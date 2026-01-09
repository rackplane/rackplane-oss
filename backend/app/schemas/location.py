# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Location Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.schemas.asset import AssetResponse
    from app.schemas.storage_container import StorageContainerResponse


class DatacenterCreate(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    city: Optional[str] = None
    total_power_capacity_kw: Optional[float] = None
    total_cooling_capacity_btu: Optional[float] = None


class RoomCreate(BaseModel):
    datacenter_id: int
    name: str
    code: str
    floor_number: Optional[int] = None
    power_capacity_kw: Optional[float] = None
    aisle_configuration: Optional[str] = None


class RackCreate(BaseModel):
    datacenter_id: int
    room_id: Optional[int] = None
    name: str
    code: str
    height_u: int = 42
    power_capacity_watts: Optional[float] = None
    row: Optional[str] = None
    position: Optional[str] = None


class RackCapacityResponse(BaseModel):
    rack_id: int
    rack_code: str
    total_u_space: int
    used_u_space: int
    available_u_space: int
    u_space_utilization_percent: float
    total_power_capacity_watts: float
    used_power_watts: float
    available_power_watts: float
    power_utilization_percent: float
    space_warning: bool
    power_warning: bool

    class Config:
        from_attributes = True


class RackContentCounts(BaseModel):
    """Counts of rack content"""
    devices: int
    storage: int
    total_u_used: int


class RackContentResponse(BaseModel):
    """Vertical-aware rack content with smart prioritization"""
    rack: dict  # RackResponse would create circular import, use dict
    devices: Optional[List[dict]] = None  # AssetResponse
    storage_containers: Optional[List[dict]] = None  # StorageContainerResponse
    vertical_pack: str
    recommended_view: str
    counts: RackContentCounts

    class Config:
        from_attributes = True
