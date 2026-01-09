# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Network Cable Pydantic Schemas"""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.network_cable import CableType, ConnectorType

# List of valid connector types for ends A and B
VALID_CONNECTORS = [
    "OSFP_FIN", "OSFP_FLT", "OSFP", "QSFP_DD", "QSFP112", "QSFP56", "QSFP28", "QSFP_PLUS",
    "SFP28", "SFP_PLUS", "SFP", "LC", "MPO", "MTP", "SC", "FC", "ST",
    "Cat5e", "Cat6", "Cat6a", "Cat7", "Cat8", "Power"
]

class NetworkCableBase(BaseModel):
    name: str
    cable_type: CableType
    connector_type: ConnectorType
    connector_type_end_a: Optional[str] = None
    connector_type_end_b: Optional[str] = None
    speed: str
    length_meters: Optional[float] = None
    breakout: Optional[str] = None
    fiber_mode: Optional[str] = None
    wavelength: Optional[str] = None
    storage_container_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    part_number: Optional[str] = None
    notes: Optional[str] = None
    quantity: int = 1

    @field_validator('connector_type_end_a', 'connector_type_end_b')
    @classmethod
    def validate_connector_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in VALID_CONNECTORS:
            # We allow it for now but maybe log a warning or be strict
            # For strict mode: raise ValueError(f"Invalid connector type: {v}")
            pass
        return v


class NetworkCableCreate(NetworkCableBase):
    pass


class NetworkCableUpdate(BaseModel):
    name: Optional[str] = None
    cable_type: Optional[CableType] = None
    connector_type: Optional[ConnectorType] = None
    connector_type_end_a: Optional[str] = None
    connector_type_end_b: Optional[str] = None
    speed: Optional[str] = None
    length_meters: Optional[float] = None
    breakout: Optional[str] = None
    fiber_mode: Optional[str] = None
    wavelength: Optional[str] = None
    storage_container_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    part_number: Optional[str] = None
    notes: Optional[str] = None
    quantity: Optional[int] = None


class NetworkCableResponse(NetworkCableBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
