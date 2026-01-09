# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""NetworkPort API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.network import NetworkPort, PortType, PortStatus
from app.models.asset import Asset
from app.models.user import User
from app.schemas.network_port import (
    NetworkPortCreate,
    NetworkPortUpdate,
    NetworkPortResponse,
    NetworkPortListResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=NetworkPortResponse, status_code=status.HTTP_201_CREATED)
async def create_network_port(
    port_data: NetworkPortCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new network port"""

    # Verify asset exists and belongs to tenant
    asset_query = db.query(Asset).filter(Asset.id == port_data.asset_id)
    asset_query = apply_tenant_filter(asset_query, Asset)
    asset = asset_query.first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {port_data.asset_id} not found"
        )

    # Check for duplicate port_number on same asset
    existing = db.query(NetworkPort).filter(
        NetworkPort.asset_id == port_data.asset_id,
        NetworkPort.port_number == port_data.port_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port {port_data.port_number} already exists on asset {asset.asset_tag}"
        )

    # Create port - need to set tenant_id from current user context
    port_dict = port_data.model_dump()
    port_dict['tenant_id'] = current_user.tenant_id
    new_port = NetworkPort(**port_dict)
    db.add(new_port)
    db.commit()
    db.refresh(new_port)

    logger.info(f"Created NetworkPort {new_port.id} on asset {asset.asset_tag}")
    return new_port


@router.get("/", response_model=NetworkPortListResponse)
async def list_network_ports(
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    port_type: Optional[str] = Query(None, description="Filter by port type"),
    port_status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List network ports with filters"""

    query = db.query(NetworkPort)
    query = apply_tenant_filter(query, NetworkPort)

    if asset_id:
        query = query.filter(NetworkPort.asset_id == asset_id)
    if port_type:
        try:
            port_type_enum = PortType(port_type)
            query = query.filter(NetworkPort.port_type == port_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid port_type: {port_type}"
            )
    if port_status:
        try:
            status_enum = PortStatus(port_status)
            query = query.filter(NetworkPort.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {port_status}"
            )

    total = query.count()
    ports = query.order_by(NetworkPort.port_number).offset(skip).limit(limit).all()

    return {
        "ports": ports,
        "total": total
    }


@router.get("/{port_id}", response_model=NetworkPortResponse)
async def get_network_port(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific network port"""

    query = db.query(NetworkPort).filter(NetworkPort.id == port_id)
    query = apply_tenant_filter(query, NetworkPort)
    port = query.first()

    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {port_id} not found"
        )

    return port


@router.put("/{port_id}", response_model=NetworkPortResponse)
async def update_network_port(
    port_id: int,
    port_data: NetworkPortUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a network port"""

    query = db.query(NetworkPort).filter(NetworkPort.id == port_id)
    query = apply_tenant_filter(query, NetworkPort)
    port = query.first()

    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {port_id} not found"
        )

    # Update fields
    update_data = port_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(port, field, value)

    db.commit()
    db.refresh(port)

    logger.info(f"Updated NetworkPort {port_id}")
    return port


@router.delete("/{port_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_network_port(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a network port"""

    query = db.query(NetworkPort).filter(NetworkPort.id == port_id)
    query = apply_tenant_filter(query, NetworkPort)
    port = query.first()

    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {port_id} not found"
        )

    # Check if port is used in any connections (Phase 2: check port_id)
    from app.models.connections import Connection
    conn_check = db.query(Connection).filter(
        Connection.port_id == port.id
    ).first()

    if conn_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete port that has active connections"
        )

    db.delete(port)
    db.commit()

    logger.info(f"Deleted NetworkPort {port_id}")
    return None


@router.post("/{port_id}/install-transceiver", response_model=dict)
async def install_transceiver(
    port_id: int,
    transceiver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Install an optical transceiver into a port.
    
    This marks the transceiver as deployed and links it to the port.
    """
    
    # Get port
    query = db.query(NetworkPort).filter(NetworkPort.id == port_id)
    query = apply_tenant_filter(query, NetworkPort)
    port = query.first()
    
    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {port_id} not found"
        )
    
    # Check if port already has a transceiver
    if port.installed_transceiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port already has a transceiver installed. Uninstall first."
        )
    
    # Get transceiver asset
    trans_query = db.query(Asset).filter(Asset.id == transceiver_id)
    trans_query = apply_tenant_filter(trans_query, Asset)
    transceiver = trans_query.first()
    
    if not transceiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transceiver asset {transceiver_id} not found"
        )
    
    if transceiver.asset_type not in ('optical_transceiver', 'copper_transceiver'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {transceiver.asset_tag} is not a transceiver (type: {transceiver.asset_type})"
        )
    
    # Install transceiver
    port.installed_transceiver_id = transceiver_id
    transceiver.status = "deployed"
    
    db.commit()
    
    logger.info(f"Installed transceiver {transceiver.asset_tag} into port {port_id}")
    
    return {
        "message": f"Transceiver {transceiver.asset_tag} installed into port {port.port_number}",
        "port_id": port_id,
        "transceiver_id": transceiver_id
    }


@router.delete("/{port_id}/uninstall-transceiver", response_model=dict)
async def uninstall_transceiver(
    port_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Uninstall a transceiver from a port.
    
    Returns the transceiver to in_storage status.
    """
    
    # Get port
    query = db.query(NetworkPort).filter(NetworkPort.id == port_id)
    query = apply_tenant_filter(query, NetworkPort)
    port = query.first()
    
    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {port_id} not found"
        )
    
    if not port.installed_transceiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port does not have a transceiver installed"
        )
    
    # Get transceiver to update status
    transceiver = db.query(Asset).filter(Asset.id == port.installed_transceiver_id).first()
    transceiver_tag = transceiver.asset_tag if transceiver else "unknown"
    
    if transceiver:
        transceiver.status = "in_storage"
    
    # Remove from port
    port.installed_transceiver_id = None
    
    db.commit()
    
    logger.info(f"Uninstalled transceiver {transceiver_tag} from port {port_id}")
    
    return {
        "message": f"Transceiver uninstalled from port {port.port_number}",
        "port_id": port_id
    }
