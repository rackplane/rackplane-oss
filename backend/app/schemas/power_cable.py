# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Power Cable Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.power_cable import PowerConnectorType


class PowerCableBase(BaseModel):
    name: str
    connector_end_a: PowerConnectorType
    connector_end_b: PowerConnectorType
    length_meters: Optional[float] = None
    voltage: str
    amperage: Optional[str] = None
    wire_gauge: Optional[str] = None
    color: Optional[str] = None
    storage_container_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None
    notes: Optional[str] = None
    quantity: int = 1


class PowerCableCreate(PowerCableBase):
    pass


class PowerCableUpdate(BaseModel):
    name: Optional[str] = None
    connector_end_a: Optional[PowerConnectorType] = None
    connector_end_b: Optional[PowerConnectorType] = None
    length_meters: Optional[float] = None
    voltage: Optional[str] = None
    amperage: Optional[str] = None
    wire_gauge: Optional[str] = None
    color: Optional[str] = None
    storage_container_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None
    notes: Optional[str] = None
    quantity: Optional[int] = None


class PowerCableResponse(PowerCableBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
