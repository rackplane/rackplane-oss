# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Locations API Endpoints
Datacenter, Room, Rack, and Position management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.location import Datacenter, Room, Rack, RackPosition
from app.models.user import User
from app.schemas.location import DatacenterCreate, RoomCreate, RackCreate, RackCapacityResponse, RackContentResponse, RackContentCounts
from app.services.location_service import LocationService
from app.utils.audit_helpers import audit_create, audit_update, audit_delete

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== DATACENTER ENDPOINTS =====

@router.post("/datacenters", status_code=status.HTTP_201_CREATED)
async def create_datacenter(
    datacenter: DatacenterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new datacenter"""
    service = LocationService(db)
    created_datacenter = service.create_datacenter(datacenter)
    audit_create(db, created_datacenter, current_user, request)
    return created_datacenter


@router.get("/datacenters")
async def list_datacenters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all datacenters for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Datacenter).filter(Datacenter.is_active == True)
    query = apply_tenant_filter(query, Datacenter)
    datacenters = query.all()
    return datacenters


@router.get("/datacenters/{datacenter_id}")
async def get_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get datacenter details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Datacenter).filter(Datacenter.id == datacenter_id)
    query = apply_tenant_filter(query, Datacenter)
    dc = query.first()
    if not dc:
        raise HTTPException(status_code=404, detail="Datacenter not found")
    return dc


@router.put("/datacenters/{datacenter_id}")
async def update_datacenter(
    datacenter_id: int,
    datacenter: DatacenterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a datacenter"""
    from app.core.tenant_query import apply_tenant_filter
    from app.services.audit_service import get_model_dict
    
    query = db.query(Datacenter).filter(Datacenter.id == datacenter_id)
    query = apply_tenant_filter(query, Datacenter)
    db_dc = query.first()
    if not db_dc:
        raise HTTPException(status_code=404, detail="Datacenter not found")

    # Capture old values BEFORE making changes
    old_values = get_model_dict(db_dc)

    # Update fields
    for key, value in datacenter.dict(exclude_unset=True).items():
        setattr(db_dc, key, value)

    db.commit()
    db.refresh(db_dc)
    
    # Audit log the update
    audit_update(db, db_dc, current_user, request, old_values)
    
    return db_dc


@router.delete("/datacenters/{datacenter_id}")
async def delete_datacenter(
    datacenter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a datacenter (soft delete)"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Datacenter).filter(Datacenter.id == datacenter_id)
    query = apply_tenant_filter(query, Datacenter)
    db_dc = query.first()
    if not db_dc:
        raise HTTPException(status_code=404, detail="Datacenter not found")

    # Audit log BEFORE soft-deleting
    audit_delete(db, db_dc, current_user, request)

    db_dc.is_active = False
    db.commit()
    return {"message": "Datacenter deleted successfully"}


# ===== ROOM ENDPOINTS =====

@router.post("/rooms", status_code=status.HTTP_201_CREATED)
async def create_room(
    room: RoomCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new room"""
    service = LocationService(db)
    created_room = service.create_room(room)
    audit_create(db, created_room, current_user, request)
    return created_room


@router.get("/datacenters/{datacenter_id}/rooms")
async def list_rooms(
    datacenter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List rooms in a datacenter"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Room).filter(
        Room.datacenter_id == datacenter_id,
        Room.is_active == True
    )
    query = apply_tenant_filter(query, Room)
    rooms = query.all()
    
    # Ensure proper serialization
    return list(rooms)


@router.get("/rooms")
async def list_all_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all rooms across all datacenters for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Room).filter(Room.is_active == True)
    query = apply_tenant_filter(query, Room)
    rooms = query.all()
    return rooms


@router.get("/rooms/{room_id}")
async def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get room details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Room).filter(Room.id == room_id)
    query = apply_tenant_filter(query, Room)
    room = query.first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.put("/rooms/{room_id}")
async def update_room(
    room_id: int,
    room: RoomCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a room"""
    from app.core.tenant_query import apply_tenant_filter
    from app.services.audit_service import get_model_dict
    
    query = db.query(Room).filter(Room.id == room_id)
    query = apply_tenant_filter(query, Room)
    db_room = query.first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Capture old values BEFORE making changes
    old_values = get_model_dict(db_room)

    # Update fields
    for key, value in room.dict(exclude_unset=True).items():
        setattr(db_room, key, value)

    db.commit()
    db.refresh(db_room)
    
    # Audit log the update
    audit_update(db, db_room, current_user, request, old_values)
    
    return db_room


@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a room (soft delete)"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Room).filter(Room.id == room_id)
    query = apply_tenant_filter(query, Room)
    db_room = query.first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Audit log BEFORE soft-deleting
    audit_delete(db, db_room, current_user, request)

    db_room.is_active = False
    db.commit()
    return {"message": "Room deleted successfully"}


# ===== RACK ENDPOINTS =====

@router.post("/racks", status_code=status.HTTP_201_CREATED)
async def create_rack(
    rack: RackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new rack"""
    service = LocationService(db)
    created_rack = service.create_rack(rack)
    audit_create(db, created_rack, current_user, request)
    return created_rack


@router.get("/racks")
async def list_racks(
    datacenter_id: Optional[int] = None,
    room_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all racks with optional filters for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Rack).filter(Rack.is_active == True)
    # Apply tenant filter FIRST
    query = apply_tenant_filter(query, Rack)

    if datacenter_id:
        query = query.filter(Rack.datacenter_id == datacenter_id)
    if room_id:
        query = query.filter(Rack.room_id == room_id)

    racks = query.all()
    return racks


@router.get("/racks/{rack_id}")
async def get_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get rack details"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Rack).filter(Rack.id == rack_id)
    query = apply_tenant_filter(query, Rack)
    rack = query.first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    return rack


@router.put("/racks/{rack_id}")
async def update_rack(
    rack_id: int,
    rack: RackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a rack"""
    from app.core.tenant_query import apply_tenant_filter
    from app.services.audit_service import get_model_dict
    
    query = db.query(Rack).filter(Rack.id == rack_id)
    query = apply_tenant_filter(query, Rack)
    db_rack = query.first()
    if not db_rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Capture old values BEFORE making changes
    old_values = get_model_dict(db_rack)

    # Update fields
    for key, value in rack.dict(exclude_unset=True).items():
        setattr(db_rack, key, value)

    db.commit()
    db.refresh(db_rack)
    
    # Audit log the update
    audit_update(db, db_rack, current_user, request, old_values)
    
    return db_rack


@router.delete("/racks/{rack_id}")
async def delete_rack(
    rack_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a rack (soft delete)"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Rack).filter(Rack.id == rack_id)
    query = apply_tenant_filter(query, Rack)
    db_rack = query.first()
    if not db_rack:
        raise HTTPException(status_code=404, detail="Rack not found")

    # Audit log BEFORE soft-deleting
    audit_delete(db, db_rack, current_user, request)

    db_rack.is_active = False
    db.commit()
    return {"message": "Rack deleted successfully"}


@router.get("/racks/{rack_id}/capacity", response_model=RackCapacityResponse)
async def get_rack_capacity(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get rack capacity and utilization metrics"""
    service = LocationService(db)
    return service.get_rack_capacity(rack_id)


@router.get("/racks/{rack_id}/content", response_model=RackContentResponse)
async def get_rack_content(
    rack_id: int,
    view: Optional[str] = Query(None, description="View filter: devices, storage, all"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return per content type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get rack content with vertical-aware prioritization.

    Returns rack details with devices and/or storage containers,
    prioritized based on the tenant's vertical pack.

    Args:
        rack_id: Rack ID
        view: Optional view filter (devices|storage|all)
        limit: Maximum number of items to return per content type (default 100, max 500)

    Returns:
        Rack content with vertical context and recommended view
    """
    from app.models.asset import Asset, AssetStatus
    from app.models.storage_container import StorageContainer
    from app.models.tenant import Tenant
    from app.core.tenant_query import apply_tenant_filter
    from app.core.tenant import get_current_tenant_id

    # Validate view parameter
    if view and view not in ["devices", "storage", "all"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid view parameter: {view}. Must be one of: devices, storage, all"
        )

    # Get tenant ID
    tenant_id = get_current_tenant_id()

    # Get rack with tenant filter
    rack_query = db.query(Rack).filter(
        Rack.id == rack_id,
        Rack.is_active == True
    )
    rack_query = apply_tenant_filter(rack_query, Rack)
    rack = rack_query.first()

    if not rack:
        # Log the attempt for security monitoring (rack may exist but belong to different tenant)
        logger.warning(
            f"Rack content access denied or not found: rack_id={rack_id}, "
            f"user={current_user.username}, tenant_id={tenant_id}"
        )
        raise HTTPException(status_code=404, detail="Rack not found")

    # Get tenant vertical
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    vertical_pack = tenant.vertical_pack if tenant else "datacenter"

    # Get devices (if requested)
    devices = None
    if view in [None, "devices", "all"]:
        devices_query = db.query(Asset).filter(
            Asset.rack_id == rack_id,
            Asset.status.in_([AssetStatus.DEPLOYED, AssetStatus.ACTIVE])
        )
        devices_query = apply_tenant_filter(devices_query, Asset)
        devices = devices_query.order_by(Asset.rack_position_start.desc()).limit(limit).all()

    # Get storage containers (if requested)
    storage_containers = None
    if view in [None, "storage", "all"] and rack.room_id:
        storage_query = db.query(StorageContainer).filter(
            StorageContainer.room_id == rack.room_id
        )
        storage_query = apply_tenant_filter(storage_query, StorageContainer)
        storage_containers = storage_query.limit(limit).all()

    # Calculate counts
    device_count = len(devices) if devices else 0
    storage_count = len(storage_containers) if storage_containers else 0

    total_u_used = sum(
        (d.rack_position_end - d.rack_position_start + 1)
        for d in (devices or [])
        if d.rack_position_start and d.rack_position_end
    ) if devices else 0

    # Determine recommended view based on vertical
    # Logic: Show the vertical's primary use case unless ONLY the other type has content
    # - Datacenter primary: devices (default to devices unless only storage has content)
    # - Warehouse/Healthcare primary: storage (default to storage unless only devices have content)
    if vertical_pack == "datacenter":
        # Show storage view only if: has storage AND no devices
        recommended_view = "storage" if storage_count > 0 and device_count == 0 else "devices"
    else:  # warehouse, healthcare
        # Show devices view only if: has devices AND no storage
        recommended_view = "devices" if device_count > 0 and storage_count == 0 else "storage"

    # Convert to dict to avoid serialization issues
    from app.schemas.asset import AssetResponse
    from app.schemas.storage_container import StorageContainerResponse

    rack_dict = {
        "id": rack.id,
        "name": rack.name,
        "code": rack.code,
        "height_u": rack.height_u,
        "datacenter_id": rack.datacenter_id,
        "room_id": rack.room_id,
        "row": rack.row,
        "position": rack.position,
        "power_capacity_watts": rack.power_capacity_watts
    }

    devices_dict = [AssetResponse.from_orm(d).dict() for d in devices] if devices else None
    storage_dict = [StorageContainerResponse.from_orm(s).dict() for s in storage_containers] if storage_containers else None

    return {
        "rack": rack_dict,
        "devices": devices_dict,
        "storage_containers": storage_dict,
        "vertical_pack": vertical_pack,
        "recommended_view": recommended_view,
        "counts": RackContentCounts(
            devices=device_count,
            storage=storage_count,
            total_u_used=total_u_used
        )
    }


@router.get("/racks/{rack_id}/available-positions")
async def get_available_positions(
    rack_id: int,
    u_height: int = Query(1, ge=1, le=42),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available U-positions in a rack for a device of specified height"""
    service = LocationService(db)
    return service.get_available_positions(rack_id, u_height)


@router.get("/racks/{rack_id}/visual")
async def get_rack_visual(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get visual representation of rack layout"""
    service = LocationService(db)
    return service.get_rack_visual(rack_id)


@router.post("/racks/{rack_id}/suggest-placement")
async def suggest_asset_placement(
    rack_id: int,
    u_height: int,
    power_watts: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Suggest optimal placement for new asset in rack"""
    service = LocationService(db)
    return service.suggest_placement(rack_id, u_height, power_watts)


@router.get("/capacity/optimal-rack")
async def find_optimal_rack(
    datacenter_id: int,
    u_height: int,
    power_watts: float,
    cooling_btu: Optional[float] = None,
    prioritize: str = Query("power_efficiency", regex="^(power_efficiency|space|balanced)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Find optimal rack for new asset based on capacity and efficiency"""
    service = LocationService(db)
    return service.find_optimal_rack(
        datacenter_id=datacenter_id,
        u_height=u_height,
        power_watts=power_watts,
        cooling_btu=cooling_btu,
        prioritize=prioritize
    )
