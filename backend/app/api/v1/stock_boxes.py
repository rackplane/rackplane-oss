# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Stock Box Management API Endpoints

Endpoints for generating and managing storage boxes based on cable specifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant_query import apply_tenant_filter
from app.models.asset import Asset
from app.models.user import User
from app.services.stock_service import generate_storage_box_name, find_or_create_storage_box
from app.schemas.asset import AssetResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/generate-name/{asset_id}", response_model=Dict[str, Any])
async def get_storage_box_name(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a storage box name for a cable asset based on its specifications.
    
    Returns the generated box name using the naming convention:
    - DAC: DAC-{speed}-{connectorA}-{connectorB}-{length}
    - Fiber: FIBER-{type}-{connectorA}-{connectorB}-{length}
    """
    # Fetch the asset
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    box_name = generate_storage_box_name(asset)
    
    if not box_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate box name. Missing required cable specifications (speed/type, connectors, length)."
        )
    
    return {
        "box_name": box_name,
        "asset_id": asset_id,
        "asset_tag": asset.asset_tag,
        "asset_type": asset.asset_type
    }


@router.post("/find-or-create/{asset_id}", response_model=AssetResponse)
async def find_or_create_box_for_cable(
    asset_id: int,
    min_stock_threshold: int = Body(5, embed=True, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Find or create a storage box for a cable asset.
    
    This endpoint:
    1. Generates a box name based on the cable's specifications
    2. Searches for an existing box with that name
    3. If not found, creates a new storage box
    4. Returns the box asset
    
    Args:
        asset_id: ID of the cable asset
        min_stock_threshold: Minimum stock threshold for the box (default: 5)
    """
    # Fetch the cable asset
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    cable_asset = query.first()
    
    if not cable_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    # Check if it's a cable type
    if 'cable' not in cable_asset.asset_type.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset {cable_asset.asset_tag} is not a cable type. Only cables can have storage boxes generated."
        )
    
    # Find or create the box
    box = find_or_create_storage_box(db, cable_asset, min_stock_threshold)
    
    if not box:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate storage box. Missing required cable specifications (speed/type, connectors, length)."
        )
    
    return box


@router.post("/find-or-create-temp", response_model=Dict[str, Any])
async def find_or_create_box_from_specs(
    asset_type: str = Body(...),
    custom_fields: Dict[str, Any] = Body(...),
    min_stock_threshold: int = Body(5, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Find or create a storage box from cable specifications (without requiring an existing asset).
    
    This is useful for the UI when creating a new cable - it can generate the box name
    before the cable is saved.
    
    Args:
        asset_type: Type of cable (e.g., 'dac_cable', 'fiber_cable')
        custom_fields: Dictionary of cable specifications (speed, connectors, length, etc.)
        min_stock_threshold: Minimum stock threshold for the box (default: 5)
    """
    from app.core.tenant import get_current_tenant_id
    
    # Create a temporary asset object for name generation
    class TempAsset:
        def __init__(self, asset_type: str, custom_fields: dict):
            self.asset_type = asset_type
            self.custom_fields = custom_fields
            self.asset_tag = ""  # Not needed for name generation
            self.id = 0  # Not needed for name generation
    
    temp_asset = TempAsset(asset_type, custom_fields)
    box_name = generate_storage_box_name(temp_asset)
    
    if not box_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate box name. Missing required cable specifications (speed/type, connectors, length)."
        )
    
    # Search for existing box with this name
    query = db.query(Asset).filter(
        Asset.asset_tag == box_name,
        Asset.min_stock_threshold > 0
    )
    query = apply_tenant_filter(query, Asset)
    existing_box = query.first()
    
    if existing_box:
        return {
            "box_name": box_name,
            "box_id": existing_box.id,
            "box_tag": existing_box.asset_tag,
            "created": False
        }
    
    # Create new storage box
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cannot create storage box: no tenant context"
        )
    
    from app.models.asset import AssetStatus
    from app.services.serial_service import generate_serial_number, generate_asset_tag
    
    # Generate proper serial number using the serial service
    serial_number = generate_serial_number(db, "storage_box", tenant_id)
    asset_tag = generate_asset_tag(db, "storage_box", tenant_id)
    
    new_box = Asset(
        asset_tag=asset_tag,  # Use generated asset tag
        serial_number=serial_number,  # Use proper format: TYPE-TENANT-RANDOM-CHECK
        asset_type="storage_box",  # Changed from "storage_device" - storage_device is for physical systems with disk drives
        manufacturer="System",
        model="Storage Box",
        status=AssetStatus.ACTIVE,
        min_stock_threshold=min_stock_threshold,  # Use the provided threshold, not hardcoded
        description=f"Auto-generated storage box for {asset_type} cables (min threshold: {min_stock_threshold})",
        tenant_id=tenant_id
    )
    
    db.add(new_box)
    db.commit()
    db.refresh(new_box)
    
    logger.info(
        f"Created new storage box: {box_name} (ID: {new_box.id}) "
        f"with min_stock_threshold: {min_stock_threshold}"
    )
    
    return {
        "box_name": box_name,
        "box_id": new_box.id,
        "box_tag": new_box.asset_tag,
        "min_stock_threshold": new_box.min_stock_threshold,
        "created": True
    }


@router.get("/list-by-type", response_model=Dict[str, Any])
async def list_storage_boxes_by_type(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all storage boxes, grouped by their naming convention type.
    
    This helps identify which boxes follow the standardized naming (DAC-*, FIBER-*)
    and which are custom named.
    """
    # Get all storage boxes (assets with min_stock_threshold > 0)
    query = db.query(Asset).filter(Asset.min_stock_threshold > 0)
    query = apply_tenant_filter(query, Asset)
    
    total = query.count()
    boxes = query.offset(skip).limit(limit).all()
    
    # Categorize boxes by naming convention
    dac_boxes = []
    fiber_boxes = []
    other_boxes = []
    
    for box in boxes:
        box_name = box.asset_tag.upper()
        if box_name.startswith('DAC-'):
            dac_boxes.append(box)
        elif box_name.startswith('FIBER-'):
            fiber_boxes.append(box)
        else:
            other_boxes.append(box)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "dac_boxes": len(dac_boxes),
        "fiber_boxes": len(fiber_boxes),
        "other_boxes": len(other_boxes),
        "boxes": boxes
    }

