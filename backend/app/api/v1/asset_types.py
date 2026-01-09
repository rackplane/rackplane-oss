# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Asset Types API Endpoints
Dynamic asset type management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.asset_type import AssetTypeModel
from app.models.user import User
from app.schemas.asset_type import AssetTypeCreate, AssetTypeUpdate, AssetTypeResponse
from app.core.tenant_query import apply_tenant_filter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[AssetTypeResponse])
async def list_asset_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all asset types for the current tenant"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AssetTypeModel)
    query = apply_tenant_filter(query, AssetTypeModel)
    
    if not include_inactive:
        query = query.filter(AssetTypeModel.is_active.is_(True))
    
    asset_types = query.order_by(AssetTypeModel.display_name).all()
    return asset_types


@router.get("/{asset_type_id}", response_model=AssetTypeResponse)
async def get_asset_type(
    asset_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific asset type"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AssetTypeModel).filter(AssetTypeModel.id == asset_type_id)
    query = apply_tenant_filter(query, AssetTypeModel)
    asset_type = query.first()
    if not asset_type:
        raise HTTPException(
            status_code=404, detail="Asset type not found"
        )
    return asset_type


@router.post("/", response_model=AssetTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_type(
    asset_type: AssetTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new asset type"""
    from app.core.tenant_query import apply_tenant_filter
    
    # Check if name already exists within tenant scope
    query = db.query(AssetTypeModel).filter(AssetTypeModel.name == asset_type.name.lower())
    query = apply_tenant_filter(query, AssetTypeModel)
    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Asset type with name '{asset_type.name}' already exists"
        )

    # Create new asset type
    db_asset_type = AssetTypeModel(
        name=asset_type.name.lower().replace(" ", "_"),
        display_name=asset_type.display_name,
        description=asset_type.description,
        icon=asset_type.icon,
        color=asset_type.color,
        is_active=True,
        is_system=False
    )

    db.add(db_asset_type)
    db.commit()
    db.refresh(db_asset_type)

    return db_asset_type


@router.put("/{asset_type_id}", response_model=AssetTypeResponse)
async def update_asset_type(
    asset_type_id: int,
    asset_type_update: AssetTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an asset type"""
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AssetTypeModel).filter(AssetTypeModel.id == asset_type_id)
    query = apply_tenant_filter(query, AssetTypeModel)
    asset_type = query.first()
    if not asset_type:
        raise HTTPException(status_code=404, detail="Asset type not found")
    
    if asset_type.is_system:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify system asset types"
        )
    
    # Update fields
    if asset_type_update.display_name is not None:
        asset_type.display_name = asset_type_update.display_name
    if asset_type_update.description is not None:
        asset_type.description = asset_type_update.description
    if asset_type_update.icon is not None:
        asset_type.icon = asset_type_update.icon
    if asset_type_update.color is not None:
        asset_type.color = asset_type_update.color
    if asset_type_update.is_active is not None:
        asset_type.is_active = asset_type_update.is_active
    
    db.commit()
    db.refresh(asset_type)
    return asset_type


@router.delete("/{asset_type_id}", status_code=status.HTTP_200_OK)
async def delete_asset_type(
    asset_type_id: int,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
    reassign_assets_to: Optional[int] = Query(None, description="Asset type ID to reassign assets to"),
    force_delete_system: bool = Query(False, description="Allow deletion of system types (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an asset type.
    
    Options:
    - hard_delete: Permanently delete from database (default: soft delete by setting is_active=False)
    - reassign_assets_to: Reassign assets using this type to another type
    - force_delete_system: Allow deletion of system types (requires admin role)
    """
    from app.core.tenant_query import apply_tenant_filter
    from app.models.asset import Asset
    from app.models.user_role import UserRole
    
    query = db.query(AssetTypeModel).filter(AssetTypeModel.id == asset_type_id)
    query = apply_tenant_filter(query, AssetTypeModel)
    asset_type = query.first()
    if not asset_type:
        raise HTTPException(status_code=404, detail="Asset type not found")
    
    # Check system type protection
    if asset_type.is_system and not force_delete_system:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete system asset types. Use force_delete_system=true to override (admin only)."
        )
    
    # Require admin role for system type deletion
    if asset_type.is_system and force_delete_system:
        if current_user.effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
            raise HTTPException(
                status_code=403,
                detail="Only admins can delete system asset types"
            )
    
    # Check if any assets are using this type
    asset_query = db.query(Asset).filter(Asset.asset_type == asset_type.name)
    asset_query = apply_tenant_filter(asset_query, Asset)
    assets_using_type = asset_query.count()
    
    reassigned_count = 0
    if assets_using_type > 0:
        if reassign_assets_to:
            # Verify target asset type exists and is in same tenant
            target_type_query = db.query(AssetTypeModel).filter(AssetTypeModel.id == reassign_assets_to)
            target_type_query = apply_tenant_filter(target_type_query, AssetTypeModel)
            target_type = target_type_query.first()
            
            if not target_type:
                raise HTTPException(
                    status_code=404,
                    detail=f"Target asset type {reassign_assets_to} not found"
                )
            
            if target_type.id == asset_type.id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot reassign assets to the same asset type"
                )
            
            # Reassign assets
            updated = asset_query.update(
                {'asset_type': target_type.name},
                synchronize_session=False
            )
            reassigned_count = updated
            logger.info(f"Reassigned {reassigned_count} assets from '{asset_type.name}' to '{target_type.name}'")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete asset type: {assets_using_type} asset(s) are using this type. "
                       f"Provide reassign_assets_to parameter to reassign assets to another type."
            )
    
    # Perform deletion
    if hard_delete:
        db.delete(asset_type)
        logger.info(f"Hard deleted asset type '{asset_type.name}' (ID: {asset_type_id})")
    else:
        asset_type.is_active = False
        logger.info(f"Soft deleted asset type '{asset_type.name}' (ID: {asset_type_id})")
    
    db.commit()
    
    return {
        "message": f"Asset type '{asset_type.display_name}' deleted successfully",
        "hard_delete": hard_delete,
        "assets_reassigned": reassigned_count,
        "assets_remaining": assets_using_type - reassigned_count
    }


@router.post("/cleanup-duplicates", response_model=dict)
async def cleanup_duplicate_asset_types(
    dry_run: bool = Query(True, description="If true, only report duplicates without deleting"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Find and optionally remove duplicate asset types.
    Duplicates are identified by case-insensitive name matching within the same tenant.
    """
    from app.core.tenant_query import apply_tenant_filter
    from app.models.asset import Asset
    
    # Get all asset types for current tenant
    query = db.query(AssetTypeModel)
    query = apply_tenant_filter(query, AssetTypeModel)
    all_types = query.all()
    
    # Group by lowercase name
    type_groups = {}
    for asset_type in all_types:
        key = asset_type.name.lower()
        if key not in type_groups:
            type_groups[key] = []
        type_groups[key].append(asset_type)
    
    # Find duplicates
    duplicates = []
    to_delete = []
    
    for key, types in type_groups.items():
        if len(types) > 1:
            # Sort by: keep system types, then by ID (oldest first)
            types.sort(key=lambda t: (not t.is_system, t.id))
            
            # Keep the first one, mark others for deletion
            keep = types[0]
            delete_candidates = types[1:]
            
            duplicates.append({
                'name': key,
                'keep': {
                    'id': keep.id,
                    'name': keep.name,
                    'display_name': keep.display_name,
                    'is_system': keep.is_system
                },
                'duplicates': [
                    {
                        'id': t.id,
                        'name': t.name,
                        'display_name': t.display_name,
                        'is_system': t.is_system,
                        'asset_count': db.query(Asset).filter(Asset.asset_type == t.name).count()
                    }
                    for t in delete_candidates
                ]
            })
            
            # Check if any duplicates have assets using them
            for dup in delete_candidates:
                asset_query = db.query(Asset).filter(Asset.asset_type == dup.name)
                asset_query = apply_tenant_filter(asset_query, Asset)
                asset_count = asset_query.count()
                if asset_count == 0:
                    to_delete.append(dup)
    
    if dry_run:
        return {
            'dry_run': True,
            'duplicates_found': len(duplicates),
            'can_delete': len(to_delete),
            'need_migration': len(duplicates) - len(to_delete),
            'duplicates': duplicates
        }
    else:
        # Actually delete duplicates that have no assets
        deleted_count = 0
        for dup in to_delete:
            db.delete(dup)
            deleted_count += 1
        
        db.commit()
        
        return {
            'dry_run': False,
            'deleted_count': deleted_count,
            'duplicates_found': len(duplicates),
            'remaining_duplicates': len(duplicates) - deleted_count
        }
