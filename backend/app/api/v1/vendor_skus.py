# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Vendor SKU API Endpoints
Manage vendor product catalogs for auto-populating asset fields
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant import get_current_tenant_id
from app.models.user import User
from app.models.vendor_sku import VendorSKU
from app.services.vendor_sku_service import VendorSKUService

router = APIRouter()


# Pydantic models for request/response
class VendorSKUCreate(BaseModel):
    vendor: str
    sku: str
    part_number: Optional[str] = None
    name: str
    manufacturer: Optional[str] = None
    asset_type: Optional[str] = None
    specifications: Optional[dict] = None
    price_usd: Optional[float] = None
    currency: Optional[str] = "USD"
    compatibility: Optional[dict] = None
    description: Optional[str] = None
    datasheet_url: Optional[str] = None
    vendor_url: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class VendorSKUUpdate(BaseModel):
    name: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer: Optional[str] = None
    asset_type: Optional[str] = None
    specifications: Optional[dict] = None
    price_usd: Optional[float] = None
    currency: Optional[str] = None
    compatibility: Optional[dict] = None
    description: Optional[str] = None
    datasheet_url: Optional[str] = None
    vendor_url: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None



class VendorSKUResponse(BaseModel):
    id: int
    vendor: str
    sku: str
    part_number: Optional[str]
    name: str
    manufacturer: Optional[str]
    asset_type: Optional[str]
    specifications: Optional[dict]
    price_usd: Optional[float]
    currency: str
    compatibility: Optional[dict]
    description: Optional[str]
    datasheet_url: Optional[str]
    vendor_url: Optional[str]
    image_url: Optional[str] = None
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[VendorSKUResponse])
async def list_vendor_skus(
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    search: Optional[str] = Query(None, description="Search in SKU, name, or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, le=500, description="Maximum results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    List local vendor SKUs with optional filtering
    
    Lists SKUs created by your organization, plus SKUs extracted from existing assets.
    For access to the Rackplane Global SKU Catalog, upgrade to a Pro or Enterprise subscription.
    """
    from app.models.asset import Asset
    from app.models.catalog_sku import CatalogSKU
    from app.models.tenant import Tenant
    from sqlalchemy import or_
    from datetime import datetime
    
    service = VendorSKUService(db)
    
    # Get tenant's vertical_pack to filter catalog SKUs
    tenant_obj = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant_vertical = tenant_obj.vertical_pack if tenant_obj else None
    
    # Get vendor SKUs from catalog
    if search:
        # Search tenant-specific VendorSKUs
        tenant_skus = service.search_skus(
            search_term=search,
            vendor=vendor,
            asset_type=asset_type,
            tenant_id=tenant_id,
            limit=limit
        )
        
        # Also search global CatalogSKUs with vertical filter
        search_pattern = f"%{search}%"
        global_query = db.query(CatalogSKU).filter(
            CatalogSKU.is_active == True,
            or_(
                CatalogSKU.sku.ilike(search_pattern),
                CatalogSKU.name.ilike(search_pattern),
                CatalogSKU.description.ilike(search_pattern)
            )
        )
        
        # Filter by tenant's vertical if set
        if tenant_vertical:
            global_query = global_query.filter(CatalogSKU.vertical == tenant_vertical)
        
        if vendor:
            global_query = global_query.filter(CatalogSKU.vendor.ilike(f"%{vendor}%"))
        if asset_type:
            global_query = global_query.filter(CatalogSKU.asset_type == asset_type)
            
        global_skus = global_query.limit(limit).all()
        
        # Convert and merge
        converted_global_skus = []
        for gsku in global_skus:
            class GlobalSKUWrapper:
                def __init__(self, sku_obj):
                    self.id = -sku_obj.id
                    self.vendor = sku_obj.vendor
                    self.sku = sku_obj.sku
                    self.part_number = sku_obj.part_number
                    self.name = sku_obj.name
                    self.manufacturer = sku_obj.manufacturer
                    self.asset_type = sku_obj.asset_type
                    self.specifications = sku_obj.specifications
                    self.price_usd = sku_obj.price_usd
                    self.currency = sku_obj.currency
                    self.compatibility = sku_obj.compatibility
                    self.description = sku_obj.description
                    self.datasheet_url = sku_obj.datasheet_url
                    self.vendor_url = sku_obj.vendor_url
                    self.is_active = sku_obj.is_active
                    self.notes = getattr(sku_obj, 'notes', None)
                    self.created_at = sku_obj.created_at
                    self.updated_at = sku_obj.updated_at
            converted_global_skus.append(GlobalSKUWrapper(gsku))
        
        # Merge and deduplicate
        all_skus = list(tenant_skus) + converted_global_skus
        seen_skus = {}
        catalog_skus = []
        for sku_obj in all_skus:
            key = (sku_obj.vendor.lower(), sku_obj.sku.lower())
            if key not in seen_skus:
                seen_skus[key] = True
                catalog_skus.append(sku_obj)
    else:
        # 1. Query Tenant-specific VendorSKUs
        query = db.query(VendorSKU).filter(VendorSKU.tenant_id == tenant_id)
        
        if vendor:
            query = query.filter(VendorSKU.vendor.ilike(f"%{vendor}%"))
        if asset_type:
            query = query.filter(VendorSKU.asset_type == asset_type)
        if is_active is not None:
            query = query.filter(VendorSKU.is_active == is_active)
        
        tenant_skus = query.order_by(VendorSKU.id).limit(limit).all()

        # No deduplication needed: Tenant SKUs only for the default list.
        # Global Catalog items are only shown when a search is performing.
        catalog_skus = tenant_skus
    
    # Get unique SKUs from assets (excluding those already in catalog)
    catalog_sku_values = {sku.sku.lower() for sku in catalog_skus}
    
    asset_query = db.query(Asset).filter(
        Asset.tenant_id == tenant_id,
        Asset.sku.isnot(None),
        Asset.sku != ''
    )
    
    # Apply filters to asset query
    if vendor:
        asset_query = asset_query.filter(Asset.manufacturer.ilike(f"%{vendor}%"))
    if asset_type:
        asset_query = asset_query.filter(Asset.asset_type == asset_type)
    if search:
        asset_query = asset_query.filter(
            (Asset.sku.ilike(f"%{search}%")) |
            (Asset.model.ilike(f"%{search}%")) |
            (Asset.asset_tag.ilike(f"%{search}%"))
        )
    
    # Get all assets with SKUs, then deduplicate by SKU in Python
    asset_skus_raw = asset_query.all()
    
    # Deduplicate by SKU (keep first occurrence of each SKU)
    seen_skus = set()
    unique_asset_skus = []
    for asset in asset_skus_raw:
        if asset.sku and asset.sku.lower() not in seen_skus:
            seen_skus.add(asset.sku.lower())
            unique_asset_skus.append(asset)
    
    # Convert asset SKUs to VendorSKUResponse format
    asset_skus = []
    for asset in unique_asset_skus:
        # Skip if this SKU is already in the catalog
        if asset.sku and asset.sku.lower() not in catalog_sku_values:
            # Create a simple object with the required attributes for VendorSKUResponse
            class AssetSKUObject:
                def __init__(self, asset):
                    self.id = -1  # Negative ID to indicate it's from assets, not catalog
                    self.vendor = asset.manufacturer or "Unknown"
                    self.sku = asset.sku
                    self.part_number = None  # Assets don't have part_number, only SKU
                    self.name = asset.model or asset.asset_tag or asset.sku
                    self.manufacturer = asset.manufacturer
                    self.asset_type = asset.asset_type
                    self.specifications = None
                    self.price_usd = None
                    self.currency = "USD"
                    self.compatibility = None
                    self.description = f"SKU from existing asset: {asset.asset_tag}"
                    self.datasheet_url = None
                    self.vendor_url = None
                    self.is_active = True
                    self.notes = f"Auto-extracted from asset {asset.asset_tag}"
                    self.created_at = getattr(asset, 'created_at', datetime.utcnow())
                    self.updated_at = getattr(asset, 'updated_at', datetime.utcnow())
            
            asset_sku_obj = AssetSKUObject(asset)
            asset_sku_response = VendorSKUResponse.model_validate(asset_sku_obj)
            asset_skus.append(asset_sku_response)
            catalog_sku_values.add(asset.sku.lower())  # Track to avoid duplicates
    
    # Combine catalog SKUs and asset SKUs
    all_skus = list(catalog_skus) + asset_skus
    
    # Apply limit to combined results
    return all_skus[:limit]


@router.get("/vendors", response_model=List[str])
async def list_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Get list of all vendors in your local catalog
    """
    service = VendorSKUService(db)
    return service.get_vendors(tenant_id=tenant_id)


@router.get("/lookup", response_model=Optional[VendorSKUResponse])
async def lookup_sku(
    sku: str = Query(..., description="SKU to lookup"),
    vendor: Optional[str] = Query(None, description="Optional vendor name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Look up a vendor SKU by SKU number
    
    **Premium Feature**: Requires 'sku_lookup' subscription.
    """
    service = VendorSKUService(db)
    vendor_sku = service.lookup_by_sku(sku, vendor=vendor, tenant_id=tenant_id)
    
    if not vendor_sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    return vendor_sku


@router.get("/match-from-text", response_model=Optional[VendorSKUResponse])
async def match_sku_from_text(
    text: str = Query(..., description="Text to search for SKU (e.g., from OCR)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Try to match a SKU from text (e.g., OCR output)
    
    **Premium Feature**: Requires 'sku_lookup' subscription.
    """
    service = VendorSKUService(db)
    vendor_sku = service.match_sku_from_text(text, tenant_id=tenant_id)
    
    if not vendor_sku:
        raise HTTPException(status_code=404, detail="No matching SKU found")
    
    return vendor_sku


@router.get("/asset-data", response_model=Optional[dict])
async def get_asset_data_from_sku(
    sku: str = Query(..., description="SKU to lookup"),
    vendor: Optional[str] = Query(None, description="Optional vendor name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Get asset field data from a vendor SKU (for auto-populating forms)
    
    **Premium Feature**: Requires 'sku_lookup' subscription.
    
    Checks:
    1. Local catalog (tenant's own SKUs)
    2. Global catalog (app.rackplane.com) if subscribed
    """
    service = VendorSKUService(db)
    
    # First check local catalog
    asset_data = service.get_asset_data_from_sku(sku, vendor=vendor, tenant_id=tenant_id)
    if asset_data:
        return asset_data
    
    # If not found locally, check global catalog (app.rackplane.com)
    try:
        from app.bridges.rackplane_services import RackPlaneServicesClient
    except ImportError:
        # OSS build - global catalog not available
        pass
    except HTTPException:
        client = RackPlaneServicesClient(db)
        
        if client.has_feature("sku_lookup"):
            global_sku = await client.lookup_sku_catalog(sku, vendor=vendor)
            if global_sku:
                # Convert global SKU format to asset data format
                vendor_sku_obj = VendorSKU(**global_sku, tenant_id=tenant_id)
                return vendor_sku_obj.to_asset_data()
    except HTTPException:
        # Central services API error - re-raise
        raise
    except Exception as e:
        # Log but don't fail - fall back to local-only
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to lookup SKU in global catalog: {e}")
    
    raise HTTPException(status_code=404, detail="SKU not found")


@router.post("/", response_model=VendorSKUResponse, status_code=201)
async def create_vendor_sku(
    sku_data: VendorSKUCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Create a new vendor SKU entry in your local catalog
    """
    # Check if SKU already exists for this vendor
    existing = db.query(VendorSKU).filter(
        VendorSKU.tenant_id == tenant_id,
        VendorSKU.vendor.ilike(sku_data.vendor),
        VendorSKU.sku.ilike(sku_data.sku)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SKU {sku_data.sku} already exists for vendor {sku_data.vendor}"
        )
    
    vendor_sku = VendorSKU(
        tenant_id=tenant_id,
        vendor=sku_data.vendor,
        sku=sku_data.sku,
        part_number=sku_data.part_number,
        name=sku_data.name,
        manufacturer=sku_data.manufacturer,
        asset_type=sku_data.asset_type,
        specifications=sku_data.specifications,
        price_usd=sku_data.price_usd,
        currency=sku_data.currency or "USD",
        compatibility=sku_data.compatibility,
        description=sku_data.description,
        datasheet_url=sku_data.datasheet_url,
        vendor_url=sku_data.vendor_url,
        image_url=sku_data.image_url,
        notes=sku_data.notes,
        is_active=True
    )
    
    db.add(vendor_sku)
    db.commit()
    db.refresh(vendor_sku)
    
    return vendor_sku


@router.get("/{sku_id}", response_model=VendorSKUResponse)
async def get_vendor_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Get a specific vendor SKU by ID from your local catalog
    """
    vendor_sku = db.query(VendorSKU).filter(
        VendorSKU.id == sku_id,
        VendorSKU.tenant_id == tenant_id
    ).first()
    
    if not vendor_sku:
        raise HTTPException(status_code=404, detail="Vendor SKU not found")
    
    return vendor_sku


@router.put("/{sku_id}", response_model=VendorSKUResponse)
async def update_vendor_sku(
    sku_id: int,
    sku_data: VendorSKUUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Update a vendor SKU in your local catalog
    """
    vendor_sku = db.query(VendorSKU).filter(
        VendorSKU.id == sku_id,
        VendorSKU.tenant_id == tenant_id
    ).first()
    
    if not vendor_sku:
        raise HTTPException(status_code=404, detail="Vendor SKU not found")
    
    # Update fields
    update_data = sku_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor_sku, field, value)
    
    if sku_data.image_url is not None:
        vendor_sku.image_url = sku_data.image_url
    if sku_data.price_usd is not None:
        vendor_sku.price_updated_at = datetime.utcnow()
    
    vendor_sku.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(vendor_sku)
    
    return vendor_sku


@router.delete("/{sku_id}", status_code=204)
async def delete_vendor_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Delete a vendor SKU from your local catalog (soft delete by setting is_active=False)
    """
    vendor_sku = db.query(VendorSKU).filter(
        VendorSKU.id == sku_id,
        VendorSKU.tenant_id == tenant_id
    ).first()
    
    if not vendor_sku:
        raise HTTPException(status_code=404, detail="Vendor SKU not found")
    
    vendor_sku.is_active = False
    vendor_sku.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None

