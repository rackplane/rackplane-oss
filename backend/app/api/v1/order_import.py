# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Generic Vendor Order Import API

Import orders from any supported vendor (PDF upload).
Auto-detects vendor and parses order to create assets.
"""

import io
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db, get_services_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.services.vendor_parsers.parser_registry import (
    parse_order,
    detect_vendor,
    extract_text_from_pdf,
    get_available_parsers
)
from app.services.vendor_parsers.base_parser import ParsedOrder, ParsedOrderItem

router = APIRouter()


# ================== Response Models ==================

class OrderImportPreview(BaseModel):
    """Preview of parsed order before asset creation."""
    success: bool
    vendor: Optional[str] = None
    order_number: Optional[str] = None
    order_date: Optional[str] = None
    customer: Optional[str] = None
    total: Optional[float] = None
    items: List[dict] = []
    item_count: int = 0
    asset_eligible_count: int = 0  # Items that can become assets (not services)
    items_needing_clarification: int = 0  # Items with ambiguous details
    message: str


class OrderImportResult(BaseModel):
    """Result of order import with asset creation."""
    success: bool
    order_number: Optional[str] = None
    vendor: Optional[str] = None
    items_parsed: int = 0
    assets_created: int = 0
    skipped_services: int = 0
    message: str
    created_asset_ids: List[int] = []


class ClarificationAnswer(BaseModel):
    """User-provided answer to a clarification question."""
    item_index: int  # Index of the item in the order
    field: str  # Field being clarified (e.g., "connector_type_end_a")
    value: str  # User's answer


# ================== Endpoints ==================

@router.get("/parsers", summary="List available vendor parsers")
def list_parsers():
    """List all available vendor order parsers."""
    return {
        "parsers": get_available_parsers(),
        "count": len(get_available_parsers())
    }


@router.post("/preview", response_model=OrderImportPreview, summary="Preview order import")
async def preview_order_import(
    file: UploadFile = File(..., description="Vendor order/invoice PDF"),
    vendor_hint: Optional[str] = Query(None, description="Vendor name hint if auto-detect fails"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Parse and preview an order without creating assets.
    
    1. Extracts text from uploaded PDF
    2. Auto-detects vendor (or uses hint)
    3. Parses order and returns preview
    
    Use this to verify parsing before calling /import.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read file content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Extract text from PDF
    try:
        text = extract_text_from_pdf(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from PDF")
    
    # Detect vendor
    detected_vendor = detect_vendor(text)
    if not detected_vendor and not vendor_hint:
        return OrderImportPreview(
            success=False,
            message=f"Could not auto-detect vendor. Available parsers: {', '.join(get_available_parsers())}. "
                    f"Use vendor_hint parameter to specify vendor."
        )
    
    # Parse order
    order = parse_order(text, vendor_hint=vendor_hint)
    if not order:
        return OrderImportPreview(
            success=False,
            vendor=detected_vendor or vendor_hint,
            message="Failed to parse order. Document format may not be supported."
        )
    
    # Count asset-eligible items (not services)
    asset_eligible = sum(1 for item in order.items if item.category != 'service')
    
    # Get a parser instance for clarification detection
    from app.services.vendor_parsers.base_parser import VendorOrderParser
    
    class ClarificationDetector(VendorOrderParser):
        vendor_name = "detector"
        def can_parse(self, text): return False
        def parse(self, text): return None
    
    detector = ClarificationDetector()
    
    # Format items for preview - include clarification questions
    preview_items = []
    items_needing_clarification = 0
    
    for idx, item in enumerate(order.items):
        # Detect if this item needs clarification
        clarifications = detector.detect_clarifications(item.description, item.category)
        needs_clarification = len(clarifications) > 0
        
        if needs_clarification:
            items_needing_clarification += 1
        
        preview_items.append({
            "index": idx,
            "description": item.description[:200],  # Increased for better context
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "extended_price": item.extended_price,
            "category": item.category,
            "manufacturer": item.manufacturer,
            "part_number": item.part_number,
            "is_asset": item.category != 'service',
            "needs_clarification": needs_clarification,
            "clarification_questions": [
                {
                    "field": q.field,
                    "question": q.question,
                    "options": q.options,
                    "default": q.default
                }
                for q in clarifications
            ] if clarifications else []
        })
    
    # Build message
    message = f"Successfully parsed order. {len(order.items)} items found, {asset_eligible} can be created as assets."
    if items_needing_clarification > 0:
        message += f" {items_needing_clarification} item(s) need clarification before import."
    
    return OrderImportPreview(
        success=True,
        vendor=order.vendor,
        order_number=order.order_number,
        order_date=order.order_date,
        customer=order.customer_name,
        total=order.total,
        items=preview_items,
        item_count=len(order.items),
        asset_eligible_count=asset_eligible,
        items_needing_clarification=items_needing_clarification,
        message=message
    )


@router.post("/import", response_model=OrderImportResult, summary="Import order and create assets")
async def import_order(
    file: UploadFile = File(..., description="Vendor order/invoice PDF"),
    vendor_hint: Optional[str] = Query(None, description="Vendor name hint if auto-detect fails"),
    create_assets: bool = Query(True, description="Create assets from order items"),
    skip_services: bool = Query(True, description="Skip service/support line items"),
    db: Session = Depends(get_db),
    services_db: Session = Depends(get_services_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Import order from vendor PDF and optionally create assets.
    
    1. Extracts text from PDF
    2. Auto-detects vendor and parses order
    3. Creates Asset records for each line item (respecting quantities)
    4. Links to VendorSKU if part numbers are found
    
    Returns count of created assets and their IDs.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read file content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Extract text from PDF
    try:
        text = extract_text_from_pdf(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from PDF")
    
    # Parse order
    order = parse_order(text, vendor_hint=vendor_hint)
    if not order:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse order. Available vendor parsers: {', '.join(get_available_parsers())}"
        )
    
    if not create_assets:
        return OrderImportResult(
            success=True,
            order_number=order.order_number,
            vendor=order.vendor,
            items_parsed=len(order.items),
            message="Order parsed successfully. Asset creation skipped (create_assets=false)."
        )
    
    # Create assets from order items
    from app.services.asset_service import AssetService
    from app.services.serial_service import generate_asset_tag, generate_serial_number
    from app.models.asset import AssetStatus
    from app.schemas.asset import AssetCreate
    from app.core.tenant import get_current_tenant_id, set_current_tenant_id
    
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        if current_user and getattr(current_user, 'tenant_id', None):
            tenant_id = current_user.tenant_id
            set_current_tenant_id(tenant_id)
        else:
            raise HTTPException(status_code=400, detail="No tenant context for asset creation")
    
    asset_service = AssetService(db)
    created_asset_ids = []
    skipped_count = 0
    
    for item in order.items:
        # Skip service items if requested
        if skip_services and item.category == 'service':
            skipped_count += 1
            continue
        
        # Map category to asset_type
        asset_type = _map_category_to_asset_type(item.category)
        
        # Create one asset per quantity
        for i in range(item.quantity):
            try:
                asset_tag = generate_asset_tag(db, asset_type, tenant_id)
                serial_number = generate_serial_number(db, asset_type, tenant_id)
                
                asset_data = AssetCreate(
                    asset_tag=asset_tag,
                    serial_number=serial_number,
                    asset_type=asset_type,
                    manufacturer=item.manufacturer or order.vendor,
                    model=item.part_number or item.description[:100],
                    status=AssetStatus.ORDERED,
                    description=item.description,
                    sku=item.sku or item.part_number,
                    purchase_cost=item.unit_price,
                    currency="USD",
                    supplier=order.vendor,
                    po_number=order.order_number,
                    custom_fields={
                        "vendor_order": order.order_number,
                        "vendor_order_date": order.order_date,
                        "line_item_description": item.description,
                        "extended_price": item.extended_price
                    }
                )
                
                created_asset = asset_service.create_asset(asset_data)
                created_asset_ids.append(created_asset.id)
                
            except Exception as e:
                print(f"Failed to create asset for item '{item.description[:50]}': {e}")
                continue
    
    return OrderImportResult(
        success=True,
        order_number=order.order_number,
        vendor=order.vendor,
        items_parsed=len(order.items),
        assets_created=len(created_asset_ids),
        skipped_services=skipped_count,
        message=f"Imported {len(created_asset_ids)} assets from order {order.order_number}",
        created_asset_ids=created_asset_ids
    )


def _map_category_to_asset_type(category: Optional[str]) -> str:
    """Map parser category to asset_type enum."""
    mapping = {
        'server': 'server_device',
        'network_switch': 'switch_device',
        'rack': 'rack',
        'pdu': 'pdu',
        # Transceivers - detect_category now returns the asset type directly
        'optical_transceiver': 'optical_transceiver',
        'transceiver': 'optical_transceiver',  # Legacy fallback
        # Cables - now specific types
        'fiber_cable': 'fiber_cable',
        'ethernet_cable': 'ethernet_cable',
        'dac_cable': 'dac_cable',
        'infiniband_cable': 'infiniband_cable',
        'cable': 'ethernet_cable',  # Legacy fallback - default to ethernet
        'service': 'other_device',  # Shouldn't happen if skipping services
    }
    return mapping.get(category, 'other_device')
