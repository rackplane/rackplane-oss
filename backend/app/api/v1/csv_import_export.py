# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
CSV Import/Export API Endpoints
Bulk import and export of assets via CSV format
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
import csv
import io
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_writable_user
from app.core.tenant_query import apply_tenant_filter
from app.core.tenant import get_current_tenant_id
from app.models.user import User
from app.models.asset import Asset, AssetStatus
from app.models.asset_type import AssetTypeModel
from app.services.asset_service import AssetService

router = APIRouter()


def detect_asset_type_from_data(row: Dict[str, Any]) -> Optional[str]:
    """
    Auto-detect asset type from CSV row data.
    Looks at manufacturer, model, description, and other fields to guess the type.
    """
    # Combine all text fields for analysis
    text_fields = [
        str(row.get('manufacturer', '')),
        str(row.get('model', '')),
        str(row.get('description', '')),
        str(row.get('hostname', '')),
        str(row.get('asset_tag', '')),
        str(row.get('serial_number', ''))
    ]
    combined_text = ' '.join(text_fields).lower()
    
    # Detection patterns (order matters - more specific first)
    if 'dac' in combined_text or 'direct attach' in combined_text or 'qsfp' in combined_text:
        return 'dac_cable'
    elif 'sfp' in combined_text or 'transceiver' in combined_text:
        return 'sfp_transceiver'
    elif 'console cable' in combined_text or 'rj45-db9' in combined_text or 'usb-serial' in combined_text:
        return 'console_cable'
    elif 'ethernet' in combined_text or 'cat' in combined_text or 'rj45' in combined_text:
        return 'ethernet_cable'
    elif 'power cable' in combined_text or 'c13' in combined_text or 'c14' in combined_text:
        return 'power_cable'
    elif 'fiber' in combined_text or 'optical' in combined_text:
        return 'fiber_cable'
    elif 'switch' in combined_text or 'nexus' in combined_text or 'brocade' in combined_text:
        return 'switch_device'
    elif 'router' in combined_text:
        return 'router_device'
    elif 'server' in combined_text or 'dl' in combined_text or 'poweredge' in combined_text:
        return 'server_device'
    elif 'pdu' in combined_text:
        return 'pdu_device'
    elif 'ups' in combined_text:
        return 'ups_device'
    elif 'firewall' in combined_text:
        return 'firewall_device'
    elif 'storage' in combined_text and 'box' in combined_text:
        return 'storage_box'
    elif 'rail' in combined_text or 'mount' in combined_text or 'caddy' in combined_text:
        return 'rack_accessory'
    elif 'memory' in combined_text or 'dimm' in combined_text or 'ddr' in combined_text:
        return 'memory_module'
    elif 'cpu' in combined_text or 'xeon' in combined_text or 'processor' in combined_text:
        return 'cpu'
    elif 'pcie' in combined_text or 'nic' in combined_text or 'adapter' in combined_text or 'mellanox' in combined_text:
        return 'expansion_card'
    elif 'ssd' in combined_text or 'nvme' in combined_text or 'disk' in combined_text or 'hdd' in combined_text:
        return 'storage_drive'
    elif 'kvm' in combined_text or 'terminal' in combined_text:
        return 'kvm_switch'
    
    return None


@router.get("/export", summary="Export assets to CSV")
async def export_assets_csv(
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Response:
    """
    Export assets to CSV format.
    
    Optional filters:
    - asset_type: Filter by asset type
    - status: Filter by status
    
    Returns a CSV file with all asset data.
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset)
    query = apply_tenant_filter(query, Asset)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if status:
        try:
            status_enum = AssetStatus(status)
            query = query.filter(Asset.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    assets = query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'asset_tag', 'serial_number', 'asset_type', 'manufacturer', 'model',
        'status', 'hostname', 'description', 'sku', 'purchase_cost',
        'purchase_date', 'currency', 'supplier', 'po_number',
        'datacenter_id', 'rack_id', 'rack_position_start', 'rack_position_end',
        'storage_container_id', 'container_id', 'height_u', 'power_consumption_watts',
        'on_loan', 'loan_direction', 'loan_party', 'loan_source',
        'has_console', 'has_ipmi', 'has_pdu', 'console_link', 'ipmi_link', 'pdu_link',
        'custom_fields'
    ])
    
    # Write data rows
    for asset in assets:
        # Serialize custom_fields as JSON string
        import json
        custom_fields_str = json.dumps(asset.custom_fields) if asset.custom_fields else ''
        
        writer.writerow([
            asset.asset_tag,
            asset.serial_number,
            asset.asset_type,
            asset.manufacturer,
            asset.model,
            asset.status.value if hasattr(asset.status, 'value') else str(asset.status),
            asset.hostname,
            asset.description,
            asset.sku,
            asset.purchase_cost,
            asset.purchase_date.isoformat() if asset.purchase_date else '',
            asset.currency,
            asset.supplier,
            asset.po_number,
            asset.datacenter_id,
            asset.rack_id,
            asset.rack_position_start,
            asset.rack_position_end,
            asset.storage_container_id,
            asset.container_id,
            asset.height_u,
            asset.power_consumption_watts,
            asset.on_loan,
            asset.loan_direction,
            asset.loan_party,
            asset.loan_source,
            asset.has_console,
            asset.has_ipmi,
            asset.has_pdu,
            asset.console_link,
            asset.ipmi_link,
            asset.pdu_link,
            custom_fields_str
        ])
    
    # Prepare response
    csv_content = output.getvalue()
    output.close()
    
    filename = f"assets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/import", summary="Import assets from CSV")
async def import_assets_csv(
    file: UploadFile = File(...),
    skip_errors: bool = Query(False),
    selected_rows: Optional[str] = Query(None, description="Comma-separated list of row numbers to import"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_writable_user)
) -> Dict[str, Any]:
    """
    Import assets from CSV file.
    
    CSV format should match the export format with these required columns:
    - asset_tag (required)
    - serial_number (required)
    - asset_type (required)
    - manufacturer (required)
    - model (required)
    - status (required)
    
    Optional columns:
    - All other asset fields
    
    Returns:
    - success: bool
    - imported_count: int
    - skipped_count: int
    - errors: List[str]
    """
    from app.schemas.asset import AssetCreate
    from app.services.audit_service import log_create
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read CSV file
    content = await file.read()
    csv_content = content.decode('utf-8')
    
    imported_count = 0
    skipped_count = 0
    errors = []
    
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context available")
    
    # Parse selected rows (if provided)
    selected_row_numbers = set()
    if selected_rows:
        try:
            selected_row_numbers = {int(r.strip()) for r in selected_rows.split(',') if r.strip()}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid selected_rows format. Expected comma-separated row numbers.")
    
    # Read CSV into list first to detect format
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    csv_rows = list(csv_reader)
    
    # Detect CSV format - check if it's the inventory format (Location, Quantity, Item Description)
    # vs the standard format (asset_tag, serial_number, etc.)
    is_inventory_format = False
    location_col_idx = None
    quantity_col_idx = None
    description_col_idx = None
    
    if csv_rows:
        first_row = csv_rows[0]
        # Get all column names, filtering out None/empty
        all_keys = [k for k in first_row.keys() if k and str(k).strip()]
        row_keys_lower = [k.lower().strip() for k in all_keys]
        
        # Check for standard format columns first
        has_asset_tag = any('asset_tag' in k or 'asset tag' in k for k in row_keys_lower)
        has_serial = any('serial' in k or 'serial_number' in k for k in row_keys_lower)
        
        # If we have asset_tag and serial_number, it's standard format
        if has_asset_tag and has_serial:
            is_inventory_format = False
        else:
            # Try to find inventory format columns by name
            has_location = any('location' in k or 'box' in k for k in row_keys_lower)
            has_quantity = any('quantity' in k or 'qty' in k for k in row_keys_lower)
            has_description = any('description' in k or 'item' in k for k in row_keys_lower)
            
            if has_location and has_quantity and has_description:
                is_inventory_format = True
            else:
                # Fallback: Try to detect by position/pattern
                # If first column has data that looks like a location/box name
                # and we don't have standard format, assume inventory format
                if all_keys and len(all_keys) >= 2:
                    first_col_name = all_keys[0].lower().strip()
                    first_col_value = str(first_row.get(all_keys[0], '')).strip()
                    
                    # If first column looks like location (contains "box", "rack", or has location-like data)
                    if ('box' in first_col_name or 'location' in first_col_name or 
                        'box' in first_col_value.lower() or 'rack' in first_col_value.lower()):
                        is_inventory_format = True
                        location_col_idx = 0
                        
                        # Try to find quantity and description columns
                        for idx, key in enumerate(all_keys):
                            key_lower = key.lower().strip()
                            if 'quantity' in key_lower or 'qty' in key_lower:
                                quantity_col_idx = idx
                            elif 'description' in key_lower or 'item' in key_lower:
                                description_col_idx = idx
                        
                        # If not found by name, assume position: col 0=location, col 1=quantity, col 2=description
                        if quantity_col_idx is None and len(all_keys) > 1:
                            quantity_col_idx = 1
                        if description_col_idx is None and len(all_keys) > 2:
                            description_col_idx = 2
    
    # Get all asset types for validation
    asset_types_query = db.query(AssetTypeModel)
    asset_types_query = apply_tenant_filter(asset_types_query, AssetTypeModel)
    asset_types = {at.name: at for at in asset_types_query.all()}
    
    service = AssetService(db)
    
    for row_num, row in enumerate(csv_rows, start=2):  # Start at 2 (header is row 1)
        # Skip if row is not in selected_rows (if provided)
        if selected_row_numbers and row_num not in selected_row_numbers:
            skipped_count += 1
            continue
        try:
            # Skip empty rows
            if not any(v for v in row.values() if v and str(v).strip()):
                continue
            
            # Handle inventory format (Location, Quantity, Item Description)
            if is_inventory_format:
                # Get valid column keys
                valid_keys = [k for k in row.keys() if k and str(k).strip()]
                
                # Find columns by name first
                location_col = next((k for k in valid_keys if 'location' in k.lower() or 'box' in k.lower()), None)
                quantity_col = next((k for k in valid_keys if 'quantity' in k.lower() or 'qty' in k.lower()), None)
                description_col = next((k for k in valid_keys if 'description' in k.lower() or 'item' in k.lower()), None)
                
                # If not found by name, use position-based detection
                if not location_col and location_col_idx is not None and location_col_idx < len(valid_keys):
                    location_col = valid_keys[location_col_idx]
                elif not location_col and len(valid_keys) > 0:
                    # First column is likely location
                    location_col = valid_keys[0]
                
                if not quantity_col and quantity_col_idx is not None and quantity_col_idx < len(valid_keys):
                    quantity_col = valid_keys[quantity_col_idx]
                elif not quantity_col and len(valid_keys) > 1:
                    # Second column is likely quantity
                    quantity_col = valid_keys[1]
                
                if not description_col and description_col_idx is not None and description_col_idx < len(valid_keys):
                    description_col = valid_keys[description_col_idx]
                elif not description_col and len(valid_keys) > 2:
                    # Third column is likely description
                    description_col = valid_keys[2]
                
                if not location_col or not description_col:
                    errors.append(f"Row {row_num}: Missing required columns (Location, Item Description). Found columns: {valid_keys}")
                    skipped_count += 1
                    continue
                
                location = str(row.get(location_col, '')).strip()
                quantity_str = str(row.get(quantity_col, '1')).strip() if quantity_col else '1'
                item_description = str(row.get(description_col, '')).strip()
                
                if not location or not item_description:
                    errors.append(f"Row {row_num}: Missing Location or Item Description")
                    skipped_count += 1
                    continue
                
                # Parse quantity
                try:
                    quantity = int(quantity_str) if quantity_str else 1
                except (ValueError, TypeError):
                    quantity = 1
                
                # Auto-detect asset type from item description
                asset_type_name = detect_asset_type_from_data({'description': item_description})
                if not asset_type_name:
                    # Try more specific detection for console cables
                    desc_lower = item_description.lower()
                    if 'console' in desc_lower or 'rj45' in desc_lower or 'coupler' in desc_lower:
                        asset_type_name = 'console_cable'
                    elif 'dac' in desc_lower:
                        asset_type_name = 'dac_cable'
                    elif 'sfp' in desc_lower:
                        asset_type_name = 'sfp_transceiver'
                    elif 'ethernet' in desc_lower:
                        asset_type_name = 'ethernet_cable'
                    elif 'power' in desc_lower:
                        asset_type_name = 'power_cable'
                    else:
                        asset_type_name = 'other_device'  # Default fallback
                
                # Validate asset type exists - if not, try to create common types
                if asset_type_name not in asset_types:
                    # Try to create common asset types if they don't exist
                    common_types = {
                        'console_cable': ('Console Cable', 'Console and serial cables'),
                        'dac_cable': ('DAC Cable', 'Direct Attach Copper cables'),
                        'ethernet_cable': ('Ethernet Cable', 'Ethernet network cables'),
                        'power_cable': ('Power Cable', 'Power cables and cords'),
                        'sfp_transceiver': ('SFP Transceiver', 'SFP/SFP+ optical transceivers'),
                        'other_device': ('Other Device', 'Miscellaneous devices')
                    }
                    
                    if asset_type_name in common_types:
                        display_name, description = common_types[asset_type_name]
                        new_asset_type = AssetTypeModel(
                            name=asset_type_name,
                            display_name=display_name,
                            description=description,
                            tenant_id=tenant_id,
                            is_system=False
                        )
                        db.add(new_asset_type)
                        db.commit()
                        db.refresh(new_asset_type)
                        asset_types[asset_type_name] = new_asset_type
                    else:
                        errors.append(f"Row {row_num}: Asset type '{asset_type_name}' not found. Please create it first.")
                        skipped_count += 1
                        continue
                
                # Find or create storage container/box
                from app.models.storage_container import StorageContainer
                from app.models.asset import Asset as AssetModel
                
                container_id = None
                container_name = location
                
                # First try to find existing storage container by name
                container_query = db.query(StorageContainer).filter(
                    StorageContainer.name.ilike(location)
                )
                container_query = apply_tenant_filter(container_query, StorageContainer)
                storage_container = container_query.first()
                
                if storage_container:
                    container_id = storage_container.id
                else:
                    # Try to find storage box asset by name
                    box_query = db.query(AssetModel).filter(
                        AssetModel.asset_type == 'storage_box',
                        AssetModel.asset_tag.ilike(f'%{location}%')
                    )
                    box_query = apply_tenant_filter(box_query, AssetModel)
                    storage_box = box_query.first()
                    
                    if storage_box:
                        container_id = storage_box.id
                    else:
                        # Create new storage box
                        from app.services.serial_service import generate_asset_tag, generate_serial_number
                        new_box = AssetModel(
                            asset_tag=generate_asset_tag(db, 'storage_box', tenant_id),
                            serial_number=generate_serial_number(db, 'storage_box', tenant_id),
                            asset_type='storage_box',
                            manufacturer='',
                            model='',
                            description=f"Storage box: {location}",
                            status=AssetStatus.IN_STORAGE,
                            tenant_id=tenant_id
                        )
                        db.add(new_box)
                        db.flush()
                        container_id = new_box.id
                        db.commit()
                
                # Create multiple assets (one for each quantity)
                for i in range(quantity):
                    # Auto-generate asset_tag and serial_number
                    from app.services.serial_service import generate_asset_tag, generate_serial_number
                    asset_tag = generate_asset_tag(db, asset_type_name, tenant_id)
                    serial_number = generate_serial_number(db, asset_type_name, tenant_id)
                    
                    # Extract manufacturer/model from description if possible
                    manufacturer = ''
                    model = item_description
                    
                    # Try to extract manufacturer
                    desc_lower = item_description.lower()
                    if 'cisco' in desc_lower:
                        manufacturer = 'Cisco'
                    elif 'fs' in desc_lower:
                        manufacturer = 'FS'
                    elif 'gtek' in desc_lower:
                        manufacturer = 'Gtek'
                    elif 'opengear' in desc_lower or 'digi' in desc_lower:
                        manufacturer = 'Opengear'
                    
                    # Create asset
                    asset_data = AssetCreate(
                        asset_tag=asset_tag,
                        serial_number=serial_number,
                        asset_type=asset_type_name,
                        manufacturer=manufacturer,
                        model=model,
                        status=AssetStatus.IN_STORAGE,
                        description=item_description,
                        container_id=container_id
                    )
                    
                    created_asset = service.create_asset(asset_data)
                    
                    # Log audit entry
                    try:
                        log_create(
                            db=db,
                            instance=created_asset,
                            user_id=current_user.id,
                            username=current_user.username,
                            tenant_id=tenant_id
                        )
                    except Exception:
                        pass
                    
                    imported_count += 1
                
                continue  # Skip the standard format processing below
            
            # Standard format processing (asset_tag, serial_number, etc.)
            # Normalize column names (handle case-insensitive and alternative names)
            # Map alternative column names to standard names
            column_mapping = {
                'rack': 'rack_id',
                'rack_name': 'rack_id',
                'rack_code': 'rack_id',
                'datacenter': 'datacenter_id',
                'dc': 'datacenter_id',
                'datacenter_name': 'datacenter_id',
                'datacenter_code': 'datacenter_id',
                'site': 'datacenter_id',
                'u': 'rack_position_start',
                'u_position': 'rack_position_start',
                'rack_u': 'rack_position_start',
                'position': 'rack_position_start',
                'u_start': 'rack_position_start',
                'rack_position': 'rack_position_start',
                'u_end': 'rack_position_end',
            }
            
            # Apply column name normalization (case-insensitive)
            normalized_row = {}
            for key, value in row.items():
                # Handle None keys (shouldn't happen, but be safe)
                if key is None:
                    continue
                key_lower = key.lower().strip() if key else ''
                if key_lower in column_mapping:
                    # Map to standard column name
                    standard_key = column_mapping[key_lower]
                    if standard_key not in normalized_row or not normalized_row[standard_key]:
                        normalized_row[standard_key] = value
                else:
                    # Keep original key (case-insensitive lookup)
                    normalized_row[key_lower] = value
            
            # Merge normalized values back into row (prefer normalized, fall back to original)
            for key, value in normalized_row.items():
                # Check if original row has this key (case-insensitive)
                original_key = next((k for k in row.keys() if k and k.lower().strip() == key), None)
                if not original_key or not row.get(original_key):
                    row[key] = value
                else:
                    # Use original key but ensure we can access it case-insensitively
                    row[key] = row[original_key]
            
            # Auto-detect asset_type if missing
            asset_type_name = row.get('asset_type')

            # If asset_type is explicitly provided as empty string, reject it
            if 'asset_type' in row and asset_type_name == '':
                errors.append(f"Row {row_num}: asset_type cannot be empty")
                skipped_count += 1
                continue

            if not asset_type_name:
                # Try to detect from other fields
                asset_type_name = detect_asset_type_from_data(row)
                if asset_type_name:
                    row['asset_type'] = asset_type_name
                    # Add warning that asset_type was auto-detected
                    if row_num not in [e.get('row_num', 0) for e in errors if isinstance(e, dict)]:
                        pass  # Will be handled in preview
                else:
                    errors.append(f"Row {row_num}: Missing required field 'asset_type' and could not auto-detect")
                    skipped_count += 1
                    continue
            
            # Check for explicitly empty required fields (reject empty strings)
            asset_tag_value = row.get('asset_tag')
            serial_number_value = row.get('serial_number')

            # Auto-generate if field is missing, None, or empty string
            # This allows users to leave fields blank in CSV for auto-generation
            if not asset_tag_value:
                from app.services.serial_service import generate_asset_tag
                row['asset_tag'] = generate_asset_tag(db, asset_type_name, tenant_id)

            if not serial_number_value:
                from app.services.serial_service import generate_serial_number
                row['serial_number'] = generate_serial_number(db, asset_type_name, tenant_id)
            
            # Validate asset_type exists
            asset_type_name = row['asset_type']
            if asset_type_name not in asset_types:
                errors.append(f"Row {row_num}: Asset type '{asset_type_name}' not found. Please create it first.")
                skipped_count += 1
                continue
            
            # Check for duplicates
            existing_query = db.query(Asset).filter(
                (Asset.asset_tag == row['asset_tag']) |
                (Asset.serial_number == row['serial_number'])
            )
            existing_query = apply_tenant_filter(existing_query, Asset)
            existing = existing_query.first()
            
            if existing:
                errors.append(f"Row {row_num}: Asset with tag '{row['asset_tag']}' or serial '{row['serial_number']}' already exists")
                skipped_count += 1
                continue
            
            # Parse status (handle None values)
            status_str = row.get('status') or 'received'
            try:
                status_enum = AssetStatus(str(status_str).lower())
            except (ValueError, AttributeError):
                errors.append(f"Row {row_num}: Invalid status '{status_str}'")
                skipped_count += 1
                continue
            
            # Parse custom_fields JSON
            custom_fields = {}
            if row.get('custom_fields'):
                try:
                    import json
                    custom_fields = json.loads(row['custom_fields'])
                except json.JSONDecodeError:
                    errors.append(f"Row {row_num}: Invalid custom_fields JSON")
                    skipped_count += 1
                    continue
            
            # Parse dates
            purchase_date = None
            if row.get('purchase_date'):
                try:
                    purchase_date = datetime.fromisoformat(row['purchase_date'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass  # Invalid date, leave as None
            
            # Parse numeric fields
            purchase_cost = None
            if row.get('purchase_cost'):
                try:
                    purchase_cost = float(row['purchase_cost'])
                except (ValueError, TypeError):
                    pass
            
            rack_position_start = None
            if row.get('rack_position_start'):
                try:
                    rack_position_start = int(row['rack_position_start'])
                except (ValueError, TypeError):
                    pass
            
            rack_position_end = None
            if row.get('rack_position_end'):
                try:
                    rack_position_end = int(row['rack_position_end'])
                except (ValueError, TypeError):
                    pass
            
            height_u = None
            if row.get('height_u'):
                try:
                    height_u = int(row['height_u'])
                except (ValueError, TypeError):
                    pass
            
            power_consumption_watts = None
            if row.get('power_consumption_watts'):
                try:
                    power_consumption_watts = float(row['power_consumption_watts'])
                except (ValueError, TypeError):
                    pass
            
            # Parse boolean fields (handle None values)
            on_loan_val = row.get('on_loan')
            on_loan = str(on_loan_val).lower() in ('true', '1', 'yes', 'y') if on_loan_val else False
            
            has_console_val = row.get('has_console')
            has_console = str(has_console_val).lower() in ('true', '1', 'yes', 'y') if has_console_val else False
            
            has_ipmi_val = row.get('has_ipmi')
            has_ipmi = str(has_ipmi_val).lower() in ('true', '1', 'yes', 'y') if has_ipmi_val else False
            
            has_pdu_val = row.get('has_pdu')
            has_pdu = str(has_pdu_val).lower() in ('true', '1', 'yes', 'y') if has_pdu_val else False
            
            # Parse integer foreign keys or look up by name/code
            from app.models.location import Datacenter, Rack
            
            datacenter_id = None
            if row.get('datacenter_id'):
                try:
                    # Try as integer ID first
                    datacenter_id = int(row['datacenter_id'])
                except (ValueError, TypeError):
                    # Try to look up by name or code
                    dc_name_or_code = str(row['datacenter_id']).strip()
                    if dc_name_or_code:
                        dc_query = db.query(Datacenter).filter(
                            (Datacenter.name.ilike(dc_name_or_code)) |
                            (Datacenter.code.ilike(dc_name_or_code))
                        )
                        dc_query = apply_tenant_filter(dc_query, Datacenter)
                        datacenter = dc_query.first()
                        if datacenter:
                            datacenter_id = datacenter.id
                        else:
                            errors.append(f"Row {row_num}: Datacenter '{dc_name_or_code}' not found")
                            if not skip_errors:
                                skipped_count += 1
                                continue
            
            rack_id = None
            if row.get('rack_id'):
                try:
                    # Try as integer ID first
                    rack_id = int(row['rack_id'])
                except (ValueError, TypeError):
                    # Try to look up by name or code
                    rack_name_or_code = str(row['rack_id']).strip()
                    if rack_name_or_code:
                        rack_query = db.query(Rack).filter(
                            (Rack.name.ilike(rack_name_or_code)) |
                            (Rack.code.ilike(rack_name_or_code))
                        )
                        rack_query = apply_tenant_filter(rack_query, Rack)
                        # If datacenter_id is known, filter by it too
                        if datacenter_id:
                            rack_query = rack_query.filter(Rack.datacenter_id == datacenter_id)
                        rack = rack_query.first()
                        if rack:
                            rack_id = rack.id
                        else:
                            errors.append(f"Row {row_num}: Rack '{rack_name_or_code}' not found" + 
                                        (f" in datacenter {datacenter_id}" if datacenter_id else ""))
                            if not skip_errors:
                                skipped_count += 1
                                continue
            
            storage_container_id = None
            if row.get('storage_container_id'):
                try:
                    storage_container_id = int(row['storage_container_id'])
                except (ValueError, TypeError):
                    pass
            
            container_id = None
            if row.get('container_id'):
                try:
                    container_id = int(row['container_id'])
                except (ValueError, TypeError):
                    pass
            
            # Create asset data
            asset_data = AssetCreate(
                asset_tag=row['asset_tag'],
                serial_number=row['serial_number'],
                asset_type=asset_type_name,
                manufacturer=row.get('manufacturer', ''),
                model=row.get('model', ''),
                status=status_enum,
                hostname=row.get('hostname'),
                description=row.get('description'),
                sku=row.get('sku'),
                purchase_cost=purchase_cost,
                purchase_date=purchase_date,
                currency=row.get('currency', 'USD'),
                supplier=row.get('supplier'),
                po_number=row.get('po_number'),
                datacenter_id=datacenter_id,
                rack_id=rack_id,
                rack_position_start=rack_position_start,
                rack_position_end=rack_position_end,
                storage_container_id=storage_container_id,
                container_id=container_id,
                height_u=height_u,
                power_consumption_watts=power_consumption_watts,
                on_loan=on_loan,
                loan_direction=row.get('loan_direction'),
                loan_party=row.get('loan_party'),
                loan_source=row.get('loan_source'),
                has_console=has_console,
                has_ipmi=has_ipmi,
                has_pdu=has_pdu,
                console_link=row.get('console_link'),
                ipmi_link=row.get('ipmi_link'),
                pdu_link=row.get('pdu_link'),
                custom_fields=custom_fields
            )
            
            # Create asset
            created_asset = service.create_asset(asset_data)
            
            # Log audit entry
            try:
                log_create(
                    db=db,
                    instance=created_asset,
                    user_id=current_user.id,
                    username=current_user.username,
                    tenant_id=tenant_id
                )
            except Exception as e:
                # Don't fail import if audit logging fails
                pass
            
            imported_count += 1
            
        except IntegrityError as e:
            error_msg = f"Row {row_num}: Database integrity error - {str(e)}"
            errors.append(error_msg)
            skipped_count += 1
            if not skip_errors:
                db.rollback()
            else:
                db.rollback()
        except Exception as e:
            error_msg = f"Row {row_num}: Error - {str(e)}"
            errors.append(error_msg)
            skipped_count += 1
            if not skip_errors:
                db.rollback()
            else:
                db.rollback()
    
    return {
        "success": len(errors) == 0 or skip_errors,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "total_rows": imported_count + skipped_count,
        "errors": errors[:100]  # Limit to first 100 errors
    }


@router.post("/preview", summary="Preview CSV import without importing")
async def preview_csv_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Preview CSV import - parse and validate CSV without importing.
    Returns a list of items that would be imported with validation status.
    """
    from app.models.location import Datacenter, Rack
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read CSV file
    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    csv_rows = list(csv_reader)
    
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context available")
    
    # Detect CSV format - same logic as import
    is_inventory_format = False
    location_col_idx = None
    quantity_col_idx = None
    description_col_idx = None
    
    if csv_rows:
        first_row = csv_rows[0]
        all_keys = [k for k in first_row.keys() if k and str(k).strip()]
        row_keys_lower = [k.lower().strip() for k in all_keys]
        
        # Check for standard format columns first
        has_asset_tag = any('asset_tag' in k or 'asset tag' in k for k in row_keys_lower)
        has_serial = any('serial' in k or 'serial_number' in k for k in row_keys_lower)
        
        if has_asset_tag and has_serial:
            is_inventory_format = False
        else:
            # Try to find inventory format columns by name
            has_location = any('location' in k or 'box' in k for k in row_keys_lower)
            has_quantity = any('quantity' in k or 'qty' in k for k in row_keys_lower)
            has_description = any('description' in k or 'item' in k for k in row_keys_lower)
            
            if has_location and has_quantity and has_description:
                is_inventory_format = True
            elif all_keys and len(all_keys) >= 2:
                # Fallback: position-based detection
                first_col_name = all_keys[0].lower().strip()
                first_col_value = str(first_row.get(all_keys[0], '')).strip()
                
                if ('box' in first_col_name or 'location' in first_col_name or 
                    'box' in first_col_value.lower() or 'rack' in first_col_value.lower()):
                    is_inventory_format = True
                    location_col_idx = 0
                    if len(all_keys) > 1:
                        quantity_col_idx = 1
                    if len(all_keys) > 2:
                        description_col_idx = 2
    
    # Get all asset types for validation
    asset_types_query = db.query(AssetTypeModel)
    asset_types_query = apply_tenant_filter(asset_types_query, AssetTypeModel)
    asset_types = {at.name: at for at in asset_types_query.all()}
    
    # Get all datacenters and racks for lookup
    datacenters_query = db.query(Datacenter)
    datacenters_query = apply_tenant_filter(datacenters_query, Datacenter)
    datacenters = {dc.id: dc for dc in datacenters_query.all()}
    datacenters_by_name = {dc.name.lower(): dc for dc in datacenters_query.all()}
    datacenters_by_code = {dc.code.lower(): dc for dc in datacenters_query.all() if dc.code}
    
    racks_query = db.query(Rack)
    racks_query = apply_tenant_filter(racks_query, Rack)
    racks = {rack.id: rack for rack in racks_query.all()}
    racks_by_name = {rack.name.lower(): rack for rack in racks_query.all()}
    racks_by_code = {rack.code.lower(): rack for rack in racks_query.all() if rack.code}
    
    preview_items = []
    
    for row_num, row in enumerate(csv_rows, start=2):  # Start at 2 (header is row 1)
        item = {
            "row_number": row_num,
            "selected": True,  # Default to selected
            "valid": True,
            "errors": [],
            "warnings": [],
            "data": {}
        }
        
        try:
            # Skip empty rows
            if not any(row.values()):
                continue
            
            # Handle inventory format (Location, Quantity, Item Description)
            if is_inventory_format:
                # Get valid column keys
                valid_keys = [k for k in row.keys() if k and str(k).strip()]
                
                # Find columns by name first
                location_col = next((k for k in valid_keys if 'location' in k.lower() or 'box' in k.lower()), None)
                quantity_col = next((k for k in valid_keys if 'quantity' in k.lower() or 'qty' in k.lower()), None)
                description_col = next((k for k in valid_keys if 'description' in k.lower() or 'item' in k.lower()), None)
                
                # If not found by name, use position-based detection
                if not location_col and location_col_idx is not None and location_col_idx < len(valid_keys):
                    location_col = valid_keys[location_col_idx]
                elif not location_col and len(valid_keys) > 0:
                    location_col = valid_keys[0]
                
                if not quantity_col and quantity_col_idx is not None and quantity_col_idx < len(valid_keys):
                    quantity_col = valid_keys[quantity_col_idx]
                elif not quantity_col and len(valid_keys) > 1:
                    quantity_col = valid_keys[1]
                
                if not description_col and description_col_idx is not None and description_col_idx < len(valid_keys):
                    description_col = valid_keys[description_col_idx]
                elif not description_col and len(valid_keys) > 2:
                    description_col = valid_keys[2]
                
                if not location_col or not description_col:
                    item = {
                        "row_number": row_num,
                        "selected": True,
                        "valid": False,
                        "errors": [f"Missing required columns (Location, Item Description). Found: {valid_keys}"],
                        "warnings": [],
                        "data": {}
                    }
                    preview_items.append(item)
                    continue
                
                location = str(row.get(location_col, '')).strip()
                quantity_str = str(row.get(quantity_col, '1')).strip() if quantity_col else '1'
                item_description = str(row.get(description_col, '')).strip()
                
                if not location or not item_description:
                    item = {
                        "row_number": row_num,
                        "selected": True,
                        "valid": False,
                        "errors": ["Missing Location or Item Description"],
                        "warnings": [],
                        "data": {}
                    }
                    preview_items.append(item)
                    continue
                
                # Parse quantity
                try:
                    quantity = int(quantity_str) if quantity_str else 1
                except (ValueError, TypeError):
                    quantity = 1
                
                # Auto-detect asset type
                asset_type_name = detect_asset_type_from_data({'description': item_description})
                if not asset_type_name:
                    asset_type_name = 'other_device'
                
                # Validate asset type
                if asset_type_name not in asset_types:
                    item = {
                        "row_number": row_num,
                        "selected": True,
                        "valid": False,
                        "errors": [f"Asset type '{asset_type_name}' not found"],
                        "warnings": [],
                        "data": {
                            "location": location,
                            "quantity": quantity,
                            "item_description": item_description,
                            "asset_type": asset_type_name
                        }
                    }
                    preview_items.append(item)
                    continue
                
                # Check if container exists
                from app.models.storage_container import StorageContainer
                from app.models.asset import Asset as AssetModel
                
                container_query = db.query(StorageContainer).filter(
                    StorageContainer.name.ilike(location)
                )
                container_query = apply_tenant_filter(container_query, StorageContainer)
                storage_container = container_query.first()
                
                box_query = db.query(AssetModel).filter(
                    AssetModel.asset_type == 'storage_box',
                    AssetModel.asset_tag.ilike(f'%{location}%')
                )
                box_query = apply_tenant_filter(box_query, AssetModel)
                storage_box = box_query.first()
                
                container_exists = storage_container is not None or storage_box is not None
                
                # Create preview item
                item = {
                    "row_number": row_num,
                    "selected": True,
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                    "data": {
                        "location": location,
                        "quantity": quantity,
                        "item_description": item_description,
                        "asset_type": asset_type_name,
                        "container_exists": container_exists,
                        "asset_tag": f"(Will generate {quantity} assets)",
                        "serial_number": "(Will auto-generate)",
                        "manufacturer": "",
                        "model": item_description,
                        "status": "in_storage"
                    }
                }
                
                if not container_exists:
                    item["warnings"].append(f"Storage box '{location}' will be created")
                
                if asset_type_name == 'other_device':
                    item["warnings"].append("Asset type auto-detected as 'other_device'")
                else:
                    item["warnings"].append(f"Asset type auto-detected as '{asset_type_name}'")
                
                item["warnings"].append(f"Will create {quantity} asset(s)")
                
                preview_items.append(item)
                continue  # Skip standard format processing
            
            # Normalize column names
            column_mapping = {
                'rack': 'rack_id',
                'rack_name': 'rack_id',
                'rack_code': 'rack_id',
                'datacenter': 'datacenter_id',
                'dc': 'datacenter_id',
                'datacenter_name': 'datacenter_id',
                'datacenter_code': 'datacenter_id',
                'site': 'datacenter_id',
                'u': 'rack_position_start',
                'u_position': 'rack_position_start',
                'rack_u': 'rack_position_start',
                'position': 'rack_position_start',
                'u_start': 'rack_position_start',
                'rack_position': 'rack_position_start',
                'u_end': 'rack_position_end',
            }
            
            normalized_row = {}
            for key, value in row.items():
                if key is None:
                    continue
                key_lower = key.lower().strip() if key else ''
                if key_lower in column_mapping:
                    standard_key = column_mapping[key_lower]
                    if standard_key not in normalized_row or not normalized_row[standard_key]:
                        normalized_row[standard_key] = value
                else:
                    normalized_row[key_lower] = value
            
            # Merge normalized values back
            for key, value in normalized_row.items():
                original_key = next((k for k in row.keys() if k and k.lower().strip() == key), None)
                if not original_key or not row.get(original_key):
                    row[key] = value
                else:
                    row[key] = row[original_key]
            
            # Auto-detect asset_type if missing
            asset_type_name = row.get('asset_type')
            if not asset_type_name:
                asset_type_name = detect_asset_type_from_data(row)
                if asset_type_name:
                    row['asset_type'] = asset_type_name
                    item["warnings"].append(f"Asset type auto-detected as '{asset_type_name}'")
                else:
                    item["valid"] = False
                    item["errors"].append("Missing required field 'asset_type' and could not auto-detect")
            
            # Validate asset_type exists
            if asset_type_name and asset_type_name not in asset_types:
                item["valid"] = False
                item["errors"].append(f"Asset type '{asset_type_name}' not found. Please create it first.")
            
            # Auto-generate asset_tag if missing
            asset_tag = row.get('asset_tag')
            if not asset_tag and asset_type_name and asset_type_name in asset_types:
                from app.services.serial_service import generate_asset_tag
                asset_tag = generate_asset_tag(db, asset_type_name, tenant_id)
                row['asset_tag'] = asset_tag
                item["warnings"].append("Asset tag will be auto-generated")
            
            # Auto-generate serial_number if missing
            serial_number = row.get('serial_number')
            if not serial_number and asset_type_name and asset_type_name in asset_types:
                from app.services.serial_service import generate_serial_number
                serial_number = generate_serial_number(db, asset_type_name, tenant_id)
                row['serial_number'] = serial_number
                item["warnings"].append("Serial number will be auto-generated")
            
            # Final validation
            if not asset_tag:
                item["valid"] = False
                item["errors"].append("Missing required field 'asset_tag' and could not auto-generate")
            
            if not serial_number:
                item["valid"] = False
                item["errors"].append("Missing required field 'serial_number' and could not auto-generate")
            
            # Check for duplicates
            if asset_tag and serial_number:
                existing_query = db.query(Asset).filter(
                    (Asset.asset_tag == asset_tag) |
                    (Asset.serial_number == serial_number)
                )
                existing_query = apply_tenant_filter(existing_query, Asset)
                existing = existing_query.first()
                if existing:
                    item["valid"] = False
                    item["errors"].append(f"Asset with tag '{asset_tag}' or serial '{serial_number}' already exists")
            
            # Parse and validate datacenter
            datacenter_id = None
            datacenter_name = None
            datacenter_code = None
            if row.get('datacenter_id'):
                try:
                    datacenter_id = int(row['datacenter_id'])
                    if datacenter_id in datacenters:
                        dc = datacenters[datacenter_id]
                        datacenter_name = dc.name
                        datacenter_code = dc.code
                    else:
                        item["warnings"].append(f"Datacenter ID {datacenter_id} not found")
                except (ValueError, TypeError):
                    dc_name_or_code = str(row['datacenter_id']).strip().lower()
                    if dc_name_or_code:
                        if dc_name_or_code in datacenters_by_name:
                            dc = datacenters_by_name[dc_name_or_code]
                            datacenter_id = dc.id
                            datacenter_name = dc.name
                            datacenter_code = dc.code
                        elif dc_name_or_code in datacenters_by_code:
                            dc = datacenters_by_code[dc_name_or_code]
                            datacenter_id = dc.id
                            datacenter_name = dc.name
                            datacenter_code = dc.code
                        else:
                            item["warnings"].append(f"Datacenter '{row['datacenter_id']}' not found")
            
            # Parse and validate rack
            rack_id = None
            rack_name = None
            rack_code = None
            if row.get('rack_id'):
                try:
                    rack_id = int(row['rack_id'])
                    if rack_id in racks:
                        rack = racks[rack_id]
                        rack_name = rack.name
                        rack_code = rack.code
                        # Auto-detect datacenter if not specified
                        if not datacenter_id and rack.datacenter_id:
                            datacenter_id = rack.datacenter_id
                            if datacenter_id in datacenters:
                                dc = datacenters[datacenter_id]
                                datacenter_name = dc.name
                                datacenter_code = dc.code
                    else:
                        item["warnings"].append(f"Rack ID {rack_id} not found")
                except (ValueError, TypeError):
                    rack_name_or_code = str(row['rack_id']).strip().lower()
                    if rack_name_or_code:
                        if rack_name_or_code in racks_by_name:
                            rack = racks_by_name[rack_name_or_code]
                            rack_id = rack.id
                            rack_name = rack.name
                            rack_code = rack.code
                            # Auto-detect datacenter if not specified
                            if not datacenter_id and rack.datacenter_id:
                                datacenter_id = rack.datacenter_id
                                if datacenter_id in datacenters:
                                    dc = datacenters[datacenter_id]
                                    datacenter_name = dc.name
                                    datacenter_code = dc.code
                        elif rack_name_or_code in racks_by_code:
                            rack = racks_by_code[rack_name_or_code]
                            rack_id = rack.id
                            rack_name = rack.name
                            rack_code = rack.code
                            # Auto-detect datacenter if not specified
                            if not datacenter_id and rack.datacenter_id:
                                datacenter_id = rack.datacenter_id
                                if datacenter_id in datacenters:
                                    dc = datacenters[datacenter_id]
                                    datacenter_name = dc.name
                                    datacenter_code = dc.code
                        else:
                            item["warnings"].append(f"Rack '{row['rack_id']}' not found")
            
            # Build preview data (use auto-generated values if they were created)
            item["data"] = {
                "asset_tag": asset_tag or row.get('asset_tag', ''),
                "serial_number": serial_number or row.get('serial_number', ''),
                "asset_type": asset_type_name or row.get('asset_type', ''),
                "manufacturer": row.get('manufacturer', ''),
                "model": row.get('model', ''),
                "status": row.get('status', 'received'),
                "hostname": row.get('hostname', ''),
                "description": row.get('description', ''),
                "datacenter_id": datacenter_id,
                "datacenter_name": datacenter_name,
                "datacenter_code": datacenter_code,
                "rack_id": rack_id,
                "rack_name": rack_name,
                "rack_code": rack_code,
                "rack_position_start": row.get('rack_position_start', ''),
                "rack_position_end": row.get('rack_position_end', ''),
            }
            
        except Exception as e:
            item["valid"] = False
            item["errors"].append(f"Error parsing row: {str(e)}")
        
        preview_items.append(item)
    
    return {
        "success": True,
        "total_rows": len(preview_items),
        "valid_rows": sum(1 for item in preview_items if item["valid"]),
        "invalid_rows": sum(1 for item in preview_items if not item["valid"]),
        "items": preview_items
    }

