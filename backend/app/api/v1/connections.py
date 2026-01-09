# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Connection API Endpoints
Double-ended cable connection management - Phase 2: Port-based connections
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.connections import Connection, ConnectionEnd
from app.models.network import NetworkPort, PortType, PortStatus
from app.models.asset import Asset, AssetStatus
from app.models.user import User
from app.schemas.connections import ConnectRequest, ConnectResponse, ConnectionResponse, Circuit, CircuitEndpoint
from app.services.stock_service import deploy_asset
from app.services.cable_validation_service import CableValidationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/connect", response_model=ConnectResponse, status_code=status.HTTP_201_CREATED)
async def connect_cable(
    request: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Smart cable connection endpoint.
    
    Phase 2: Now supports port_id for true port-to-port connections.
    Also supports deprecated device_id + port_label for backward compatibility.
    
    Automatically assigns End 'A' or 'B' based on existing connections:
    - 0 connections -> Assign End 'A'
    - 1 connection (End 'A' used) -> Assign End 'B'
    - 2 connections -> Return 400 Error (cable fully connected)
    """
    from app.core.tenant import get_current_tenant_id
    
    # Verify cable asset exists
    cable_query = db.query(Asset).filter(Asset.id == request.cable_id)
    cable_query = apply_tenant_filter(cable_query, Asset)
    cable = cable_query.first()
    
    if not cable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable asset with ID {request.cable_id} not found"
        )
    
    # Phase 2: Resolve port_id
    port_id = None
    device_id = None
    
    if request.port_id:
        # New Phase 2 flow: Use port_id directly
        port_query = db.query(NetworkPort).filter(NetworkPort.id == request.port_id)
        port_query = apply_tenant_filter(port_query, NetworkPort)
        port = port_query.first()
        
        if not port:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Port with ID {request.port_id} not found"
            )
        
        port_id = port.id
        device_id = port.asset_id
        
        # Check if cable is already connected to this exact port
        existing_on_port = db.query(Connection).filter(
            Connection.cable_asset_id == request.cable_id,
            Connection.port_id == port_id
        ).first()
        
        if existing_on_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cable is already connected to port {port.port_label or port.port_number}"
            )
    
    elif request.device_id:
        # Deprecated flow: Use device_id + port_label
        device_query = db.query(Asset).filter(Asset.id == request.device_id)
        device_query = apply_tenant_filter(device_query, Asset)
        device = device_query.first()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device asset with ID {request.device_id} not found"
            )
        
        device_id = device.id
        
        # Try to find or create a matching port
        if request.port_label:
            port = db.query(NetworkPort).filter(
                NetworkPort.asset_id == device_id,
                (NetworkPort.port_label == request.port_label) |
                (NetworkPort.port_name == request.port_label) |
                (NetworkPort.port_number == request.port_label)
            ).first()
            
            if port:
                port_id = port.id
            else:
                # Create a new port for this connection (migration helper)
                from app.core.tenant import get_current_tenant_id
                new_port = NetworkPort(
                    asset_id=device_id,
                    tenant_id=get_current_tenant_id(),
                    port_number=request.port_label,
                    port_name=f"{device.asset_tag}:{request.port_label}",
                    port_label=request.port_label,
                    port_type=PortType.OTHER,
                    status=PortStatus.ACTIVE,
                    enabled=True
                )
                db.add(new_port)
                db.flush()
                port_id = new_port.id
                logger.info(f"Created port {port_id} for device {device_id} with label {request.port_label}")
        
        # Prevent connecting cable to itself
        if request.cable_id == request.device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot connect a cable to itself"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either port_id or device_id must be provided"
        )
    
    # LIFECYCLE EVENT: Deploy cable from storage
    try:
        deployed_cable = deploy_asset(db, request.cable_id)
        if deployed_cable:
            logger.info(f"Cable {cable.asset_tag} deployed from storage")
            db.refresh(cable)
    except Exception as e:
        logger.warning(f"Failed to deploy cable {cable.asset_tag} from storage: {str(e)}")
    
    # Query existing connections for this cable
    connections_query = db.query(Connection).filter(Connection.cable_asset_id == request.cable_id)
    connections_query = apply_tenant_filter(connections_query, Connection)
    existing_connections = connections_query.all()
    
    # Determine which end to assign
    if len(existing_connections) == 0:
        end_label = ConnectionEnd.A
        message = "End A connected. Now walk to the other end and scan the destination device."
    elif len(existing_connections) == 1:
        existing_end = existing_connections[0].end_label
        end_label = ConnectionEnd.B if existing_end == ConnectionEnd.A else ConnectionEnd.A
        
        # Check for loopback (same device)
        if existing_connections[0].port_id:
            existing_port = db.query(NetworkPort).filter(NetworkPort.id == existing_connections[0].port_id).first()
            if existing_port and existing_port.asset_id == device_id:
                message = f"End B connected. Loopback circuit complete!"
            else:
                message = "End B connected. Circuit complete!"
        else:
            message = "End B connected. Circuit complete!"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cable is fully connected. Both ends (A and B) are already in use."
        )
    
    # Create the connection
    try:
        new_connection = Connection(
            cable_asset_id=request.cable_id,
            port_id=port_id,
            device_asset_id=device_id,  # Keep for backward compat
            end_label=end_label
        )
        db.add(new_connection)
        db.commit()
        db.refresh(new_connection)
        
        # Phase 3: Validate cable/port compatibility
        compatibility_result = None
        if port_id:
            port = db.query(NetworkPort).filter(NetworkPort.id == port_id).first()
            if port and port.port_type:
                # Get cable connector type from formal columns or custom_fields
                cable_connector_type = None
                if end_label == ConnectionEnd.A:
                    cable_connector_type = getattr(cable, 'connector_type_end_a', None)
                else:
                    cable_connector_type = getattr(cable, 'connector_type_end_b', None)
                
                # Fallback to general connector_type or custom_fields
                if not cable_connector_type:
                    cable_connector_type = getattr(cable, 'connector_type', None)
                
                if not cable_connector_type and cable.custom_fields and isinstance(cable.custom_fields, dict):
                    cable_connector_type = cable.custom_fields.get('connector_type') or cable.custom_fields.get('dac_connector_a') or cable.custom_fields.get('fiber_connector_a')
                
                if cable_connector_type:
                    compatibility_result = CableValidationService.validate_compatibility(
                        cable_connector_type=cable_connector_type,
                        port_type=port.port_type.value if hasattr(port.port_type, 'value') else str(port.port_type)
                    )
                    logger.info(
                        f"Compatibility check: {cable.asset_tag} ({cable_connector_type}) -> "
                        f"{port.port_label or port.port_number} ({port.port_type}): {compatibility_result['level']}"
                    )
        
        return ConnectResponse(
            connection=ConnectionResponse(
                id=new_connection.id,
                cable_asset_id=new_connection.cable_asset_id,
                port_id=new_connection.port_id,
                device_asset_id=new_connection.device_asset_id,
                port_label=None,  # Deprecated
                end_label=new_connection.end_label.value,
                created_at=None
            ),
            end_label=end_label.value,
            message=message,
            compatibility=compatibility_result
        )
    except IntegrityError as e:
        db.rollback()
        if "uq_cable_end" in str(e.orig) if hasattr(e, 'orig') else "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cable end {end_label.value} is already connected for this cable"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create connection: {str(e)}"
        )


@router.get("/cable/{cable_id}", response_model=list[ConnectionResponse])
async def get_cable_connections(
    cable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all connections for a specific cable"""
    connections_query = db.query(Connection).filter(Connection.cable_asset_id == cable_id)
    connections_query = apply_tenant_filter(connections_query, Connection)
    connections = connections_query.all()
    
    return [
        ConnectionResponse(
            id=conn.id,
            cable_asset_id=conn.cable_asset_id,
            port_id=conn.port_id,
            device_asset_id=conn.device_asset_id,
            port_label=None,
            end_label=conn.end_label.value,
            created_at=None
        )
        for conn in connections
    ]


@router.get("/circuits", response_model=List[Circuit])
async def get_all_circuits(
    rack_id: Optional[int] = Query(None, description="Filter by rack ID"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns a 'Circuit' view: Grouping connections by Cable ID.
    Shows both ends of each cable connection in a readable format.
    
    Phase 2: Now includes full port information.
    """
    from app.models.location import Rack
    
    # Get all connections with eager loading
    query = db.query(Connection).options(
        joinedload(Connection.cable_asset),
        joinedload(Connection.port).joinedload(NetworkPort.asset),
        joinedload(Connection.device_asset)  # For backward compat
    )
    query = apply_tenant_filter(query, Connection)
    
    # Apply filters
    if rack_id or device_id:
        if device_id:
            # Filter by device - check both port.asset_id and device_asset_id
            query = query.outerjoin(NetworkPort, Connection.port_id == NetworkPort.id)
            query = query.filter(
                (NetworkPort.asset_id == device_id) | (Connection.device_asset_id == device_id)
            )
        elif rack_id:
            # Filter by rack - need to join through port or device_asset
            query = query.outerjoin(NetworkPort, Connection.port_id == NetworkPort.id)
            query = query.outerjoin(Asset, 
                (NetworkPort.asset_id == Asset.id) | (Connection.device_asset_id == Asset.id)
            )
            query = query.filter(Asset.rack_id == rack_id)
    
    raw_connections = query.all()
    
    # Group connections by cable ID
    circuits = {}
    
    for conn in raw_connections:
        c_id = conn.cable_asset_id
        if c_id not in circuits:
            cable = conn.cable_asset
            circuits[c_id] = {
                "cable": {
                    "id": c_id,
                    "name": cable.model or cable.asset_tag,
                    "tag": cable.asset_tag,
                    "manufacturer": cable.manufacturer,
                    "connector_type": (
                        getattr(cable, 'connector_type', None) or 
                        (cable.custom_fields.get("connector_type") if cable.custom_fields else None)
                    ),
                    "connector_type_end_a": getattr(cable, "connector_type_end_a", None),
                    "connector_type_end_b": getattr(cable, "connector_type_end_b", None)
                },
                "end_a": None,
                "end_b": None
            }
        
        # Get device and port info
        if conn.port_id and conn.port:
            port = conn.port
            device = port.asset
            port_info = {
                "port_id": port.id,
                "port_number": port.port_number,
                "port_name": port.port_name or port.port_label,
                "port_type": port.port_type.value if port.port_type else "unknown",
                "port": port.port_label or port.port_number  # Backward compat
            }
        else:
            # Fallback to device_asset for old connections
            device = conn.device_asset
            port_info = {
                "port_id": None,
                "port_number": None,
                "port_name": None,
                "port_type": None,
                "port": "N/A"
            }
        
        if not device:
            continue
        
        # Get rack info
        rack_name = "Unracked"
        rack_code = None
        if device.rack_id:
            rack = db.query(Rack).filter(Rack.id == device.rack_id).first()
            if rack:
                rack_name = rack.name
                rack_code = rack.code
        
        endpoint_data = CircuitEndpoint(
            device_id=device.id,
            device_name=device.asset_tag,
            device_type=device.asset_type,
            device_model=device.model or "",
            rack_name=rack_name,
            rack_code=rack_code,
            **port_info
        )
        
        if conn.end_label == ConnectionEnd.A:
            circuits[c_id]["end_a"] = endpoint_data
        elif conn.end_label == ConnectionEnd.B:
            circuits[c_id]["end_b"] = endpoint_data
    
    return [Circuit(**c) for c in circuits.values()]


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a connection"""
    connection_query = db.query(Connection).filter(Connection.id == connection_id)
    connection_query = apply_tenant_filter(connection_query, Connection)
    connection = connection_query.first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with ID {connection_id} not found"
        )
    
    db.delete(connection)
    db.commit()
    
    return None

