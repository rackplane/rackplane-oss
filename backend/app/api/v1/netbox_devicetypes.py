"""
NetBox Device Type Library API Endpoints

Provides access to the NetBox Community devicetype-library for auto-populating
rack item specifications when creating assets.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
import re
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.tenant import get_current_tenant_id
from app.models.user import User
from app.models.vendor_sku import VendorSKU
from app.services.devicetype_service import DeviceTypeService
from app.services.devicetype_mapper import DeviceTypeMapper

router = APIRouter()
logger = logging.getLogger(__name__)


def _sanitize_error_for_client(error: Exception, context: str) -> str:
    """
    Sanitize error messages before returning to clients.
    
    Logs the full error for debugging but returns a generic message
    to avoid leaking internal details (paths, stack traces, etc.)
    
    Args:
        error: The exception that occurred
        context: A short description of what operation failed
        
    Returns:
        A sanitized error message safe for client consumption
    """
    error_str = str(error).lower()
    
    # Map known error types to user-friendly messages
    if "rate limit" in error_str:
        return str(error)  # Rate limit messages are safe to expose
    elif "not found" in error_str:
        return f"{context}: resource not found"
    elif "connection" in error_str or "timeout" in error_str:
        return f"{context}: unable to connect to GitHub"
    else:
        # Log full error for debugging, return generic message
        logger.error(f"{context}: {error}")
        return f"{context}: an unexpected error occurred"


# Pydantic models for request/response
class ManufacturerListResponse(BaseModel):
    """Response for manufacturer list."""
    manufacturers: List[str]
    total: int


class DeviceTypeSummary(BaseModel):
    """Summary of a device type without full YAML data."""
    slug: str
    name: str
    manufacturer: str


class DeviceTypeListResponse(BaseModel):
    """Response for device type list."""
    devices: List[DeviceTypeSummary]
    total: int
    manufacturer: str


class DeviceTypeImportRequest(BaseModel):
    """Request to import a device type to VendorSKU."""
    manufacturer: str
    slug: str

    @field_validator('manufacturer', 'slug')
    @classmethod
    def validate_slug_format(cls, v: str) -> str:
        """Validate manufacturer and slug contain only safe characters.
        
        Security: Prevents path traversal attacks by rejecting:
        - Dots (can be used for ..), backslashes, URL-encoded sequences
        - Only allows alphanumeric, hyphens, and underscores
        """
        # Reject path traversal attempts and URL-encoded sequences
        if '..' in v or '/' in v or '\\' in v or '%' in v:
            raise ValueError('Cannot contain path traversal sequences (/, \\, .., or %)')
        # Allow only safe characters (no dots to prevent hidden file/path traversal)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Must contain only alphanumeric characters, hyphens, and underscores')
        if v.startswith('-') or v.startswith('_'):
            raise ValueError('Cannot start with hyphen or underscore')
        return v


class DeviceTypeImportResponse(BaseModel):
    """Response after importing a device type."""
    success: bool
    message: str
    sku_id: Optional[int] = None
    sku: Optional[dict] = None


class DeviceTypeDetailResponse(BaseModel):
    """Detailed device type information."""
    manufacturer: str
    slug: str
    model: str
    u_height: Optional[float]
    weight: Optional[float]
    is_full_depth: Optional[bool]
    specifications: dict
    asset_type: str


@router.get("/manufacturers", response_model=ManufacturerListResponse)
async def list_manufacturers(
    current_user: User = Depends(get_current_active_user),
    use_cache: bool = Query(True, description="Use cached data")
):
    """
    List all available manufacturers from NetBox devicetype-library.

    Returns a list of manufacturer names that have device types available
    in the NetBox community library.
    """
    try:
        service = DeviceTypeService()
        manufacturers = service.list_manufacturers(use_cache=use_cache)

        return ManufacturerListResponse(
            manufacturers=manufacturers,
            total=len(manufacturers)
        )

    except Exception as e:
        if "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_sanitize_error_for_client(e, "Failed to fetch manufacturers")
        )


@router.get("/manufacturers/{manufacturer}/devices", response_model=DeviceTypeListResponse)
async def list_device_types(
    manufacturer: str,
    search: Optional[str] = Query(None, description="Search device models"),
    limit: int = Query(100, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_active_user),
    use_cache: bool = Query(True, description="Use cached data")
):
    """
    List all device types for a specific manufacturer.

    Returns device type slugs and names for the specified manufacturer.
    Supports search and pagination.
    """
    try:
        service = DeviceTypeService()
        devices = service.list_device_types(manufacturer, use_cache=use_cache)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            devices = [
                d for d in devices
                if search_lower in d['slug'].lower() or search_lower in d['name'].lower()
            ]

        # Total count before pagination
        total = len(devices)

        # Apply pagination
        devices = devices[offset:offset + limit]

        # Convert to response format
        device_summaries = [
            DeviceTypeSummary(
                slug=d['slug'],
                name=d['name'],
                manufacturer=manufacturer
            )
            for d in devices
        ]

        return DeviceTypeListResponse(
            devices=device_summaries,
            total=total,
            manufacturer=manufacturer
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "rate limit" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        # Use 404 only for known not-found cases, 500 for unexpected errors
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_sanitize_error_for_client(e, f"Manufacturer '{manufacturer}'")
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_sanitize_error_for_client(e, f"Failed to fetch devices for '{manufacturer}'")
        )


@router.get("/manufacturers/{manufacturer}/devices/{slug}", response_model=DeviceTypeDetailResponse)
async def get_device_type_details(
    manufacturer: str,
    slug: str,
    current_user: User = Depends(get_current_active_user),
    use_cache: bool = Query(True, description="Use cached data")
):
    """
    Get detailed information about a specific device type.

    Returns the full device type specification including dimensions,
    interfaces, power requirements, and other specifications.
    """
    try:
        service = DeviceTypeService()
        device_type = service.fetch_device_type(manufacturer, slug, use_cache=use_cache)

        # Validate device type
        is_valid, error_msg = DeviceTypeMapper.validate_device_type(device_type)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid device type data: {error_msg}"
            )

        # Infer asset type
        model = device_type.get('model', slug)
        asset_type = DeviceTypeMapper.infer_asset_type(device_type, model)

        # Build specifications using public method
        specifications = DeviceTypeMapper.build_specifications(device_type)

        return DeviceTypeDetailResponse(
            manufacturer=manufacturer,
            slug=slug,
            model=model,
            u_height=device_type.get('u_height'),
            weight=device_type.get('weight'),
            is_full_depth=device_type.get('is_full_depth'),
            specifications=specifications,
            asset_type=asset_type
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "rate limit" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        # Use 404 only for known not-found cases, 500 for unexpected errors
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_sanitize_error_for_client(e, f"Device type '{manufacturer}/{slug}'")
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_sanitize_error_for_client(e, f"Failed to fetch device type '{manufacturer}/{slug}'")
        )


@router.post("/import", response_model=DeviceTypeImportResponse)
async def import_device_type(
    request: DeviceTypeImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant_id)
):
    """
    Import a device type from NetBox library to VendorSKU catalog.

    This creates a VendorSKU entry that can be used to auto-populate
    asset fields when creating new assets.
    """
    try:
        # Fetch device type from NetBox library
        service = DeviceTypeService()
        device_type = service.fetch_device_type(
            request.manufacturer,
            request.slug,
            use_cache=True
        )

        # Validate device type
        is_valid, error_msg = DeviceTypeMapper.validate_device_type(device_type)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid device type data: {error_msg}"
            )

        # Transform to VendorSKU format
        vendor_sku_data = DeviceTypeMapper.to_vendor_sku(
            device_type,
            request.manufacturer
        )

        # Check if SKU already exists for this tenant
        existing_sku = db.query(VendorSKU).filter(
            VendorSKU.tenant_id == tenant_id,
            VendorSKU.vendor == vendor_sku_data['vendor'],
            VendorSKU.sku == vendor_sku_data['sku']
        ).first()

        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device type '{request.manufacturer}/{request.slug}' already imported"
            )

        # Create VendorSKU
        vendor_sku = VendorSKU(
            tenant_id=tenant_id,
            **vendor_sku_data,
            last_verified=datetime.now(timezone.utc)
        )

        db.add(vendor_sku)
        db.commit()
        db.refresh(vendor_sku)

        # Return success response
        return DeviceTypeImportResponse(
            success=True,
            message=f"Successfully imported {request.manufacturer} {device_type.get('model', request.slug)}",
            sku_id=vendor_sku.id,
            sku={
                'id': vendor_sku.id,
                'vendor': vendor_sku.vendor,
                'sku': vendor_sku.sku,
                'name': vendor_sku.name,
                'manufacturer': vendor_sku.manufacturer,
                'asset_type': vendor_sku.asset_type,
                'specifications': vendor_sku.specifications
            }
        )

    except HTTPException as e:
        logger.warning(f"Import failed for {request.manufacturer}/{request.slug}: {e.detail}")
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        if "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_sanitize_error_for_client(e, "Failed to import device type")
        )


@router.post("/search", response_model=List[DeviceTypeSummary])
async def search_device_types(
    query: str = Query(..., min_length=2, description="Search query"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    limit: int = Query(50, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for device types across all or specific manufacturer(s).

    Searches device model names and slugs for matches.
    """
    try:
        service = DeviceTypeService()
        results = service.search_device_types(
            query=query,
            manufacturer=manufacturer,
            limit=limit
        )

        # Convert to response format
        device_summaries = [
            DeviceTypeSummary(
                slug=r['slug'],
                name=r['name'],
                manufacturer=r['manufacturer']
            )
            for r in results
        ]

        return device_summaries

    except Exception as e:
        if "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_sanitize_error_for_client(e, "Search failed")
        )


@router.delete("/cache", status_code=status.HTTP_200_OK)
async def clear_cache(
    current_user: User = Depends(get_current_active_user)
):
    """
    Clear the NetBox devicetype-library cache.

    Use this to force refresh of manufacturer and device type lists.
    Requires authentication.
    
    Note: Returns 200 instead of 204 because we include a response body.
    HTTP 204 No Content should not have a body per HTTP specification.
    """
    try:
        service = DeviceTypeService()
        count = service.clear_cache()
        return {"message": f"Cleared {count} cache files"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_sanitize_error_for_client(e, "Failed to clear cache")
        )
