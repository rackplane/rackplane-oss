# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Global Search API Endpoints
Provides unified search across assets, locations, cables, and other entities
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.user import User
from app.models.asset import Asset
from app.models.location import Datacenter, Room, Rack
from app.models.network_cable import NetworkCable
from app.models.power_cable import PowerCable
from app.models.asset_type import AssetTypeModel
from app.models.storage_container import StorageContainer

router = APIRouter()


@router.get("/", summary="Global search across all entities")
async def global_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results per category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Perform a global search across all asset types, locations, cables, and other entities.
    
    Searches in:
    - Assets (asset_tag, serial_number, manufacturer, model, hostname)
    - Datacenters (name, code)
    - Rooms (name, code)
    - Racks (name, code)
    - Network cables (asset_tag, serial_number)
    - Power cables (asset_tag, serial_number)
    - Asset types (name, display_name)
    
    Returns results grouped by entity type.
    """
    search_term = f"%{q}%"
    results = {
        "query": q,
        "assets": [],
        "datacenters": [],
        "rooms": [],
        "racks": [],
        "storage_containers": [],
        "network_cables": [],
        "power_cables": [],
        "asset_types": [],
        "total_results": 0
    }
    
    # Search Assets
    asset_query = db.query(Asset).filter(
        or_(
            Asset.asset_tag.ilike(search_term),
            Asset.serial_number.ilike(search_term),
            Asset.manufacturer.ilike(search_term),
            Asset.model.ilike(search_term),
            Asset.hostname.ilike(search_term),
            Asset.description.ilike(search_term)
        )
    )
    asset_query = apply_tenant_filter(asset_query, Asset)
    assets = asset_query.limit(limit).all()
    
    for asset in assets:
        results["assets"].append({
            "id": asset.id,
            "asset_tag": asset.asset_tag,
            "serial_number": asset.serial_number,
            "asset_type": asset.asset_type,
            "manufacturer": asset.manufacturer,
            "model": asset.model,
            "status": asset.status.value if hasattr(asset.status, 'value') else str(asset.status),
            "entity_type": "asset"
        })
    
    # Search Datacenters
    datacenter_query = db.query(Datacenter).filter(
        or_(
            Datacenter.name.ilike(search_term),
            Datacenter.code.ilike(search_term),
            Datacenter.address.ilike(search_term)
        )
    )
    datacenter_query = apply_tenant_filter(datacenter_query, Datacenter)
    datacenters = datacenter_query.limit(limit).all()
    
    for dc in datacenters:
        results["datacenters"].append({
            "id": dc.id,
            "name": dc.name,
            "code": dc.code,
            "address": dc.address,
            "entity_type": "datacenter"
        })
    
    # Search Rooms
    room_query = db.query(Room).filter(
        or_(
            Room.name.ilike(search_term),
            Room.code.ilike(search_term)
        )
    )
    room_query = apply_tenant_filter(room_query, Room)
    rooms = room_query.limit(limit).all()
    
    for room in rooms:
        results["rooms"].append({
            "id": room.id,
            "name": room.name,
            "code": room.code,
            "datacenter_id": room.datacenter_id,
            "entity_type": "room"
        })
    
    # Search Racks
    rack_query = db.query(Rack).filter(
        or_(
            Rack.name.ilike(search_term),
            Rack.code.ilike(search_term)
        )
    )
    rack_query = apply_tenant_filter(rack_query, Rack)
    racks = rack_query.limit(limit).all()
    
    for rack in racks:
        results["racks"].append({
            "id": rack.id,
            "name": rack.name,
            "code": rack.code,
            "datacenter_id": rack.datacenter_id,
            "room_id": rack.room_id,
            "entity_type": "rack"
        })
    
    # Search Storage Containers (including location and rack info)
    storage_container_query = db.query(StorageContainer).filter(
        or_(
            StorageContainer.name.ilike(search_term),
            StorageContainer.location.ilike(search_term),
            StorageContainer.description.ilike(search_term),
            StorageContainer.barcode.ilike(search_term)
        )
    )
    storage_container_query = apply_tenant_filter(storage_container_query, StorageContainer)
    storage_containers = storage_container_query.limit(limit).all()
    
    # Also search by rack name/code through relationships
    # Find racks matching the search term (already queried above)
    matching_rack_ids = [r.id for r in racks]
    if matching_rack_ids:
        # Find rooms that contain these racks
        room_ids_query = db.query(Room.id).join(Rack, Room.id == Rack.room_id).filter(Rack.id.in_(matching_rack_ids))
        room_ids_query = apply_tenant_filter(room_ids_query, Room)
        room_ids = [r[0] for r in room_ids_query.all()]
        
        if room_ids:
            # Find storage containers in these rooms
            additional_containers_query = db.query(StorageContainer).filter(
                StorageContainer.room_id.in_(room_ids)
            )
            additional_containers_query = apply_tenant_filter(additional_containers_query, StorageContainer)
            additional_containers = additional_containers_query.all()
            
            # Add containers that aren't already in results
            existing_ids = {sc.id for sc in storage_containers}
            for sc in additional_containers:
                if sc.id not in existing_ids:
                    storage_containers.append(sc)
    
    for container in storage_containers:
        # Get rack info if container is in a room with racks
        rack_info = None
        if container.room_id:
            rack = db.query(Rack).filter(Rack.room_id == container.room_id).first()
            if rack:
                rack_info = {"id": rack.id, "name": rack.name, "code": rack.code}
        
        results["storage_containers"].append({
            "id": container.id,
            "name": container.name,
            "container_type": container.container_type,
            "location": container.location,
            "description": container.description,
            "datacenter_id": container.datacenter_id,
            "room_id": container.room_id,
            "rack": rack_info,
            "entity_type": "storage_container"
        })
    
    # Search Network Cables
    network_cable_query = db.query(NetworkCable).filter(
        or_(
            NetworkCable.name.ilike(search_term),
            NetworkCable.serial_number.ilike(search_term),
            NetworkCable.manufacturer.ilike(search_term),
            NetworkCable.model.ilike(search_term)
        )
    )
    network_cable_query = apply_tenant_filter(network_cable_query, NetworkCable)
    network_cables = network_cable_query.limit(limit).all()
    
    for cable in network_cables:
        results["network_cables"].append({
            "id": cable.id,
            "name": cable.name,
            "serial_number": cable.serial_number,
            "cable_type": cable.cable_type.value if hasattr(cable.cable_type, 'value') else str(cable.cable_type),
            "speed": cable.speed,
            "entity_type": "network_cable"
        })
    
    # Search Power Cables
    power_cable_query = db.query(PowerCable).filter(
        or_(
            PowerCable.name.ilike(search_term),
            PowerCable.manufacturer.ilike(search_term),
            PowerCable.model.ilike(search_term),
            PowerCable.voltage.ilike(search_term)
        )
    )
    power_cable_query = apply_tenant_filter(power_cable_query, PowerCable)
    power_cables = power_cable_query.limit(limit).all()
    
    for cable in power_cables:
        results["power_cables"].append({
            "id": cable.id,
            "name": cable.name,
            "voltage": cable.voltage,
            "connector_end_a": cable.connector_end_a.value if hasattr(cable.connector_end_a, 'value') else str(cable.connector_end_a),
            "connector_end_b": cable.connector_end_b.value if hasattr(cable.connector_end_b, 'value') else str(cable.connector_end_b),
            "entity_type": "power_cable"
        })
    
    # Search Asset Types
    asset_type_query = db.query(AssetTypeModel).filter(
        or_(
            AssetTypeModel.name.ilike(search_term),
            AssetTypeModel.display_name.ilike(search_term),
            AssetTypeModel.description.ilike(search_term)
        )
    )
    asset_type_query = apply_tenant_filter(asset_type_query, AssetTypeModel)
    asset_types = asset_type_query.limit(limit).all()
    
    for at in asset_types:
        results["asset_types"].append({
            "id": at.id,
            "name": at.name,
            "display_name": at.display_name,
            "description": at.description,
            "entity_type": "asset_type"
        })
    
    # Calculate total results
    results["total_results"] = (
        len(results["assets"]) +
        len(results["datacenters"]) +
        len(results["rooms"]) +
        len(results["racks"]) +
        len(results["storage_containers"]) +
        len(results["network_cables"]) +
        len(results["power_cables"]) +
        len(results["asset_types"])
    )
    
    return results

