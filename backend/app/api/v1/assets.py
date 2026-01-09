# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Assets API Endpoints
Real-time inventory tracking and asset management

This module provides comprehensive REST API endpoints for asset (hardware inventory)
management. All endpoints are tenant-scoped and require authentication.

Key Endpoints:
- GET /api/v1/assets: List assets with filtering and pagination
- POST /api/v1/assets: Create new asset
- GET /api/v1/assets/{id}: Get asset details
- PUT /api/v1/assets/{id}: Update asset
- DELETE /api/v1/assets/{id}: Delete asset
- POST /api/v1/assets/{id}/photos: Upload asset photos
- GET /api/v1/assets/containers/{container_id}/stock: Get stock levels
- POST /api/v1/assets/bulk-assign-to-storage-box: Bulk assign to storage boxes

Features:
- Multi-tenant isolation (automatic via middleware)
- Stock level tracking and low stock alerts
- Asset lifecycle management
- Photo uploads and management
- Bulk operations
- Advanced filtering and search

Security:
- All endpoints require authentication
- Tenant isolation enforced automatically
- Asset operations scoped to current tenant
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Body, Request, Security
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_writable_user
from app.core.scopes import get_current_api_key_with_scopes
from app.models.api_key import ApiKey
from app.models.asset import Asset, AssetStatus, AssetLifecycleEvent
from app.models.asset_type import AssetTypeModel
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetListResponse, EOLWarningResponse
from app.services.asset_service import AssetService
from app.services.inventory_service import get_container_stock_info, get_stock_by_item_type, get_container_stock_summary
from app.services.audit_service import log_create, log_update, log_delete, get_model_dict
from app.services.serial_service import (
    generate_serial_number,
    generate_asset_tag,
    generate_bulk_serials,
    validate_check_digit,
    get_type_prefix,
)

router = APIRouter()


@router.post("/generate-serial")
async def generate_serial(
    asset_type: str = Body(..., embed=True, description="Asset type (e.g., 'dac_cable', 'server')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate a unique serial number and asset tag for an asset.
    """
    serial = generate_serial_number(db, asset_type, current_user.tenant_id)
    tag = generate_asset_tag(db, asset_type, current_user.tenant_id)

    return {
        "serial_number": serial,
        "asset_tag": tag,
        "type_prefix": get_type_prefix(asset_type),
    }


@router.post("/generate-bulk-serials")
async def generate_bulk_serials_endpoint(
    asset_type: str = Body(..., embed=True, description="Asset type (e.g., 'dac_cable', 'server')"),
    quantity: int = Body(..., embed=True, ge=1, le=1000, description="Number of serial/tag pairs to generate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate multiple unique serial numbers and asset tags for bulk creation.
    """
    if quantity > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 items per bulk generation request",
        )

    pairs = generate_bulk_serials(db, asset_type, quantity, current_user.tenant_id)
    return {
        "items": [{"serial_number": s, "asset_tag": t} for s, t in pairs],
        "count": len(pairs),
        "type_prefix": get_type_prefix(asset_type),
    }


@router.post("/validate-serial")
async def validate_serial(
    serial_number: str = Body(..., embed=True, description="Serial number to validate"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Validate a serial number's check digit.
    """
    is_valid = validate_check_digit(serial_number)
    return {
        "serial_number": serial_number,
        "is_valid": is_valid,
        "message": "Valid serial number" if is_valid else "Invalid check digit - possible typo",
    }


@router.get("/skus/autocomplete")
async def autocomplete_skus(
    q: str = Query(..., min_length=1, description="Search query for SKU autocomplete"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Autocomplete SKUs from existing inventory.
    
    Returns distinct SKUs from assets table that match the query,
    ordered by frequency of use (most common first).
    """
    from sqlalchemy import func, distinct
    
    # Query distinct SKUs that match the search term, ordered by usage count
    query = db.query(
        Asset.sku,
        func.count(Asset.id).label('usage_count')
    ).filter(
        Asset.tenant_id == current_user.tenant_id,
        Asset.sku.isnot(None),
        Asset.sku != '',
        Asset.sku.ilike(f"%{q}%")
    ).group_by(
        Asset.sku
    ).order_by(
        func.count(Asset.id).desc(),
        Asset.sku.asc()
    ).limit(limit)
    
    results = query.all()
    
    return {
        "skus": [
            {
                "sku": sku,
                "usage_count": count
            }
            for sku, count in results
        ],
        "count": len(results)
    }


@router.get("/containers/{container_id}/stock")
async def get_container_stock(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get stock level information for an asset container"""
    stock_info = get_container_stock_info(container_id, db)
    if not stock_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with ID {container_id} not found"
        )
    return stock_info


@router.get("/containers/{container_id}/stock-by-type")
async def get_container_stock_by_type(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get stock levels grouped by item type (manufacturer + model + asset_type)"""
    stock_by_type = get_stock_by_item_type(container_id, db)
    if stock_by_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with ID {container_id} not found"
        )
    return stock_by_type


@router.get("/containers/{container_id}/stock-summary")
async def get_container_stock_summary_endpoint(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive stock summary including stock levels by item type"""
    from app.models.storage_container import StorageContainer
    from app.models.asset import Asset
    from app.core.tenant_query import apply_tenant_filter
    from app.services.inventory_service import get_container_stock_info, get_stock_by_item_type
    
    # Auto-detect: Check if it's a StorageContainer first, otherwise treat as Asset-based box
    # CRITICAL: Apply tenant filter for multi-tenant isolation
    query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    query = apply_tenant_filter(query, StorageContainer)
    storage_container = query.first()
    is_storage_container = storage_container is not None
    
    if is_storage_container:
        summary = get_container_stock_summary(container_id, db, is_storage_container=True)
    else:
        # Legacy Asset-based storage box - use get_container_stock_info and format as summary
        stock_info = get_container_stock_info(container_id, db)
        if stock_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Container with ID {container_id} not found"
            )
        # Format as summary for compatibility
        stock_by_type = get_stock_by_item_type(container_id, db, is_storage_container=False)
        summary = {
            'container_id': container_id,
            'container_name': stock_info.get('container_name', 'Unknown'),
            'min_threshold': stock_info.get('min_threshold', 0),
            'total_items': stock_info.get('current_count', 0),
            'item_types': stock_by_type,
            'low_stock_types': [item for item in stock_by_type if stock_info.get('is_low_stock', False)],
            'is_low_stock': stock_info.get('is_low_stock', False)
        }
    
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container with ID {container_id} not found"
        )
    return summary


@router.get("/containers/{container_id}/items", response_model=List[AssetResponse])
async def get_container_items(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all items inside a storage box asset (by container_id)"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Verify container exists
    container_query = db.query(Asset).filter(Asset.id == container_id)
    container_query = apply_tenant_filter(container_query, Asset)
    container = container_query.first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage box with ID {container_id} not found"
        )
    
    # Get all items in this container
    items_query = db.query(Asset).filter(Asset.container_id == container_id)
    items_query = apply_tenant_filter(items_query, Asset)
    items = items_query.all()
    
    return items


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)  # Read-only users cannot create assets
):
    """Create a new asset in inventory"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Validate that asset_type exists in asset_types table (within tenant scope)
    # First try by name (the actual field), then by display_name (in case frontend sends display name)
    # Also try case-insensitive match for name
    query = db.query(AssetTypeModel).filter(
        AssetTypeModel.name == asset.asset_type,
        AssetTypeModel.is_active == True
    )
    query = apply_tenant_filter(query, AssetTypeModel)
    asset_type_exists = query.first()
    
    # If not found by exact name, try case-insensitive name match
    if not asset_type_exists:
        from sqlalchemy import func
        query = db.query(AssetTypeModel).filter(
            func.lower(AssetTypeModel.name) == asset.asset_type.lower(),
            AssetTypeModel.is_active == True
        )
        query = apply_tenant_filter(query, AssetTypeModel)
        asset_type_exists = query.first()
        if asset_type_exists:
            # Update to use the correct name (preserves case)
            asset.asset_type = asset_type_exists.name
    
    # If still not found, try by display_name (case-insensitive)
    if not asset_type_exists:
        from sqlalchemy import func
        query = db.query(AssetTypeModel).filter(
            func.lower(AssetTypeModel.display_name) == asset.asset_type.lower(),
            AssetTypeModel.is_active == True
        )
        query = apply_tenant_filter(query, AssetTypeModel)
        asset_type_by_display = query.first()
        
        if asset_type_by_display:
            # Found by display_name, update the asset to use the correct name
            asset.asset_type = asset_type_by_display.name
            asset_type_exists = asset_type_by_display
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid asset_type: '{asset.asset_type}'. Please add this type in Asset Types page first."
            )

    service = AssetService(db)
    try:
        created_asset = service.create_asset(asset)
    except IntegrityError as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
             raise HTTPException(status_code=400, detail="Asset with this tag or serial number already exists")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Log the create operation
    try:
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        log_create(
            db=db,
            instance=created_asset,
            user_id=current_user.id,
            username=current_user.username,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.commit()
    except Exception as e:
        # Don't fail the request if audit logging fails
        import logging
        logging.getLogger(__name__).error(f"Failed to log asset creation: {e}", exc_info=True)
    
    return created_asset


@router.get("/storage-boxes", response_model=List[AssetResponse])
async def list_storage_boxes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all assets that are storage boxes (have min_stock_threshold and are containers)"""
    from app.core.tenant_query import apply_tenant_filter
    from sqlalchemy import func
    
    # Get all assets with min_stock_threshold > 0
    query = db.query(Asset).filter(
        Asset.min_stock_threshold.isnot(None),
        Asset.min_stock_threshold > 0
    )
    query = apply_tenant_filter(query, Asset)
    
    # Count how many items point to each asset via container_id
    # Only return assets that have items in them OR are storage box types
    all_assets = query.all()
    storage_boxes = []
    
    for asset in all_assets:
        # Check if it's a storage box type
        is_storage_type = asset.asset_type and (
            'storage' in asset.asset_type.lower() or
            asset.asset_type.lower() in ['storage_device', 'storage_box']
        )
        
        # EXCLUDE cables - cables should never be storage boxes, even if they have min_stock_threshold set
        is_cable = asset.asset_type and (
            'cable' in asset.asset_type.lower() or
            asset.asset_type.lower() in ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
        )
        
        if is_cable:
            continue  # Skip cables - they should never appear as storage boxes
        
        # IMPORTANT: A storage box should always be included if it has min_stock_threshold > 0
        # The threshold being set means it's intended for stock management, regardless of current contents
        # This prevents boxes from disappearing when stock levels change or when threshold is updated
        # Since we've already excluded cables above, we can safely include any asset with min_stock_threshold > 0
        # OR any asset that is a storage type
        if is_storage_type or asset.min_stock_threshold > 0:
            storage_boxes.append(asset)
    
    return storage_boxes


@router.get(
    "/",
    response_model=AssetListResponse,
    dependencies=[Security(get_current_api_key_with_scopes, scopes=["assets:read"])]
)
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(10000, ge=1, le=100000),  # Increased limit to 10,000 default, max 100,000
    asset_type: Optional[str] = None,  # Dynamic type from asset_types table
    exclude_types: Optional[str] = Query(None, description="Comma-separated list of asset types to exclude"),
    has_ports: Optional[bool] = Query(None, description="Filter to only show assets that have network ports configured"),
    status: Optional[AssetStatus] = None,
    datacenter_id: Optional[int] = None,
    rack_id: Optional[int] = None,
    manufacturer: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    api_key: Optional[ApiKey] = Security(get_current_api_key_with_scopes, scopes=["assets:read"])
):
    """List all assets with filtering options"""
    from app.core.tenant_query import apply_tenant_filter
    from app.core.tenant import get_current_tenant_id
    from app.models.network import NetworkPort
    import logging
    
    logger = logging.getLogger(__name__)
    tenant_id = get_current_tenant_id()
    logger.info(f"list_assets: tenant_id={tenant_id}, user={current_user.username}, user_tenant_id={current_user.tenant_id}")
    
    # Ensure tenant_id is set from user if not in context
    if tenant_id is None and current_user.tenant_id:
        from app.core.tenant import set_current_tenant_id
        set_current_tenant_id(current_user.tenant_id)
        tenant_id = current_user.tenant_id
        logger.warning(f"Tenant_id was None, set from user: {tenant_id}")
    
    service = AssetService(db)

    query = db.query(Asset)
    # Apply tenant filter first - CRITICAL for tenant isolation
    query = apply_tenant_filter(query, Asset)

    # Apply filters
    if asset_type:
        if ',' in asset_type:
            types = [t.strip() for t in asset_type.split(',') if t.strip()]
            query = query.filter(Asset.asset_type.in_(types))
        else:
            query = query.filter(Asset.asset_type == asset_type)
    
    # Exclude specific asset types (comma-separated)
    if exclude_types:
        types_to_exclude = [t.strip() for t in exclude_types.split(',') if t.strip()]
        if types_to_exclude:
            query = query.filter(~Asset.asset_type.in_(types_to_exclude))
    
    # Filter to only assets with network ports configured
    if has_ports is True:
        # Subquery to find asset IDs that have at least one port
        assets_with_ports = db.query(NetworkPort.asset_id).distinct().subquery()
        query = query.filter(Asset.id.in_(db.query(assets_with_ports.c.asset_id)))
    elif has_ports is False:
        # Filter to assets WITHOUT ports
        assets_with_ports = db.query(NetworkPort.asset_id).distinct().subquery()
        query = query.filter(~Asset.id.in_(db.query(assets_with_ports.c.asset_id)))
    
    if status:
        query = query.filter(Asset.status == status)
    if datacenter_id:
        query = query.filter(Asset.datacenter_id == datacenter_id)
    if rack_id:
        query = query.filter(Asset.rack_id == rack_id)
    if manufacturer:
        query = query.filter(Asset.manufacturer.ilike(f"%{manufacturer}%"))
    if search:
        # Enhanced Search: Includes description/manufacturer and fuzzy matching
        # Fuzzy matching uses pg_trgm extension (enabled) via '%' operator
        from sqlalchemy import or_

        # Exact substring matches on all relevant fields
        search_filter = or_(
            Asset.asset_tag.ilike(f"%{search}%"),
            Asset.serial_number.ilike(f"%{search}%"),
            Asset.hostname.ilike(f"%{search}%"),
            Asset.model.ilike(f"%{search}%"),
            Asset.manufacturer.ilike(f"%{search}%"),
            Asset.description.ilike(f"%{search}%")
        )

        # Add fuzzy match if installed (pg_trgm)
        # Using operator(%) which is the similarity operator in pg_trgm
        # Both operands must be cast to TEXT (not VARCHAR) for the operator to work
        from sqlalchemy import cast, Text, literal
        # Cast search to text explicitly - use cast(literal()) to ensure proper type
        search_literal = cast(literal(search), Text)
        fuzzy_filter = or_(
            cast(Asset.model, Text).op("%")(search_literal),
            cast(Asset.description, Text).op("%")(search_literal),
            cast(Asset.manufacturer, Text).op("%")(search_literal)
        )

        # Combine: Either it matches substring OR it matches fuzzy
        query = query.filter(or_(search_filter, fuzzy_filter))

    total = query.count()
    assets = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "assets": assets
    }


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed asset information"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/tag/{asset_tag}", response_model=AssetResponse)
async def get_asset_by_tag(
    asset_tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get asset by asset tag"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.asset_tag == asset_tag)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/serial/{serial_number}", response_model=AssetResponse)
async def get_asset_by_serial(
    serial_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get asset by serial number"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.serial_number == serial_number)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)  # Read-only users cannot update assets
):
    """Update asset information"""
    # Validate container_id to prevent circular references
    if asset_update.container_id is not None:
        # Use AssetService to handle validation (includes circular reference checks)
        service = AssetService(db)
        # The validation will happen in service.update_asset()
    
    # Validate asset_type if it's being updated (within tenant scope)
    if asset_update.asset_type is not None:
        from app.core.tenant_query import apply_tenant_filter
        from sqlalchemy import func
        
        query = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == asset_update.asset_type,
            AssetTypeModel.is_active == True
        )
        query = apply_tenant_filter(query, AssetTypeModel)
        asset_type_exists = query.first()
        
        # If not found by exact name, try case-insensitive name match
        if not asset_type_exists:
            query = db.query(AssetTypeModel).filter(
                func.lower(AssetTypeModel.name) == asset_update.asset_type.lower(),
                AssetTypeModel.is_active == True
            )
            query = apply_tenant_filter(query, AssetTypeModel)
            asset_type_exists = query.first()
            if asset_type_exists:
                # Update to use the correct name (preserves case)
                asset_update.asset_type = asset_type_exists.name
        
        # If still not found, try by display_name (case-insensitive)
        if not asset_type_exists:
            query = db.query(AssetTypeModel).filter(
                func.lower(AssetTypeModel.display_name) == asset_update.asset_type.lower(),
                AssetTypeModel.is_active == True
            )
            query = apply_tenant_filter(query, AssetTypeModel)
            asset_type_by_display = query.first()
            
            if asset_type_by_display:
                # Found by display_name, update to use the correct name
                asset_update.asset_type = asset_type_by_display.name
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid asset_type: '{asset_update.asset_type}'. Please add this type in Asset Types page first."
                )

    # Get old values before update for audit log
    from app.core.tenant_query import apply_tenant_filter
    old_asset_query = db.query(Asset).filter(Asset.id == asset_id)
    old_asset_query = apply_tenant_filter(old_asset_query, Asset)
    old_asset = old_asset_query.first()
    
    if not old_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get old values as dict
    from app.services.audit_service import get_model_dict
    old_values = get_model_dict(old_asset)
    
    service = AssetService(db)
    updated_asset = service.update_asset(asset_id, asset_update)
    
    # Log the update operation
    try:
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        # Create a note describing what changed (helpful for debugging)
        # Compare old_values with updated_asset values
        changes_note = []
        if old_values.get('container_id') != updated_asset.container_id:
            changes_note.append(f"container_id: {old_values.get('container_id')} -> {updated_asset.container_id}")
        if old_values.get('status') != updated_asset.status:
            changes_note.append(f"status: {old_values.get('status')} -> {updated_asset.status}")
        notes = "; ".join(changes_note) if changes_note else "Asset updated"
        log_update(
            db=db,
            instance=updated_asset,
            old_values=old_values,
            user_id=current_user.id,
            username=current_user.username,
            tenant_id=current_user.tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes
        )
        db.commit()
    except Exception as e:
        # Don't fail the request if audit logging fails
        import logging
        logging.getLogger(__name__).error(f"Failed to log asset update: {e}", exc_info=True)
    
    return updated_asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)  # Read-only users cannot delete assets
):
    """Delete an asset"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Log the delete operation before deleting
    try:
        log_delete(
            db=db,
            instance=asset,
            user_id=current_user.id,
            username=current_user.username,
            tenant_id=current_user.tenant_id
        )
    except Exception as e:
        # Don't fail the request if audit logging fails
        import logging
        logging.getLogger(__name__).error(f"Failed to log asset deletion: {e}")

    db.delete(asset)
    db.commit()
    return


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_assets(
    asset_ids: List[int] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete multiple assets in bulk"""
    from app.core.tenant_query import apply_tenant_filter
    
    if not asset_ids:
        raise HTTPException(status_code=400, detail="No asset IDs provided")
    
    # Query all assets with tenant filter
    query = db.query(Asset).filter(Asset.id.in_(asset_ids))
    query = apply_tenant_filter(query, Asset)
    assets_to_delete = query.all()
    
    if not assets_to_delete:
        raise HTTPException(status_code=404, detail="No assets found to delete")
    
    # Check if all requested assets were found (some might be in different tenant)
    found_ids = {asset.id for asset in assets_to_delete}
    missing_ids = set(asset_ids) - found_ids
    
    deleted_count = 0
    for asset in assets_to_delete:
        db.delete(asset)
        deleted_count += 1
    
    db.commit()
    
    result = {
        "deleted_count": deleted_count,
        "requested_count": len(asset_ids)
    }
    
    if missing_ids:
        result["missing_ids"] = list(missing_ids)
        result["message"] = f"Deleted {deleted_count} asset(s). {len(missing_ids)} asset(s) were not found or not accessible."
    else:
        result["message"] = f"Successfully deleted {deleted_count} asset(s)."
    
    return result


@router.post("/bulk-assign-to-storage-box", status_code=status.HTTP_200_OK)
async def bulk_assign_to_storage_box(
    asset_ids: List[int] = Body(..., embed=True, description="List of asset IDs to assign"),
    container_id: Optional[int] = Body(None, embed=True, description="Storage box ID (if None, will auto-find/create)"),
    auto_create_box: bool = Body(True, embed=True, description="Auto-create storage box if not found"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk assign assets to a storage box.
    
    If container_id is provided, assigns all assets to that box.
    If container_id is None and auto_create_box=True, automatically finds/creates
    the appropriate storage box for each asset based on its type.
    """
    from app.core.tenant_query import apply_tenant_filter
    from app.models.asset import AssetStatus
    from app.services.stock_service import sync_storage_box_for_cable
    from app.services.audit_service import get_model_dict, log_update
    
    if not asset_ids:
        raise HTTPException(status_code=400, detail="No asset IDs provided")
    
    # Query all assets with tenant filter
    query = db.query(Asset).filter(Asset.id.in_(asset_ids))
    query = apply_tenant_filter(query, Asset)
    assets = query.all()
    
    if not assets:
        raise HTTPException(status_code=404, detail="No assets found")
    
    assigned_count = 0
    skipped_count = 0
    errors = []
    
    for asset in assets:
        try:
            # Capture old values BEFORE making changes for audit log
            old_values = get_model_dict(asset)
            old_container_id = asset.container_id
            old_status = asset.status
            asset_was_modified = False
            
            # If container_id is provided, use it
            if container_id:
                # Verify container exists and is a storage box
                container_query = db.query(Asset).filter(Asset.id == container_id)
                container_query = apply_tenant_filter(container_query, Asset)
                container = container_query.first()
                
                if not container:
                    errors.append(f"Asset {asset.asset_tag} (ID: {asset.id}): Container {container_id} not found")
                    skipped_count += 1
                    continue
                
                if not container.min_stock_threshold or container.min_stock_threshold <= 0:
                    errors.append(f"Asset {asset.asset_tag} (ID: {asset.id}): Container {container.asset_tag} is not a storage box (no min_stock_threshold)")
                    skipped_count += 1
                    continue
                
                asset.container_id = container_id
                if asset.status != AssetStatus.IN_STORAGE:
                    asset.status = AssetStatus.IN_STORAGE
                asset_was_modified = True
                assigned_count += 1
            else:
                # Auto-find/create storage box
                asset_type_lower = (asset.asset_type or '').lower()
                is_cable = (
                    'cable' in asset_type_lower or
                    asset_type_lower in ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
                )
                
                if is_cable and auto_create_box:
                    # sync_storage_box_for_cable may commit internally and modify the asset
                    # Capture old values BEFORE calling it, but refresh after to get latest state
                    storage_box = sync_storage_box_for_cable(db, asset)
                    if storage_box:
                        # Refresh asset to get latest values after sync (which may have committed)
                        db.refresh(asset)
                        # Check if sync_storage_box_for_cable already made the changes
                        container_already_set = asset.container_id == storage_box.id
                        status_already_set = asset.status == AssetStatus.IN_STORAGE
                        
                        # Only make changes if sync didn't already do them
                        if not container_already_set:
                            asset.container_id = storage_box.id
                        if not status_already_set:
                            asset.status = AssetStatus.IN_STORAGE
                        
                        # Only mark as modified if we actually changed something OR sync changed it
                        if (asset.container_id != old_container_id or asset.status != old_status):
                            asset_was_modified = True
                            assigned_count += 1
                    else:
                        errors.append(f"Asset {asset.asset_tag} (ID: {asset.id}): Could not create/find storage box")
                        skipped_count += 1
                else:
                    errors.append(f"Asset {asset.asset_tag} (ID: {asset.id}): Not a cable or auto_create_box is False")
                    skipped_count += 1
            
            # Log the update if container_id or status actually changed
            # Only log if there was a real change (not just a refresh after sync_storage_box_for_cable)
            if asset_was_modified:
                # Check if values actually changed from what we captured
                db.flush()  # Flush any pending changes
                db.refresh(asset)  # Refresh to get latest committed values
                
                # Only log if there was an actual change
                container_changed = asset.container_id != old_container_id
                status_changed = asset.status != old_status
                
                if container_changed or status_changed:
                    try:
                        log_update(
                            db=db,
                            instance=asset,
                            old_values=old_values,
                            user_id=current_user.id,
                            username=current_user.username,
                            tenant_id=current_user.tenant_id,
                            ip_address=request.client.host if request and request.client else None,
                            user_agent=request.headers.get("user-agent") if request else None,
                            notes=f"Bulk assigned to storage box (container_id: {asset.container_id})"
                        )
                    except Exception as e:
                        # Don't fail the request if audit logging fails
                        import logging
                        logging.getLogger(__name__).error(f"Failed to log bulk assign update for asset {asset.id}: {e}")
                    
        except Exception as e:
            errors.append(f"Asset {asset.asset_tag} (ID: {asset.id}): {str(e)}")
            skipped_count += 1
    
    db.commit()
    
    result = {
        "assigned_count": assigned_count,
        "skipped_count": skipped_count,
        "requested_count": len(asset_ids),
        "message": f"Assigned {assigned_count} asset(s) to storage box"
    }
    
    if errors:
        result["errors"] = errors[:10]  # Limit to first 10 errors
        if len(errors) > 10:
            result["error_message"] = f"({len(errors) - 10} more errors not shown)"
    
    return result


@router.post("/{asset_id}/photos")
async def upload_asset_photo(
    asset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload photo for asset"""
    # Capture old values (photo_urls changes)
    from app.core.tenant_query import apply_tenant_filter
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    # Apply tenant filter to be safe/consistent
    asset = apply_tenant_filter(db.query(Asset).filter(Asset.id == asset_id), Asset).first()
    old_values = get_model_dict(asset) if asset else None

    service = AssetService(db)
    result = service.upload_photo(asset_id, file)
    
    # Log update
    if asset:
        db.refresh(asset) # Ensure we have latest
        try:
            log_update(
                db=db,
                instance=asset,
                old_values=old_values,
                user_id=current_user.id,
                username=current_user.username,
                tenant_id=current_user.tenant_id,
                notes="Photo uploaded"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to log photo upload: {e}")
            
    return result


@router.post("/{asset_id}/deploy")
async def deploy_asset(
    asset_id: int,
    rack_id: int,
    u_position_start: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deploy asset to rack location"""
    # Capture old values
    from app.core.tenant_query import apply_tenant_filter
    asset = apply_tenant_filter(db.query(Asset).filter(Asset.id == asset_id), Asset).first()
    old_values = get_model_dict(asset) if asset else None
    
    service = AssetService(db)
    result = service.deploy_asset(asset_id, rack_id, u_position_start)
    
    # Log update
    if asset:
        db.refresh(asset)
        try:
            log_update(
                db=db,
                instance=asset,
                old_values=old_values,
                user_id=current_user.id,
                username=current_user.username,
                tenant_id=current_user.tenant_id,
                notes=f"Deployed to Rack {rack_id} U{u_position_start}"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to log deployment: {e}")
            
    return result


@router.post("/{asset_id}/decommission")
async def decommission_asset(
    asset_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Decommission an asset"""
    # Capture old values
    from app.core.tenant_query import apply_tenant_filter
    asset = apply_tenant_filter(db.query(Asset).filter(Asset.id == asset_id), Asset).first()
    old_values = get_model_dict(asset) if asset else None
    
    service = AssetService(db)
    result = service.decommission_asset(asset_id, reason)
    
    # Log update
    if asset:
        db.refresh(asset)
        try:
            log_update(
                db=db,
                instance=asset,
                old_values=old_values,
                user_id=current_user.id,
                username=current_user.username,
                tenant_id=current_user.tenant_id,
                notes=f"Decommissioned: {reason or 'No reason provided'}"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to log decommission: {e}")
            
    return result


@router.get("/lifecycle/{asset_id}/events")
async def get_lifecycle_events(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all lifecycle events for an asset"""
    from app.core.tenant_query import apply_tenant_filter
    
    # First verify the asset exists and belongs to tenant
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get events for this asset (events are also tenant-scoped)
    query = db.query(AssetLifecycleEvent).filter(
        AssetLifecycleEvent.asset_id == asset_id
    )
    query = apply_tenant_filter(query, AssetLifecycleEvent)
    events = query.order_by(AssetLifecycleEvent.event_timestamp.desc()).all()

    return events


@router.get("/warnings/eol", response_model=List[EOLWarningResponse])
async def get_eol_warnings(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get assets approaching end-of-life within specified days"""
    from app.core.tenant_query import apply_tenant_filter
    
    cutoff_date = datetime.utcnow() + timedelta(days=days)

    query = db.query(Asset).filter(
        Asset.eol_date.isnot(None),
        Asset.eol_date <= cutoff_date,
        Asset.eol_date >= datetime.utcnow(),
        Asset.status.in_([AssetStatus.ACTIVE, AssetStatus.DEPLOYED])
    )
    query = apply_tenant_filter(query, Asset)
    assets = query.order_by(Asset.eol_date).all()

    return [
        {
            "asset": asset,
            "eol_date": asset.eol_date,
            "days_remaining": (asset.eol_date - datetime.utcnow()).days
        }
        for asset in assets
    ]


@router.get("/warnings/warranty")
async def get_warranty_warnings(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get assets with expiring warranties"""
    from app.core.tenant_query import apply_tenant_filter
    
    cutoff_date = datetime.utcnow() + timedelta(days=days)

    query = db.query(Asset).filter(
        Asset.warranty_end_date.isnot(None),
        Asset.warranty_end_date <= cutoff_date,
        Asset.warranty_end_date >= datetime.utcnow(),
        Asset.status.in_([AssetStatus.ACTIVE, AssetStatus.DEPLOYED])
    )
    query = apply_tenant_filter(query, Asset)
    assets = query.order_by(Asset.warranty_end_date).all()

    return [
        {
            "asset": asset,
            "warranty_end_date": asset.warranty_end_date,
            "days_remaining": (asset.warranty_end_date - datetime.utcnow()).days
        }
        for asset in assets
    ]


@router.post("/{asset_id}/barcode/scan")
async def scan_barcode(
    asset_id: int,
    barcode_data: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Associate barcode scan with asset"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.barcode_data = barcode_data
    asset.updated_at = datetime.utcnow()
    
    # Capture old values if possible (or just log the change)
    # Since we didn't capture old_values before, we'll let audit service handle it or just log current state
    
    db.commit()
    db.refresh(asset)

    # Log the update
    try:
        log_update(
            db=db,
            instance=asset,
            user_id=current_user.id,
            username=current_user.username,
            tenant_id=current_user.tenant_id,
            notes=f"Barcode scanned: {barcode_data}"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log barcode scan: {e}")

    return {"message": "Barcode scanned successfully", "asset": asset}


@router.post("/{asset_id}/clone")
async def clone_asset(
    asset_id: int,
    quantity: int = Body(1, ge=1, le=100, embed=True, description="Number of clones to create"),
    prefix: Optional[str] = Body(None, embed=True, description="Asset tag prefix (optional)"),
    new_status: Optional[str] = Body(None, embed=True, description="Status for cloned assets (optional)"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)
):
    """
    Clone an existing asset to create one or more duplicates.
    
    Copies all fields except:
    - id (auto-generated)
    - asset_tag (generated new with optional prefix)
    - serial_number (generated new)
    - created_at, updated_at (auto-set)
    - rack position (cleared for clones)
    
    Useful for:
    - Creating multiple identical servers/switches
    - Populating inventory after receiving bulk shipments
    """
    from app.core.tenant_query import apply_tenant_filter
    import uuid
    
    # Get source asset
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    source_asset = query.first()
    
    if not source_asset:
        raise HTTPException(status_code=404, detail="Source asset not found")
    
    # Fields to NOT copy (will be generated or cleared)
    exclude_fields = {
        'id', 'asset_tag', 'serial_number', 'original_serial_number',
        'created_at', 'updated_at', 'tenant_id',
        # Clear location-specific fields for clones
        'rack_position_start', 'rack_position_end', 'rack_id',
        # Clear unique network identifiers
        'hostname', 'primary_ip', 'management_ip', 'mac_address'
    }
    
    created_assets = []
    
    for i in range(quantity):
        # Generate new asset tag
        if prefix:
            new_tag = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        else:
            # Use source tag with CLONE suffix
            new_tag = f"{source_asset.asset_tag}-CLONE-{i+1}"
        
        # Generate new serial number
        new_serial = f"CLN-{uuid.uuid4().hex[:12].upper()}"
        
        # Build new asset data from source
        clone_data = {}
        for column in Asset.__table__.columns:
            if column.name not in exclude_fields:
                clone_data[column.name] = getattr(source_asset, column.name)
        
        # Set generated fields
        clone_data['asset_tag'] = new_tag
        clone_data['serial_number'] = new_serial
        
        # Override status if specified
        if new_status:
            try:
                clone_data['status'] = AssetStatus(new_status.lower())
            except ValueError:
                pass  # Keep original status if invalid
        
        # Create the clone
        clone = Asset(**clone_data)
        db.add(clone)
        db.flush()  # Get the ID
        
        created_assets.append(clone)
        
        # Log the creation
        try:
            ip_address = request.client.host if request and request.client else None
            user_agent = request.headers.get("user-agent") if request else None
            log_create(
                db=db,
                instance=clone,
                user_id=current_user.id,
                username=current_user.username,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to log clone creation: {e}")
    
    db.commit()
    
    return {
        "success": True,
        "source_asset_id": asset_id,
        "source_asset_tag": source_asset.asset_tag,
        "cloned_count": len(created_assets),
        "created_asset_ids": [a.id for a in created_assets],
        "created_asset_tags": [a.asset_tag for a in created_assets],
        "message": f"Successfully cloned {len(created_assets)} asset(s) from {source_asset.asset_tag}"
    }

