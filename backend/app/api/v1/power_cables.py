# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Power Cables API Endpoints
CRUD operations for power cable management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.power_cable import PowerCable, PowerConnectorType
from app.models.user import User
from app.schemas.power_cable import (
    PowerCableCreate,
    PowerCableUpdate,
    PowerCableResponse
)

router = APIRouter()


@router.get("/", response_model=List[PowerCableResponse])
async def list_power_cables(
    skip: int = 0,
    limit: int = 500,
    connector_end_a: Optional[PowerConnectorType] = None,
    connector_end_b: Optional[PowerConnectorType] = None,
    voltage: Optional[str] = None,
    storage_container_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List power cables with optional filters for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(PowerCable)
    query = apply_tenant_filter(query, PowerCable)

    if connector_end_a:
        query = query.filter(PowerCable.connector_end_a == connector_end_a)
    if connector_end_b:
        query = query.filter(PowerCable.connector_end_b == connector_end_b)
    if voltage:
        query = query.filter(PowerCable.voltage == voltage)
    if storage_container_id:
        query = query.filter(PowerCable.storage_container_id == storage_container_id)

    cables = query.offset(skip).limit(limit).all()
    return cables


@router.get("/{cable_id}", response_model=PowerCableResponse)
async def get_power_cable(
    cable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific power cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(PowerCable).filter(PowerCable.id == cable_id)
    query = apply_tenant_filter(query, PowerCable)
    cable = query.first()
    if not cable:
        raise HTTPException(status_code=404, detail="Power cable not found")
    return cable


@router.post("/", response_model=PowerCableResponse, status_code=status.HTTP_201_CREATED)
async def create_power_cable(
    cable: PowerCableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new power cable"""
    db_cable = PowerCable(**cable.model_dump())
    db.add(db_cable)
    db.commit()
    db.refresh(db_cable)
    return db_cable


@router.put("/{cable_id}", response_model=PowerCableResponse)
async def update_power_cable(
    cable_id: int,
    cable_update: PowerCableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a power cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(PowerCable).filter(PowerCable.id == cable_id)
    query = apply_tenant_filter(query, PowerCable)
    db_cable = query.first()
    if not db_cable:
        raise HTTPException(status_code=404, detail="Power cable not found")

    # Update fields
    for key, value in cable_update.model_dump(exclude_unset=True).items():
        setattr(db_cable, key, value)

    db.commit()
    db.refresh(db_cable)
    return db_cable


@router.delete("/{cable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_power_cable(
    cable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a power cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(PowerCable).filter(PowerCable.id == cable_id)
    query = apply_tenant_filter(query, PowerCable)
    cable = query.first()
    if not cable:
        raise HTTPException(status_code=404, detail="Power cable not found")

    db.delete(cable)
    db.commit()
    return None
