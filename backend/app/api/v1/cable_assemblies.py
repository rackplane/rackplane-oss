# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
CableAssembly API Endpoints

Pre-configured fiber cable assemblies (2 transceivers + 1 fiber cable).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.cable_assembly import CableAssembly, AssemblyStatus
from app.models.asset import Asset
from app.models.network import NetworkPort
from app.models.user import User
from app.schemas.cable_assembly import (
    CableAssemblyCreate,
    CableAssemblyUpdate,
    CableAssemblyResponse,
    DeployAssemblyRequest
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CableAssemblyResponse, status_code=status.HTTP_201_CREATED)
async def create_cable_assembly(
    assembly_data: CableAssemblyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new cable assembly from existing assets"""
    
    # Verify fiber cable exists and is correct type
    fiber_query = db.query(Asset).filter(Asset.id == assembly_data.fiber_cable_id)
    fiber_query = apply_tenant_filter(fiber_query, Asset)
    fiber = fiber_query.first()
    
    if not fiber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fiber cable asset {assembly_data.fiber_cable_id} not found"
        )
    
    if fiber.asset_type not in ('fiber_cable', 'network_cable'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {fiber.asset_tag} is not a fiber cable (type: {fiber.asset_type})"
        )
    
    # Verify transceiver A exists and is correct type
    trans_a_query = db.query(Asset).filter(Asset.id == assembly_data.transceiver_a_id)
    trans_a_query = apply_tenant_filter(trans_a_query, Asset)
    trans_a = trans_a_query.first()
    
    if not trans_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transceiver A asset {assembly_data.transceiver_a_id} not found"
        )
    
    if trans_a.asset_type not in ('optical_transceiver', 'copper_transceiver'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {trans_a.asset_tag} is not a transceiver (type: {trans_a.asset_type})"
        )
    
    # Verify transceiver B exists and is correct type
    trans_b_query = db.query(Asset).filter(Asset.id == assembly_data.transceiver_b_id)
    trans_b_query = apply_tenant_filter(trans_b_query, Asset)
    trans_b = trans_b_query.first()
    
    if not trans_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transceiver B asset {assembly_data.transceiver_b_id} not found"
        )
    
    if trans_b.asset_type not in ('optical_transceiver', 'copper_transceiver'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {trans_b.asset_tag} is not a transceiver (type: {trans_b.asset_type})"
        )
    
    # Check if transceivers are already in use in another assembly
    existing_with_trans_a = db.query(CableAssembly).filter(
        (CableAssembly.transceiver_a_id == assembly_data.transceiver_a_id) |
        (CableAssembly.transceiver_b_id == assembly_data.transceiver_a_id)
    ).first()
    
    if existing_with_trans_a:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transceiver A ({trans_a.asset_tag}) is already used in assembly '{existing_with_trans_a.name}'"
        )
    
    existing_with_trans_b = db.query(CableAssembly).filter(
        (CableAssembly.transceiver_a_id == assembly_data.transceiver_b_id) |
        (CableAssembly.transceiver_b_id == assembly_data.transceiver_b_id)
    ).first()
    
    if existing_with_trans_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transceiver B ({trans_b.asset_tag}) is already used in assembly '{existing_with_trans_b.name}'"
        )
    
    # Check if fiber cable is already in use in another assembly
    existing_with_fiber = db.query(CableAssembly).filter(
        CableAssembly.fiber_cable_id == assembly_data.fiber_cable_id
    ).first()
    
    if existing_with_fiber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fiber cable ({fiber.asset_tag}) is already used in assembly '{existing_with_fiber.name}'"
        )
    
    # Create assembly
    new_assembly = CableAssembly(
        tenant_id=current_user.tenant_id,
        name=assembly_data.name,
        description=assembly_data.description,
        fiber_cable_id=assembly_data.fiber_cable_id,
        transceiver_a_id=assembly_data.transceiver_a_id,
        transceiver_b_id=assembly_data.transceiver_b_id,
        status=AssemblyStatus.AVAILABLE
    )
    
    db.add(new_assembly)
    db.commit()
    db.refresh(new_assembly)
    
    logger.info(f"Created CableAssembly {new_assembly.id}: {new_assembly.name}")
    return new_assembly


@router.get("/", response_model=List[CableAssemblyResponse])
async def list_cable_assemblies(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all cable assemblies"""
    
    query = db.query(CableAssembly)
    query = apply_tenant_filter(query, CableAssembly)
    
    if status:
        query = query.filter(CableAssembly.status == status)
    
    assemblies = query.order_by(CableAssembly.name).all()
    return assemblies


@router.get("/{assembly_id}", response_model=CableAssemblyResponse)
async def get_cable_assembly(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific cable assembly"""
    
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    assembly = query.first()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    return assembly


@router.put("/{assembly_id}", response_model=CableAssemblyResponse)
async def update_cable_assembly(
    assembly_id: int,
    assembly_data: CableAssemblyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a cable assembly"""
    
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    assembly = query.first()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    update_data = assembly_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assembly, field, value)
    
    db.commit()
    db.refresh(assembly)
    
    logger.info(f"Updated CableAssembly {assembly_id}")
    return assembly


@router.delete("/{assembly_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cable_assembly(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete (disassemble) a cable assembly"""
    
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    assembly = query.first()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    if assembly.status == AssemblyStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete deployed assembly. Undeploy first."
        )
    
    db.delete(assembly)
    db.commit()
    
    logger.info(f"Deleted CableAssembly {assembly_id}")
    return None


@router.post("/{assembly_id}/clone", response_model=CableAssemblyResponse, status_code=status.HTTP_201_CREATED)
async def clone_cable_assembly(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Clone a cable assembly with next available matching components.
    
    Finds:
    - Next available fiber cable with same manufacturer/model
    - Next available transceiver A with same manufacturer/model
    - Next available transceiver B with same manufacturer/model
    
    Creates a new assembly with incrementing name (e.g., "Cable-1" -> "Cable-2")
    """
    from sqlalchemy import func
    
    # Get original assembly
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    original = query.first()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    # Get original components to match
    orig_fiber = original.fiber_cable
    orig_trans_a = original.transceiver_a
    orig_trans_b = original.transceiver_b
    
    # Get all transceivers already used in assemblies
    used_trans_ids = set()
    used_fiber_ids = set()
    
    all_assemblies = db.query(CableAssembly).all()
    for asm in all_assemblies:
        used_trans_ids.add(asm.transceiver_a_id)
        used_trans_ids.add(asm.transceiver_b_id)
        used_fiber_ids.add(asm.fiber_cable_id)
    
    # Find next available fiber cable with same mfr/model
    fiber_query = db.query(Asset).filter(
        Asset.manufacturer == orig_fiber.manufacturer,
        Asset.model == orig_fiber.model,
        Asset.asset_type.in_(['fiber_cable', 'network_cable']),
        ~Asset.id.in_(used_fiber_ids)
    )
    fiber_query = apply_tenant_filter(fiber_query, Asset)
    new_fiber = fiber_query.first()
    
    if not new_fiber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available fiber cable matching {orig_fiber.manufacturer} {orig_fiber.model}"
        )
    
    # Find next available transceiver A with same mfr/model
    trans_a_query = db.query(Asset).filter(
        Asset.manufacturer == orig_trans_a.manufacturer,
        Asset.model == orig_trans_a.model,
        Asset.asset_type.in_(['optical_transceiver', 'copper_transceiver']),
        ~Asset.id.in_(used_trans_ids)
    )
    trans_a_query = apply_tenant_filter(trans_a_query, Asset)
    new_trans_a = trans_a_query.first()
    
    if not new_trans_a:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available transceiver matching {orig_trans_a.manufacturer} {orig_trans_a.model}"
        )
    
    # Add trans A to used list so we don't pick same for trans B
    used_trans_ids.add(new_trans_a.id)
    
    # Find next available transceiver B with same mfr/model  
    trans_b_query = db.query(Asset).filter(
        Asset.manufacturer == orig_trans_b.manufacturer,
        Asset.model == orig_trans_b.model,
        Asset.asset_type.in_(['optical_transceiver', 'copper_transceiver']),
        ~Asset.id.in_(used_trans_ids)
    )
    trans_b_query = apply_tenant_filter(trans_b_query, Asset)
    new_trans_b = trans_b_query.first()
    
    if not new_trans_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available transceiver matching {orig_trans_b.manufacturer} {orig_trans_b.model}"
        )
    
    # Generate new name - increment number if exists, else add -2
    base_name = original.name
    # Remove trailing number pattern like " (Copy)" or "-2"
    import re
    match = re.match(r'^(.+?)(?:\s*\(Copy\)|\s*-\s*(\d+))?\s*$', base_name)
    if match:
        base_name = match.group(1).strip()
    
    # Find the next available number
    existing_names = db.query(CableAssembly.name).filter(
        CableAssembly.name.like(f"{base_name}%")
    ).all()
    existing_names = [n[0] for n in existing_names]
    
    # Find highest number
    max_num = 1
    for name in existing_names:
        num_match = re.search(r'-\s*(\d+)\s*$', name)
        if num_match:
            max_num = max(max_num, int(num_match.group(1)))
    
    new_name = f"{base_name}-{max_num + 1}"
    
    # Create the cloned assembly
    cloned = CableAssembly(
        tenant_id=current_user.tenant_id,
        name=new_name,
        description=original.description,
        fiber_cable_id=new_fiber.id,
        transceiver_a_id=new_trans_a.id,
        transceiver_b_id=new_trans_b.id,
        status=AssemblyStatus.AVAILABLE
    )
    
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    
    logger.info(f"Cloned CableAssembly {assembly_id} -> {cloned.id}: {cloned.name}")
    return cloned


@router.post("/{assembly_id}/deploy", response_model=dict)
async def deploy_cable_assembly(
    assembly_id: int,
    request: DeployAssemblyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deploy a cable assembly to two ports.
    
    This:
    1. Installs transceiver A into port A
    2. Installs transceiver B into port B
    3. Creates cable connection between ports
    4. Updates assembly status to 'deployed'
    """
    
    # Get assembly
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    assembly = query.first()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    if assembly.status == AssemblyStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assembly is already deployed"
        )
    
    # Get ports
    port_a_query = db.query(NetworkPort).filter(NetworkPort.id == request.port_a_id)
    port_a_query = apply_tenant_filter(port_a_query, NetworkPort)
    port_a = port_a_query.first()
    
    if not port_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port A ({request.port_a_id}) not found"
        )
    
    port_b_query = db.query(NetworkPort).filter(NetworkPort.id == request.port_b_id)
    port_b_query = apply_tenant_filter(port_b_query, NetworkPort)
    port_b = port_b_query.first()
    
    if not port_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port B ({request.port_b_id}) not found"
        )
    
    # Check ports don't already have transceivers
    if port_a.installed_transceiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port A already has a transceiver installed"
        )
    
    if port_b.installed_transceiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port B already has a transceiver installed"
        )
    
    # Install transceivers
    port_a.installed_transceiver_id = assembly.transceiver_a_id
    port_b.installed_transceiver_id = assembly.transceiver_b_id
    
    # Update transceiver assets to deployed status
    assembly.transceiver_a.status = "deployed"
    assembly.transceiver_b.status = "deployed"
    assembly.fiber_cable.status = "deployed"
    
    # Update assembly status
    assembly.status = AssemblyStatus.DEPLOYED
    
    # Create connection between ports using Connection model
    from app.models.connection import Connection
    
    connection_a = Connection(
        tenant_id=current_user.tenant_id,
        cable_id=assembly.fiber_cable_id,
        port_id=port_a.id,
        end_label="A"
    )
    connection_b = Connection(
        tenant_id=current_user.tenant_id,
        cable_id=assembly.fiber_cable_id,
        port_id=port_b.id,
        end_label="B"
    )
    
    db.add(connection_a)
    db.add(connection_b)
    
    db.commit()
    
    logger.info(f"Deployed CableAssembly {assembly_id} to ports {request.port_a_id} and {request.port_b_id}")
    
    return {
        "message": f"Assembly '{assembly.name}' deployed successfully",
        "assembly_id": assembly_id,
        "port_a_id": request.port_a_id,
        "port_b_id": request.port_b_id,
        "transceiver_a_installed": True,
        "transceiver_b_installed": True,
        "cable_connected": True
    }


@router.post("/{assembly_id}/undeploy", response_model=dict)
async def undeploy_cable_assembly(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Undeploy a cable assembly.
    
    This:
    1. Removes transceivers from ports
    2. Disconnects cable
    3. Updates assembly status to 'available'
    """
    
    # Get assembly
    query = db.query(CableAssembly).filter(CableAssembly.id == assembly_id)
    query = apply_tenant_filter(query, CableAssembly)
    assembly = query.first()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable assembly {assembly_id} not found"
        )
    
    if assembly.status != AssemblyStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assembly is not deployed"
        )
    
    # Find ports with these transceivers installed
    port_a = db.query(NetworkPort).filter(
        NetworkPort.installed_transceiver_id == assembly.transceiver_a_id
    ).first()
    
    port_b = db.query(NetworkPort).filter(
        NetworkPort.installed_transceiver_id == assembly.transceiver_b_id
    ).first()
    
    # Remove transceivers from ports
    if port_a:
        port_a.installed_transceiver_id = None
    if port_b:
        port_b.installed_transceiver_id = None
    
    # Remove cable connections
    from app.models.connection import Connection
    db.query(Connection).filter(Connection.cable_id == assembly.fiber_cable_id).delete()
    
    # Update asset statuses back to in_storage
    assembly.transceiver_a.status = "in_storage"
    assembly.transceiver_b.status = "in_storage"
    assembly.fiber_cable.status = "in_storage"
    
    # Update assembly status
    assembly.status = AssemblyStatus.AVAILABLE
    
    db.commit()
    
    logger.info(f"Undeployed CableAssembly {assembly_id}")
    
    return {
        "message": f"Assembly '{assembly.name}' undeployed successfully",
        "assembly_id": assembly_id
    }
