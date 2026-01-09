# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""PortTemplate API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.port_template import PortTemplate
from app.models.network import NetworkPort, PortType, PortStatus
from app.models.asset import Asset
from app.models.user import User
from app.schemas.port_template import (
    PortTemplateCreate,
    PortTemplateUpdate,
    PortTemplateResponse,
    ApplyTemplateRequest
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=PortTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_port_template(
    template_data: PortTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new port template"""

    # Check for duplicate
    existing = db.query(PortTemplate).filter(
        PortTemplate.manufacturer == template_data.manufacturer,
        PortTemplate.model == template_data.model
    )
    existing = apply_tenant_filter(existing, PortTemplate)

    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template for {template_data.manufacturer} {template_data.model} already exists"
        )

    # Convert Pydantic models to dicts for JSON storage
    port_defs = [p.model_dump() for p in template_data.port_definitions]

    new_template = PortTemplate(
        tenant_id=current_user.tenant_id,
        manufacturer=template_data.manufacturer,
        model=template_data.model,
        description=template_data.description,
        port_definitions=port_defs
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    logger.info(f"Created PortTemplate {new_template.id}: {template_data.manufacturer} {template_data.model}")
    return new_template


@router.get("/", response_model=List[PortTemplateResponse])
async def list_port_templates(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all port templates"""

    query = db.query(PortTemplate)
    query = apply_tenant_filter(query, PortTemplate)

    if manufacturer:
        query = query.filter(PortTemplate.manufacturer.ilike(f"%{manufacturer}%"))

    return query.order_by(PortTemplate.manufacturer, PortTemplate.model).all()


@router.get("/{template_id}", response_model=PortTemplateResponse)
async def get_port_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific port template"""

    query = db.query(PortTemplate).filter(PortTemplate.id == template_id)
    query = apply_tenant_filter(query, PortTemplate)
    template = query.first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )

    return template


@router.put("/{template_id}", response_model=PortTemplateResponse)
async def update_port_template(
    template_id: int,
    template_data: PortTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a port template"""

    query = db.query(PortTemplate).filter(PortTemplate.id == template_id)
    query = apply_tenant_filter(query, PortTemplate)
    template = query.first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )

    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    if "port_definitions" in update_data and update_data["port_definitions"] is not None:
        # Convert Pydantic models to dicts
        update_data["port_definitions"] = [p.model_dump() if hasattr(p, 'model_dump') else p for p in update_data["port_definitions"]]
    
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)

    logger.info(f"Updated PortTemplate {template_id}")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a port template"""

    query = db.query(PortTemplate).filter(PortTemplate.id == template_id)
    query = apply_tenant_filter(query, PortTemplate)
    template = query.first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )

    db.delete(template)
    db.commit()

    logger.info(f"Deleted PortTemplate {template_id}")
    return None


@router.post("/apply", response_model=dict)
async def apply_template_to_device(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Apply a port template to a device"""

    # Verify asset exists
    asset_query = db.query(Asset).filter(Asset.id == request.asset_id)
    asset_query = apply_tenant_filter(asset_query, Asset)
    asset = asset_query.first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {request.asset_id} not found"
        )

    # Verify template exists
    template_query = db.query(PortTemplate).filter(PortTemplate.id == request.template_id)
    template_query = apply_tenant_filter(template_query, PortTemplate)
    template = template_query.first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {request.template_id} not found"
        )

    # Check for existing ports
    existing_ports = db.query(NetworkPort).filter(NetworkPort.asset_id == request.asset_id).all()

    if existing_ports and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset already has {len(existing_ports)} ports. Use overwrite=true to replace them."
        )

    # Delete existing ports if overwrite
    if request.overwrite:
        for port in existing_ports:
            db.delete(port)
        db.flush()

    # Create ports from template
    created_ports = []
    for port_def in template.port_definitions:
        # Validate and convert port_type to enum
        port_type_str = port_def.get("port_type", "other").lower()
        try:
            port_type_enum = PortType(port_type_str)
        except ValueError:
            port_type_enum = PortType.OTHER

        new_port = NetworkPort(
            tenant_id=current_user.tenant_id,
            asset_id=request.asset_id,
            port_number=port_def.get("port_number"),
            port_name=f"{asset.asset_tag}:{port_def.get('port_number')}",
            port_label=port_def.get("port_number"),
            port_type=port_type_enum,
            speed_mbps=port_def.get("speed_mbps"),
            duplex=port_def.get("duplex", "full"),
            poe_capable=port_def.get("poe_capable", False),
            poe_power_watts=port_def.get("poe_max_watts"),
            status=PortStatus.INACTIVE,
            enabled=True
        )
        db.add(new_port)
        created_ports.append(new_port)

    db.commit()

    logger.info(f"Applied template {template.manufacturer} {template.model} to asset {asset.asset_tag} - created {len(created_ports)} ports")

    return {
        "message": f"Created {len(created_ports)} ports on {asset.asset_tag}",
        "ports_created": len(created_ports),
        "template_applied": f"{template.manufacturer} {template.model}"
    }
