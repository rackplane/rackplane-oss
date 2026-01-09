# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Environmental Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SensorCreate(BaseModel):
    datacenter_id: int
    sensor_id: str
    sensor_name: str
    sensor_type: str
    location_description: Optional[str] = None
    warning_threshold_min: Optional[float] = None
    warning_threshold_max: Optional[float] = None
    unit_of_measure: Optional[str] = None


class ReadingCreate(BaseModel):
    sensor_id: int
    value: float
    unit: str
    timestamp: Optional[datetime] = None
    secondary_value: Optional[float] = None


class SensorResponse(BaseModel):
    id: int
    sensor_id: str
    sensor_name: str
    sensor_type: str
    is_active: bool
    last_reading_at: Optional[datetime]
    last_reading_value: Optional[float]

    class Config:
        from_attributes = True
