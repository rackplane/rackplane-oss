# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Network Cables API Endpoints
CRUD operations for network cable and module management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.network_cable import NetworkCable, CableType, ConnectorType
from app.models.user import User
from app.schemas.network_cable import (
    NetworkCableCreate,
    NetworkCableUpdate,
    NetworkCableResponse
)

router = APIRouter()


@router.get("/", response_model=List[NetworkCableResponse])
async def list_network_cables(
    skip: int = 0,
    limit: int = 500,
    cable_type: Optional[CableType] = None,
    connector_type: Optional[ConnectorType] = None,
    search: Optional[str] = None,
    speed: Optional[str] = None,
    storage_container_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List network cables with optional filters for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    from sqlalchemy import or_
    
    query = db.query(NetworkCable)
    query = apply_tenant_filter(query, NetworkCable)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                NetworkCable.name.ilike(search_term),
                NetworkCable.serial_number.ilike(search_term),
                NetworkCable.model.ilike(search_term)
            )
        )

    if cable_type:
        query = query.filter(NetworkCable.cable_type == cable_type)
    if connector_type:
        query = query.filter(NetworkCable.connector_type == connector_type)
    if speed:
        query = query.filter(NetworkCable.speed == speed)
    if storage_container_id:
        query = query.filter(NetworkCable.storage_container_id == storage_container_id)

    cables = query.offset(skip).limit(limit).all()
    return cables


@router.get("/{cable_id}", response_model=NetworkCableResponse)
async def get_network_cable(
    cable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific network cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(NetworkCable).filter(NetworkCable.id == cable_id)
    query = apply_tenant_filter(query, NetworkCable)
    cable = query.first()
    if not cable:
        raise HTTPException(status_code=404, detail="Network cable not found")
    return cable


@router.post("/", response_model=NetworkCableResponse, status_code=status.HTTP_201_CREATED)
async def create_network_cable(
    cable: NetworkCableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new network cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Check if serial number already exists within tenant scope (if provided)
    if cable.serial_number:
        query = db.query(NetworkCable).filter(NetworkCable.serial_number == cable.serial_number)
        query = apply_tenant_filter(query, NetworkCable)
        existing = query.first()
        if existing:
            raise HTTPException(status_code=400, detail="Network cable with this serial number already exists")

    db_cable = NetworkCable(**cable.model_dump())
    db.add(db_cable)
    db.commit()
    db.refresh(db_cable)
    return db_cable


@router.put("/{cable_id}", response_model=NetworkCableResponse)
async def update_network_cable(
    cable_id: int,
    cable_update: NetworkCableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a network cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(NetworkCable).filter(NetworkCable.id == cable_id)
    query = apply_tenant_filter(query, NetworkCable)
    db_cable = query.first()
    if not db_cable:
        raise HTTPException(status_code=404, detail="Network cable not found")

    # Update fields
    for key, value in cable_update.model_dump(exclude_unset=True).items():
        setattr(db_cable, key, value)

    db.commit()
    db.refresh(db_cable)
    return db_cable


@router.delete("/{cable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_network_cable(
    cable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a network cable"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(NetworkCable).filter(NetworkCable.id == cable_id)
    query = apply_tenant_filter(query, NetworkCable)
    cable = query.first()
    if not cable:
        raise HTTPException(status_code=404, detail="Network cable not found")

    db.delete(cable)
    db.commit()
    return None
