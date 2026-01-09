# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
White-Label Configuration API Endpoints
Manage branding, terminology, and vertical pack settings for tenants

These endpoints allow tenants to customize their white-label experience
including branding (logo, colors), terminology (Asset -> Supply), and
vertical-specific features (expiration tracking, par levels).
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.user_role import UserRole
from app.services.terminology_service import terminology_service, TerminologyService
from app.schemas.whitelabel import (
    BrandingConfig,
    BrandingConfigUpdate,
    Terminology,
    TerminologyUpdate,
    VerticalFeatures,
    VerticalFeaturesUpdate,
    TenantConfigResponse,
    VerticalPreset,
    VerticalPresetsResponse,
    ApplyPresetRequest
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Define presets in a single source of truth
VERTICAL_PRESETS = {
    "datacenter": {
        "display_name": "Datacenter",
        "description": "Data center infrastructure and IT equipment management",
        "terminology": terminology_service.DATACENTER_PRESET,
        "default_features": {
            "expiration_tracking": False,
            "par_levels": False,
            "lot_tracking": False,
            "department_attribution": False,
            "show_power_watts": True,
            "show_warranty_info": True,
            "show_hostname": True,
            "show_rack_position": True,
            "show_datacenter_location": True,
            "show_sku_lookup": True,
            "show_loan_tracking": True
        }
    },
    "healthcare": {
        "display_name": "Healthcare",
        "description": "Hospital supply room and medical equipment management",
        "terminology": terminology_service.HEALTHCARE_PRESET,
        "default_features": {
            "expiration_tracking": True,
            "par_levels": True,
            "lot_tracking": True,
            "department_attribution": True,
            "show_power_watts": False,
            "show_warranty_info": False,
            "show_hostname": False,
            "show_rack_position": False,
            "show_datacenter_location": False,
            "show_sku_lookup": True,
            "show_loan_tracking": True
        }
    },
    "warehouse": {
        "display_name": "Warehouse",
        "description": "General warehouse and inventory management",
        "terminology": terminology_service.WAREHOUSE_PRESET,
        "default_features": {
            "expiration_tracking": False,
            "par_levels": True,
            "lot_tracking": False,
            "department_attribution": False,
            "show_power_watts": False,
            "show_warranty_info": True,
            "show_hostname": False,
            "show_rack_position": False,
            "show_datacenter_location": False,
            "show_sku_lookup": True,
            "show_loan_tracking": True
        }
    }
}


# =============================================================================
# Tenant Configuration Endpoints
# =============================================================================

@router.get("/config", response_model=TenantConfigResponse)
def get_tenant_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get complete white-label configuration for the current tenant.
    
    Returns branding, terminology, and vertical feature settings.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Build response with defaults for missing values
    branding = tenant.branding_config or {}
    terms = terminology_service.get_terminology(tenant.id, db)
    features = tenant.vertical_features or {}
    
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "vertical_pack": tenant.vertical_pack or "datacenter",
        "branding": BrandingConfig(
            name=branding.get("name"),
            logo_url=branding.get("logo_url"),
            favicon_url=branding.get("favicon_url"),
            primary_color=branding.get("primary_color", "#6366f1"),
            secondary_color=branding.get("secondary_color", "#4f46e5"),
            accent_color=branding.get("accent_color", "#818cf8"),
            font_family=branding.get("font_family", "Inter"),
            custom_domain=branding.get("custom_domain"),
            email_from_name=branding.get("email_from_name"),
            email_from_address=branding.get("email_from_address")
        ),
        "terminology": Terminology(**terms),
        "vertical_features": VerticalFeatures(
            expiration_tracking=features.get("expiration_tracking", False),
            par_levels=features.get("par_levels", False),
            lot_tracking=features.get("lot_tracking", False),
            department_attribution=features.get("department_attribution", False),
            show_power_watts=features.get("show_power_watts", True),
            show_warranty_info=features.get("show_warranty_info", True),
            show_hostname=features.get("show_hostname", True),
            show_rack_position=features.get("show_rack_position", True),
            show_datacenter_location=features.get("show_datacenter_location", True),
            show_sku_lookup=features.get("show_sku_lookup", True),
            show_loan_tracking=features.get("show_loan_tracking", True)
        )
    }


# =============================================================================
# Branding Endpoints
# =============================================================================

@router.get("/branding", response_model=BrandingConfig)
def get_branding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get branding configuration for the current tenant.
    
    Returns logo, colors, fonts, and custom domain settings.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    branding = tenant.branding_config or {}
    
    return BrandingConfig(
        name=branding.get("name"),
        logo_url=branding.get("logo_url"),
        favicon_url=branding.get("favicon_url"),
        primary_color=branding.get("primary_color", "#6366f1"),
        secondary_color=branding.get("secondary_color", "#4f46e5"),
        accent_color=branding.get("accent_color", "#818cf8"),
        font_family=branding.get("font_family", "Inter"),
        custom_domain=branding.get("custom_domain"),
        email_from_name=branding.get("email_from_name"),
        email_from_address=branding.get("email_from_address")
    )


@router.patch("/branding", response_model=BrandingConfig)
def update_branding(
    updates: BrandingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update branding configuration for the current tenant.
    
    Requires admin role. Only provided fields are updated.
    """
    # Check if user is admin
    if current_user.effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update branding"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get current branding or initialize
    branding = tenant.branding_config or {}
    
    # Update only provided fields
    update_dict = updates.model_dump(exclude_unset=True, mode='json')
    for key, value in update_dict.items():
        if value is not None:
            branding[key] = value
    
    tenant.branding_config = branding
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Updated branding for tenant {tenant.id}: {list(update_dict.keys())}")
    
    return get_branding(db, current_user)


# =============================================================================
# Terminology Endpoints
# =============================================================================

@router.get("/terminology", response_model=Terminology)
def get_terminology(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get terminology configuration for the current tenant.
    
    Returns all configurable terminology mappings merged with vertical preset.
    """
    terms = terminology_service.get_terminology(current_user.tenant_id, db)
    return Terminology(**terms)


@router.patch("/terminology", response_model=Terminology)
def update_terminology(
    updates: TerminologyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update terminology for the current tenant.
    
    Requires admin role. Only provided fields are updated.
    """
    # Check if user is admin
    if current_user.effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update terminology"
        )
    
    update_dict = updates.to_dict()
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )
    
    updated_terms = terminology_service.update_tenant_terminology(
        current_user.tenant_id,
        update_dict,
        db
    )
    
    return Terminology(**updated_terms)


# =============================================================================
# Vertical Pack Endpoints
# =============================================================================

@router.get("/vertical-features", response_model=VerticalFeatures)
def get_vertical_features(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get vertical-specific feature flags for the current tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    features = tenant.vertical_features or {}
    
    return VerticalFeatures(
        expiration_tracking=features.get("expiration_tracking", False),
        par_levels=features.get("par_levels", False),
        lot_tracking=features.get("lot_tracking", False),
        department_attribution=features.get("department_attribution", False),
        show_power_watts=features.get("show_power_watts", True),
        show_warranty_info=features.get("show_warranty_info", True),
        show_hostname=features.get("show_hostname", True),
        show_rack_position=features.get("show_rack_position", True),
        show_datacenter_location=features.get("show_datacenter_location", True),
        show_sku_lookup=features.get("show_sku_lookup", True),
        show_loan_tracking=features.get("show_loan_tracking", True)
    )


@router.patch("/vertical-features", response_model=VerticalFeatures)
def update_vertical_features(
    updates: VerticalFeaturesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update vertical-specific feature flags for the current tenant.
    
    Requires admin role.
    """
    # Check if user is admin
    if current_user.effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update vertical features"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get current features or initialize
    features = tenant.vertical_features or {}
    
    # Update only provided fields
    # Update only provided fields using Pydantic's exclude_unset if desired, 
    # but here we follow the existing pattern of updating matching keys
    update_dict = updates.model_dump(exclude_unset=True, mode='json')
    
    # Create a NEW dict merging existing features with updates
    # This ensures SQLAlchemy detects the change to the JSONB column
    tenant.vertical_features = {**features, **update_dict}
    
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Updated vertical features for tenant {tenant.id}: {list(update_dict.keys())}")
    
    return get_vertical_features(db, current_user)


# =============================================================================
# Vertical Presets Endpoints
# =============================================================================

@router.get("/presets", response_model=VerticalPresetsResponse)
def list_vertical_presets(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all available vertical presets.
    
    Returns datacenter, healthcare, and warehouse presets with their
    default terminology and feature configurations.
    """
    presets = []
    
    for name, data in VERTICAL_PRESETS.items():
        presets.append(VerticalPreset(
            name=name,
            display_name=data["display_name"],
            description=data["description"],
            terminology=data["terminology"].copy(),
            default_features=data["default_features"]
        ))
    
    return VerticalPresetsResponse(presets=presets)


@router.get("/presets/{vertical}", response_model=VerticalPreset)
def get_vertical_preset(
    vertical: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific vertical preset by name.
    """
    if vertical not in VERTICAL_PRESETS:
        raise HTTPException(
            status_code=404,
            detail=f"Vertical preset '{vertical}' not found. "
                   f"Options: {list(VERTICAL_PRESETS.keys())}"
        )
    
    data = VERTICAL_PRESETS[vertical]
    return VerticalPreset(
        name=vertical,
        display_name=data["display_name"],
        description=data["description"],
        terminology=data["terminology"].copy(),
        default_features=data["default_features"]
    )


@router.post("/presets/apply", response_model=TenantConfigResponse)
def apply_vertical_preset(
    request: ApplyPresetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Apply a vertical preset to the current tenant.
    
    This updates the tenant's vertical pack and optionally resets
    terminology to preset defaults.
    
    Requires admin role.
    """
    # Check if user is admin
    if current_user.effective_role not in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can apply vertical presets"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Apply the preset
    try:
        terminology_service.apply_vertical_preset(
            tenant.id,
            request.vertical,
            db,
            override_custom=request.override_custom
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Also update vertical features based on preset
    preset_config = VERTICAL_PRESETS.get(request.vertical, {})
    preset_features = preset_config.get("default_features", {})
    
    if request.override_custom:
        tenant.vertical_features = preset_features
        db.commit()
        db.refresh(tenant)
    
    # Automatically seed vertical-specific asset types when vertical changes
    try:
        from app.services.asset_type_seed_service import seed_vertical_asset_types
        seed_result = seed_vertical_asset_types(tenant.id, db)
        logger.info(f"Seeded {seed_result.get('created', 0)} asset types for tenant {tenant.id} after vertical change to '{request.vertical}'")
        
        # Optionally clean up asset types from the old vertical (if override_custom is True)
        if request.override_custom:
            try:
                from app.services.asset_type_seed_service import VERTICAL_ASSET_TYPES
                from app.models.asset_type import AssetTypeModel
                from app.models.asset import Asset
                
                # Get expected types for new vertical
                expected_types = {t['name'] for t in VERTICAL_ASSET_TYPES.get(request.vertical, [])}
                
                # Find asset types that don't belong to new vertical
                wrong_types = db.query(AssetTypeModel).execution_options(skip_tenant_filter=True).filter(
                    AssetTypeModel.tenant_id == tenant.id
                ).all()
                
                deleted_count = 0
                for asset_type in wrong_types:
                    if asset_type.name not in expected_types:
                        # Check if any assets are using it
                        asset_count = db.query(Asset).execution_options(skip_tenant_filter=True).filter(
                            Asset.tenant_id == tenant.id,
                            Asset.asset_type == asset_type.name
                        ).count()
                        
                        if asset_count == 0:
                            db.delete(asset_type)
                            deleted_count += 1
                            logger.info(f"Deleted asset type '{asset_type.name}' from previous vertical")
                
                if deleted_count > 0:
                    db.commit()
                    logger.info(f"Cleaned up {deleted_count} asset types from previous vertical for tenant {tenant.id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup old vertical asset types for tenant {tenant.id}: {e}")
                # Don't fail the entire operation if cleanup fails
    except Exception as e:
        logger.warning(f"Failed to seed asset types for tenant {tenant.id} after vertical change: {e}")
        # Don't fail the entire operation if asset type seeding fails
    
    logger.info(f"Applied vertical preset '{request.vertical}' to tenant {tenant.id}")
    
    # Return updated config
    return get_tenant_config(db, current_user)


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/terminology-keys")
def get_terminology_keys(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all supported terminology keys.
    
    Useful for building dynamic forms for terminology customization.
    """
    return {
        "keys": terminology_service.get_supported_keys(),
        "descriptions": {
            "item": "Singular term for a tracked item (e.g., Asset, Supply, Item)",
            "items": "Plural term for tracked items (e.g., Assets, Supplies, Items)",
            "location": "Term for top-level location (e.g., Datacenter, Facility)",
            "locations": "Plural term for locations",
            "bin": "Term for storage bin (e.g., Rack, Cabinet, Shelf)",
            "bins": "Plural term for storage bins",
            "check_out": "Action for taking out an item (e.g., Deploy, Dispense, Pick)",
            "check_in": "Action for returning an item (e.g., Return, Restock, Receive)",
            "category": "Term for item category (e.g., Asset Type, Supply Category)",
            "categories": "Plural term for categories",
            "lifecycle": "Term for item status (e.g., Status, Supply Status)",
            "storage": "Term for storage area (e.g., Storage, Supply Room, Zone)",
            "stock": "Term for inventory (e.g., Inventory, Stock)",
            "container": "Term for storage container (e.g., Storage Container, Bin)",
            "containers": "Plural term for containers"
        }
    }


@router.get("/display-name")
def get_display_name(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the display name for the white-labeled product.
    
    Returns the custom branding name or default "RackPlane".
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        return {"name": "RackPlane"}
    
    return {"name": tenant.get_display_name()}
