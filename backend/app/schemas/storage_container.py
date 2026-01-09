# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""Storage Container Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StorageContainerBase(BaseModel):
    name: str
    container_type: str
    datacenter_id: Optional[int] = None
    room_id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    min_stock_threshold: Optional[int] = None


class StorageContainerCreate(StorageContainerBase):
    pass


class StorageContainerUpdate(BaseModel):
    name: Optional[str] = None
    container_type: Optional[str] = None
    datacenter_id: Optional[int] = None
    room_id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    min_stock_threshold: Optional[int] = None


class StorageContainerResponse(StorageContainerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Computed fields
    item_count: Optional[int] = None
    is_low_stock: Optional[bool] = None

    class Config:
        from_attributes = True

