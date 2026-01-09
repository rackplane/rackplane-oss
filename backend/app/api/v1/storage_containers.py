# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Storage Containers API Endpoints
CRUD operations for storage container management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_writable_user
from app.models.storage_container import StorageContainer
from app.models.asset import Asset
from app.models.asset_type import AssetTypeModel
from app.models.user import User
from app.schemas.storage_container import (
    StorageContainerCreate,
    StorageContainerUpdate,
    StorageContainerResponse
)
from app.schemas.asset import AssetResponse
from app.utils.audit_helpers import audit_create, audit_update, audit_delete

router = APIRouter()


@router.get("/")
async def list_storage_containers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all storage containers with asset type information for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(StorageContainer)
    query = apply_tenant_filter(query, StorageContainer)
    containers = query.offset(skip).limit(limit).all()

    # Enrich each container with asset type information
    result = []
    for container in containers:
        # Get all assets in this container grouped by type (tenant-scoped)
        query = db.query(Asset).filter(
            Asset.storage_container_id == container.id
        )
        query = apply_tenant_filter(query, Asset)
        assets_by_type = query.all()

        # Calculate counts per asset type (accounting for custom_fields quantity)
        type_data = {}
        for asset in assets_by_type:
            asset_type = asset.asset_type
            quantity = 1  # Default quantity

            # Check if asset has custom_fields with quantity
            if asset.custom_fields and isinstance(asset.custom_fields, dict):
                quantity = asset.custom_fields.get('quantity', 1)

            if asset_type not in type_data:
                type_data[asset_type] = {
                    'count': 0,
                    'total_quantity': 0
                }

            type_data[asset_type]['count'] += 1  # Number of entries
            type_data[asset_type]['total_quantity'] += quantity  # Sum of quantities

        # Get display names and format result
        from app.core.tenant_query import apply_tenant_filter
        
        asset_types = []
        for asset_type_name, data in type_data.items():
            query = db.query(AssetTypeModel).filter(
                AssetTypeModel.name == asset_type_name
            )
            query = apply_tenant_filter(query, AssetTypeModel)
            asset_type_obj = query.first()
            asset_types.append({
                "asset_type": asset_type_name,
                "display_name": asset_type_obj.display_name if asset_type_obj else asset_type_name,
                "count": data['total_quantity']  # Use total quantity instead of entry count
            })

        container_dict = {
            "id": container.id,
            "name": container.name,
            "container_type": container.container_type,
            "datacenter_id": container.datacenter_id,
            "room_id": container.room_id,
            "location": container.location,
            "description": container.description,
            "barcode": container.barcode,
            "created_at": container.created_at,
            "updated_at": container.updated_at,
            "asset_types": asset_types,
            "total_assets": sum(item["count"] for item in asset_types)
        }
        result.append(container_dict)

    return result


@router.get("/{container_id}", response_model=StorageContainerResponse)
async def get_storage_container(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific storage container"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")
    return container


@router.post("/", response_model=StorageContainerResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_container(
    container: StorageContainerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new storage container"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Check if name already exists within tenant scope
    query = db.query(StorageContainer).filter(StorageContainer.name == container.name)
    query = apply_tenant_filter(query, StorageContainer)
    existing = query.first()
    if existing:
        raise HTTPException(status_code=400, detail="Storage container with this name already exists")

    # Check if barcode already exists within tenant scope (if provided)
    if container.barcode:
        query = db.query(StorageContainer).filter(StorageContainer.barcode == container.barcode)
        query = apply_tenant_filter(query, StorageContainer)
        existing_barcode = query.first()
        if existing_barcode:
            raise HTTPException(status_code=400, detail="Storage container with this barcode already exists")

    db_container = StorageContainer(**container.model_dump())
    db.add(db_container)
    db.commit()
    db.refresh(db_container)
    
    # Audit log the create operation
    audit_create(db, db_container, current_user, request)
    
    return db_container


@router.put("/{container_id}", response_model=StorageContainerResponse)
async def update_storage_container(
    container_id: int,
    container_update: StorageContainerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a storage container"""
    from app.core.tenant_query import apply_tenant_filter
    from app.services.audit_service import get_model_dict
    
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    db_container = query.first()
    if not db_container:
        raise HTTPException(status_code=404, detail="Storage container not found")

    # Capture old values BEFORE making changes
    old_values = get_model_dict(db_container)

    # Update fields
    for key, value in container_update.model_dump(exclude_unset=True).items():
        setattr(db_container, key, value)

    db.commit()
    db.refresh(db_container)
    
    # Audit log the update operation
    audit_update(db, db_container, current_user, request, old_values)
    
    return db_container


@router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_storage_container(
    container_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a storage container"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")

    # Audit log BEFORE deleting
    audit_delete(db, container, current_user, request)

    db.delete(container)
    db.commit()
    return None


@router.get("/{container_id}/assets", response_model=List[AssetResponse])
async def get_container_assets(
    container_id: int,
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assets in a specific storage container, optionally filtered by asset type"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Verify container exists (tenant-scoped)
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")

    # Build query for assets (tenant-scoped)
    # Get ALL assets in this container, regardless of status
    # (Items in storage containers can have various statuses)
    query = db.query(Asset).filter(Asset.storage_container_id == container_id)
    query = apply_tenant_filter(query, Asset)

    # Apply asset type filter if provided
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    assets = query.all()
    return assets


@router.get("/{container_id}/asset-types")
async def get_container_asset_types(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get asset type counts and details for a specific storage container"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Verify container exists (tenant-scoped)
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")

    # Get all assets in this container (tenant-scoped)
    query = db.query(Asset).filter(
        Asset.storage_container_id == container_id
    )
    query = apply_tenant_filter(query, Asset)
    assets = query.all()

    # Calculate counts per asset type (accounting for custom_fields quantity)
    type_data = {}
    for asset in assets:
        asset_type = asset.asset_type
        quantity = 1  # Default quantity

        # Check if asset has custom_fields with quantity
        if asset.custom_fields and isinstance(asset.custom_fields, dict):
            quantity = asset.custom_fields.get('quantity', 1)

        if asset_type not in type_data:
            type_data[asset_type] = 0

        type_data[asset_type] += quantity  # Sum up quantities

    from app.core.tenant_query import apply_tenant_filter
    
    # Enrich with display names from asset_types table
    result = []
    for asset_type_name, total_quantity in type_data.items():
        query = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == asset_type_name
        )
        query = apply_tenant_filter(query, AssetTypeModel)
        asset_type_obj = query.first()

        result.append({
            "asset_type": asset_type_name,
            "display_name": asset_type_obj.display_name if asset_type_obj else asset_type_name,
            "count": total_quantity  # Use total quantity
        })

    return {
        "container_id": container_id,
        "container_name": container.name,
        "asset_types": result,
        "total_assets": sum(item["count"] for item in result)
    }


@router.get("/{container_id}/stock-summary")
async def get_storage_container_stock_summary(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive stock summary for a storage container, including grouped items by type"""
    from app.services.inventory_service import get_container_stock_summary
    
    summary = get_container_stock_summary(container_id, db, is_storage_container=True)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage container with ID {container_id} not found"
        )
    return summary


@router.get("/{container_id}/stock-by-type")
async def get_storage_container_stock_by_type(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get stock levels grouped by item type (manufacturer + model + asset_type) for a storage container"""
    from app.services.inventory_service import get_stock_by_item_type
    
    stock_by_type = get_stock_by_item_type(container_id, db, is_storage_container=True)
    if stock_by_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage container with ID {container_id} not found"
        )
    return stock_by_type


@router.get("/{container_id}/stock-thresholds")
async def get_container_stock_thresholds(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all stock thresholds for a storage container"""
    from app.core.tenant_query import apply_tenant_filter
    from app.models.container_stock_threshold import ContainerStockThreshold
    from app.schemas.container_stock_threshold import ContainerStockThresholdResponse
    
    # Verify container exists
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")
    
    # Get thresholds
    thresholds_query = db.query(ContainerStockThreshold).filter(
        ContainerStockThreshold.storage_container_id == container_id
    )
    thresholds_query = apply_tenant_filter(thresholds_query, ContainerStockThreshold)
    thresholds = thresholds_query.all()
    
    return [ContainerStockThresholdResponse(
        id=t.id,
        storage_container_id=t.storage_container_id,
        asset_type=t.asset_type,
        manufacturer=t.manufacturer,
        model=t.model,
        min_threshold=t.min_threshold,
        max_quantity=t.max_quantity
    ) for t in thresholds]


@router.post("/{container_id}/stock-thresholds")
async def create_container_stock_threshold(
    container_id: int,
    asset_type: str = Body(...),
    manufacturer: Optional[str] = Body(None),
    model: Optional[str] = Body(None),
    min_threshold: int = Body(..., ge=1),
    max_quantity: Optional[int] = Body(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)
):
    """Create a stock threshold for a specific item type in a storage container"""
    from app.core.tenant_query import apply_tenant_filter
    from app.models.container_stock_threshold import ContainerStockThreshold
    from app.schemas.container_stock_threshold import ContainerStockThresholdResponse
    from app.core.tenant import get_current_tenant_id
    
    # Verify container exists
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")
    
    tenant_id = get_current_tenant_id()
    
    # Check if threshold already exists
    existing = db.query(ContainerStockThreshold).filter(
        ContainerStockThreshold.storage_container_id == container_id,
        ContainerStockThreshold.asset_type == asset_type,
        ContainerStockThreshold.manufacturer == (manufacturer or None),
        ContainerStockThreshold.model == (model or None),
        ContainerStockThreshold.tenant_id == tenant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Stock threshold already exists for {asset_type} / {manufacturer or 'any'} / {model or 'any'}"
        )
    
    # Create threshold
    threshold = ContainerStockThreshold(
        storage_container_id=container_id,
        asset_type=asset_type,
        manufacturer=manufacturer,
        model=model,
        min_threshold=min_threshold,
        max_quantity=max_quantity,
        tenant_id=tenant_id
    )
    db.add(threshold)
    db.commit()
    db.refresh(threshold)
    
    return ContainerStockThresholdResponse(
        id=threshold.id,
        storage_container_id=threshold.storage_container_id,
        asset_type=threshold.asset_type,
        manufacturer=threshold.manufacturer,
        model=threshold.model,
        min_threshold=threshold.min_threshold,
        max_quantity=threshold.max_quantity
    )


@router.put("/{container_id}/stock-thresholds/{threshold_id}")
async def update_container_stock_threshold(
    container_id: int,
    threshold_id: int,
    update_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)
):
    """Update a stock threshold"""
    from app.core.tenant_query import apply_tenant_filter
    from app.models.container_stock_threshold import ContainerStockThreshold
    from app.schemas.container_stock_threshold import ContainerStockThresholdResponse
    
    # Verify container exists
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")
    
    # Get threshold
    threshold_query = db.query(ContainerStockThreshold).filter(
        ContainerStockThreshold.id == threshold_id,
        ContainerStockThreshold.storage_container_id == container_id
    )
    threshold_query = apply_tenant_filter(threshold_query, ContainerStockThreshold)
    threshold = threshold_query.first()
    
    if not threshold:
        raise HTTPException(status_code=404, detail="Stock threshold not found")
    
    # Update threshold fields
    min_threshold = update_data.get("min_threshold")
    max_quantity = update_data.get("max_quantity")
    
    if min_threshold is not None:
        if not isinstance(min_threshold, int) or min_threshold < 1:
            raise HTTPException(status_code=400, detail="min_threshold must be an integer >= 1")
        threshold.min_threshold = min_threshold
        
    if "max_quantity" in update_data:
        # Allow clearing max_quantity if None is passed explicitly or implicitly via omission if schema allows, 
        # but here we use dict so "in" check. If value is None, it clears it.
        # If value is provided, check >= 1
        if max_quantity is not None and (not isinstance(max_quantity, int) or max_quantity < 1):
            raise HTTPException(status_code=400, detail="max_quantity must be an integer >= 1")
        threshold.max_quantity = max_quantity
    db.commit()
    db.refresh(threshold)
    
    return ContainerStockThresholdResponse(
        id=threshold.id,
        storage_container_id=threshold.storage_container_id,
        asset_type=threshold.asset_type,
        manufacturer=threshold.manufacturer,
        model=threshold.model,
        min_threshold=threshold.min_threshold,
        max_quantity=threshold.max_quantity
    )


@router.delete("/{container_id}/stock-thresholds/{threshold_id}")
async def delete_container_stock_threshold(
    container_id: int,
    threshold_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)
):
    """Delete a stock threshold"""
    from app.core.tenant_query import apply_tenant_filter
    from app.models.container_stock_threshold import ContainerStockThreshold
    
    # Verify container exists
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    container = query.first()
    if not container:
        raise HTTPException(status_code=404, detail="Storage container not found")
    
    # Get threshold
    threshold_query = db.query(ContainerStockThreshold).filter(
        ContainerStockThreshold.id == threshold_id,
        ContainerStockThreshold.storage_container_id == container_id
    )
    threshold_query = apply_tenant_filter(threshold_query, ContainerStockThreshold)
    threshold = threshold_query.first()
    
    if not threshold:
        raise HTTPException(status_code=404, detail="Stock threshold not found")
    
    db.delete(threshold)
    db.commit()
    
    return {"message": "Stock threshold deleted"}
