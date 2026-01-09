# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Stock Service
Handles asset lifecycle and inventory stock management for multi-tenant DCIM system.

This service provides comprehensive stock management functionality including:
- Automatic storage box creation and naming
- Stock level tracking and low stock alerts
- Asset assignment to storage boxes
- Stock count calculations by asset type
- Cable-to-storage-box synchronization

Key Features:
- Auto-generates storage box names based on cable specifications
- Tracks stock levels using status=IN_STORAGE and container_id
- Calculates stock counts by grouping assets (manufacturer+model+asset_type)
- Triggers low stock alerts when stock falls below min_stock_threshold
- Automatically assigns cables to storage boxes on create/update

Stock Tracking:
- Assets with status=IN_STORAGE and container_id set are "in stock"
- Storage boxes (asset_type='storage_box') have min_stock_threshold
- Stock counts group by manufacturer+model+asset_type
- Low stock alerts trigger when count < min_stock_threshold

Usage:
    from app.services.stock_service import sync_storage_box_for_cable, get_stock_count
    
    # Auto-assign cable to storage box
    box = sync_storage_box_for_cable(db, cable_asset)
    
    # Get stock count for an asset type
    count = get_stock_count(db, manufacturer, model, asset_type)
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
import logging
from typing import Optional
import re

from app.models.asset import Asset, AssetStatus
from app.core.tenant_query import apply_tenant_filter

logger = logging.getLogger(__name__)


def generate_storage_box_name(asset) -> Optional[str]:
    """
    Generate a standardized storage box name based on cable type and specifications.
    
    Naming conventions:
    - DAC: DAC-{speed}-{connectorA}-{connectorB}-{length}
      Example: DAC-800G-OSFP112-OSFP112-1M
    - Fiber: FIBER-{type}-{connectorA}-{connectorB}-{length}
      Example: FIBER-SM-MTP12-MTP12-1M
    
    Args:
        asset: Asset object (or object with asset_type and custom_fields) to generate box name for
        
    Returns:
        Generated box name string, or None if insufficient data
    """
    if not asset:
        return None
    
    # Handle both Asset objects and dict-like objects
    if hasattr(asset, 'custom_fields'):
        custom_fields = asset.custom_fields or {}
        asset_type = asset.asset_type
    elif isinstance(asset, dict):
        custom_fields = asset.get('custom_fields', {}) or {}
        asset_type = asset.get('asset_type', '')
    else:
        return None
    
    # Normalize length (convert to uppercase, remove spaces)
    def normalize_length(length_str: str) -> str:
        """Normalize length string (e.g., '1m' -> '1M', '3 feet' -> '3FT')"""
        if not length_str:
            return ''
        # Remove spaces, convert to uppercase
        normalized = length_str.strip().upper().replace(' ', '')
        # If it ends with 'm' or 'ft', ensure uppercase
        if normalized.endswith('m') and not normalized.endswith('M'):
            normalized = normalized[:-1] + 'M'
        elif normalized.endswith('ft') and not normalized.endswith('FT'):
            normalized = normalized[:-2] + 'FT'
        return normalized
    
    # DAC Cable naming: DAC-{speed}-{connectorA}-{connectorB}-{length}
    if asset_type == 'dac_cable':
        speed = custom_fields.get('dac_speed', '').strip().upper()
        # Prioritize formal columns, fallback to custom_fields
        connector_a = (getattr(asset, 'connector_type_end_a', None) or 
                       custom_fields.get('dac_connector_a', '')).strip().upper()
        connector_b = (getattr(asset, 'connector_type_end_b', None) or 
                       custom_fields.get('dac_connector_b', '')).strip().upper()
        length = normalize_length(custom_fields.get('cable_length', ''))
        
        # Require at least speed and connectors
        if not speed or not connector_a or not connector_b:
            return None
        
        # If length is missing, use 'VAR' for variable
        if not length:
            length = 'VAR'
        
        return f"DAC-{speed}-{connector_a}-{connector_b}-{length}"
    
    # Fiber Cable naming: FIBER-{type}-{connectorA}-{connectorB}-{length}
    elif asset_type == 'fiber_cable':
        fiber_type = custom_fields.get('fiber_type', '').strip().upper()
        # Prioritize formal columns, fallback to custom_fields
        connector_a = (getattr(asset, 'connector_type_end_a', None) or 
                       custom_fields.get('fiber_connector_a', '')).strip().upper()
        connector_b = (getattr(asset, 'connector_type_end_b', None) or 
                       custom_fields.get('fiber_connector_b', '')).strip().upper()
        length = normalize_length(custom_fields.get('cable_length', ''))
        
        # Require at least fiber type and connectors
        if not fiber_type or not connector_a or not connector_b:
            return None
        
        # If length is missing, use 'VAR' for variable
        if not length:
            length = 'VAR'
        
        return f"FIBER-{fiber_type}-{connector_a}-{connector_b}-{length}"
    
    # Other cable types - use generic format if possible
    elif 'cable' in asset_type.lower():
        # For generic cables, use formalized ends if available, else main connector_type
        connector_a = (getattr(asset, 'connector_type_end_a', None) or 
                       custom_fields.get('connector_type_end_a', '')).strip().upper()
        connector_b = (getattr(asset, 'connector_type_end_b', None) or 
                       custom_fields.get('connector_type_end_b', '')).strip().upper()
        
        main_connector = (getattr(asset, 'power_connector_type', None) or 
                        custom_fields.get('connector_type', '')).strip().upper()
        
        length = normalize_length(custom_fields.get('cable_length', ''))
        
        if not connector_a and not connector_b and not main_connector and not length:
            return None
        
        # Generic format: {asset_type}-{connector}-{length}
        asset_type_short = asset_type.upper().replace('_', '-')
        
        if connector_a and connector_b:
            connector_part = f"{connector_a}-{connector_b}"
        else:
            connector_part = main_connector if main_connector else 'VAR'
            
        length_part = length if length else 'VAR'
        
        return f"{asset_type_short}-{connector_part}-{length_part}"
    
    return None


def find_or_create_storage_box(
    db: Session,
    cable_asset: Asset,
    min_stock_threshold: int = 5
) -> Optional[Asset]:
    """
    Find or create a storage box for a cable based on its type and specifications.
    
    This function:
    1. Generates a box name using generate_storage_box_name()
    2. Searches for an existing box with that name
    3. If not found, creates a new storage box asset
    4. Returns the box asset (existing or newly created)
    
    Args:
        db: SQLAlchemy database session
        cable_asset: Cable asset to find/create box for
        min_stock_threshold: Minimum stock threshold for the box (default: 5)
        
    Returns:
        Storage box Asset object, or None if box name couldn't be generated
    """
    box_name = generate_storage_box_name(cable_asset)
    
    if not box_name:
        logger.warning(
            f"Cannot generate box name for cable {cable_asset.asset_tag} (ID: {cable_asset.id}). "
            f"Missing required fields."
        )
        return None
    
    # Retry loop to handle race conditions
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Search for existing box with this name
            # We use a nested transaction (savepoint) to prevent breaking the main transaction
            # if we encounter an error, though regular query shouldn't cause one
            query = db.query(Asset).filter(
                Asset.asset_tag == box_name,
                Asset.min_stock_threshold > 0  # Must be a storage box
            )
            query = apply_tenant_filter(query, Asset)
            existing_box = query.first()
            
            if existing_box:
                logger.debug(f"Found existing storage box: {box_name} (ID: {existing_box.id})")
                return existing_box
            
            # Create new storage box
            from app.core.tenant import get_current_tenant_id
            from sqlalchemy.exc import IntegrityError
            
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                logger.error("Cannot create storage box: no tenant context")
                return None
            
            # Generate proper serial number using the serial service
            from app.services.serial_service import generate_serial_number, generate_asset_tag
            
            # Use a nested transaction for creation to safely rollback if uniqueness fails
            with db.begin_nested():
                serial_number = generate_serial_number(db, "storage_box", tenant_id)
                asset_tag = generate_asset_tag(db, "storage_box", tenant_id)
                
                # NOTE: We override asset_tag with box_name below, but keeping generation for safety
                
                new_box = Asset(
                    asset_tag=box_name,  # Use descriptive box name as asset tag
                    serial_number=serial_number,  # Use proper format: TYPE-TENANT-RANDOM-CHECK
                    asset_type="storage_box",  # storage_device is for physical systems with disk drives, not boxes
                    manufacturer="System",
                    model="Storage Box",
                    status=AssetStatus.ACTIVE,
                    min_stock_threshold=min_stock_threshold,  # Use the provided threshold
                    description=f"Auto-generated storage box for {cable_asset.asset_type} cables (min threshold: {min_stock_threshold})",
                    tenant_id=tenant_id
                )
                
                db.add(new_box)
                db.flush() # Flush to catch integrity errors within the nested block
            
            # Outside nested block, commit the savepoint changes to the main transaction
            # db.commit() # DO NOT COMMIT THE MAIN TRANSACTION HERE - let the caller decide
            
            # Check if we need to refresh (might not be needed if flush populated ID)
            if new_box.id:
                 logger.info(f"Created new storage box: {box_name} (ID: {new_box.id})")
                 return new_box
                 
        except Exception as e:
            # Check for integrity error (UniqueViolation)
            is_integrity_error = "unique constraint" in str(e).lower() or "integrity" in str(e).lower()
            
            if is_integrity_error:
                logger.warning(f"Race condition creating storage box {box_name}: {e}. Retrying ({attempt+1}/{max_retries})...")
                # If it was a race condition, the box likely exists now, so next loop should find it
                continue
            else:
                logger.error(f"Error creating storage box {box_name}: {e}")
                # For non-integrity errors, re-raise
                raise e
    
    logger.error(f"Failed to find or create storage box {box_name} after {max_retries} attempts")
    return None


def sync_storage_box_for_cable(db: Session, cable_asset: Asset) -> Optional[Asset]:
    """
    Automatically create or update storage box for a cable based on the number of cables of that type.
    
    This function:
    1. Generates the box name for the cable
    2. Counts how many cables of this type exist (with same box name)
    3. Creates or updates the storage box with min_stock_threshold = count
    
    Args:
        db: SQLAlchemy database session
        cable_asset: Cable asset to sync storage box for
        
    Returns:
        Storage box Asset object, or None if box name couldn't be generated
    """
    box_name = generate_storage_box_name(cable_asset)
    
    if not box_name:
        logger.debug(
            f"Cannot sync storage box for cable {cable_asset.asset_tag} (ID: {cable_asset.id}). "
            f"Missing required fields for box name generation."
        )
        return None
    
    # Count how many cables of this type exist (that would go in this box)
    # We need to find all cables that would generate the same box name
    from sqlalchemy import func, or_
    
    # For DAC cables: match by speed, connectors, length
    # For Fiber cables: match by type, connectors, length
    # This is a simplified approach - we'll count cables that match the same box name pattern
    
    # Get all cables in the same tenant
    query = db.query(Asset).filter(
        Asset.tenant_id == cable_asset.tenant_id,
        Asset.asset_type == cable_asset.asset_type
    )
    query = apply_tenant_filter(query, Asset)
    all_cables = query.all()
    
    # Count cables that would generate the same box name
    matching_count = 0
    for cable in all_cables:
        if generate_storage_box_name(cable) == box_name:
            matching_count += 1
    
    # Ensure threshold is at least 1
    threshold = max(matching_count, 1)
    
    # Find or create the storage box
    box_query = db.query(Asset).filter(
        Asset.asset_tag == box_name,
        Asset.tenant_id == cable_asset.tenant_id
    )
    box_query = apply_tenant_filter(box_query, Asset)
    existing_box = box_query.first()
    
    if existing_box:
        # Only auto-update threshold if it hasn't been manually set to a different value
        # If the user has manually set a threshold, respect that choice
        # Only update if the current threshold is 0 or None (unset) or matches the old count
        current_threshold = existing_box.min_stock_threshold or 0
        # Only auto-update if threshold is unset (0/None) or if it exactly matches the old cable count
        # This prevents overriding user's manual threshold settings
        should_auto_update = (
            current_threshold == 0 or  # Unset - safe to auto-update
            current_threshold == matching_count  # Matches current count - safe to update
        )
        
        if should_auto_update and current_threshold != threshold:
            existing_box.min_stock_threshold = threshold
            db.commit()
            db.refresh(existing_box)
            logger.info(
                f"Updated storage box {box_name} (ID: {existing_box.id}) threshold to {threshold} "
                f"(based on {matching_count} cables of this type)"
            )
        elif not should_auto_update:
            logger.debug(
                f"Storage box {box_name} (ID: {existing_box.id}) has manually set threshold {current_threshold}, "
                f"not auto-updating to {threshold} (based on {matching_count} cables)"
            )
        
        # Auto-assign the cable to the box if it's not already assigned
        needs_commit = False
        if cable_asset.container_id is None:
            if cable_asset.status == AssetStatus.IN_STORAGE:
                cable_asset.container_id = existing_box.id
                needs_commit = True
                logger.info(
                    f"Auto-assigned cable {cable_asset.asset_tag} (ID: {cable_asset.id}) to existing storage box {box_name} (ID: {existing_box.id})"
                )
            else:
                # If status is not IN_STORAGE, set it and assign to box
                cable_asset.container_id = existing_box.id
                cable_asset.status = AssetStatus.IN_STORAGE
                needs_commit = True
                logger.info(
                    f"Auto-assigned cable {cable_asset.asset_tag} (ID: {cable_asset.id}) to existing storage box {box_name} (ID: {existing_box.id}) "
                    f"and set status to IN_STORAGE"
                )
        elif cable_asset.container_id != existing_box.id:
            # Cable is in a different box - check if it should be moved
            # Only auto-move if the current box doesn't match the cable's type
            current_box_query = db.query(Asset).filter(Asset.id == cable_asset.container_id)
            current_box_query = apply_tenant_filter(current_box_query, Asset)
            current_box = current_box_query.first()
            if current_box and generate_storage_box_name(cable_asset) != current_box.asset_tag:
                # Current box doesn't match - move to correct box
                cable_asset.container_id = existing_box.id
                if cable_asset.status != AssetStatus.IN_STORAGE:
                    cable_asset.status = AssetStatus.IN_STORAGE
                needs_commit = True
                logger.info(
                    f"Moved cable {cable_asset.asset_tag} (ID: {cable_asset.id}) from box {current_box.asset_tag} "
                    f"to correct box {box_name} (ID: {existing_box.id})"
                )
        
        if needs_commit:
            db.commit()
            db.refresh(cable_asset)
        
        return existing_box
    else:
        # Create new storage box
        from app.core.tenant import get_current_tenant_id
        
        tenant_id = get_current_tenant_id() or cable_asset.tenant_id
        if not tenant_id:
            logger.error("Cannot create storage box: no tenant context")
            return None
        
        # Generate proper serial number using the serial service
        from app.services.serial_service import generate_serial_number
        serial_number = generate_serial_number(db, "storage_box", tenant_id)

        new_box = Asset(
            asset_tag=box_name,  # Use descriptive box name as asset tag
            serial_number=serial_number,  # Use proper format: TYPE-TENANT-RANDOM-CHECK
            asset_type="storage_box",
            manufacturer="System",
            model="Storage Box",
            status=AssetStatus.ACTIVE,
            min_stock_threshold=threshold,
            description=f"Auto-generated storage box for {cable_asset.asset_type} cables (min threshold: {threshold}, based on {matching_count} existing cables)",
            tenant_id=tenant_id
        )
        
        db.add(new_box)
        db.commit()
        db.refresh(new_box)
        
        logger.info(
            f"Created new storage box {box_name} (ID: {new_box.id}) with threshold {threshold} "
            f"(based on {matching_count} cables of this type)"
        )
        
        # Auto-assign the cable to the box (same logic as existing box path)
        if cable_asset.container_id is None:
            if cable_asset.status == AssetStatus.IN_STORAGE:
                cable_asset.container_id = new_box.id
                logger.info(
                    f"Auto-assigned cable {cable_asset.asset_tag} (ID: {cable_asset.id}) to storage box {box_name} (ID: {new_box.id})"
                )
            else:
                # If status is not IN_STORAGE, set it and assign to box
                cable_asset.container_id = new_box.id
                cable_asset.status = AssetStatus.IN_STORAGE
                logger.info(
                    f"Auto-assigned cable {cable_asset.asset_tag} (ID: {cable_asset.id}) to storage box {box_name} (ID: {new_box.id}) "
                    f"and set status to IN_STORAGE"
                )
            db.commit()
            db.refresh(cable_asset)
        
        return new_box


def deploy_asset(db: Session, asset_id: int) -> Optional[Asset]:
    """
    Deploy an asset from storage to active use.
    
    This function implements the "Consume" workflow:
    1. If asset is IN_STORAGE and has a container_id, remove it from the container
    2. Set status to DEPLOYED
    3. Clear container_id
    4. Check stock levels of the old container
    
    Args:
        db: SQLAlchemy database session
        asset_id: ID of the asset to deploy
        
    Returns:
        Updated Asset object, or None if asset not found or not in storage
        
    Raises:
        NoResultFound: If asset doesn't exist
    """
    # Fetch the asset with tenant filtering
    query = db.query(Asset).filter(Asset.id == asset_id)
    query = apply_tenant_filter(query, Asset)
    asset = query.first()
    
    if not asset:
        raise NoResultFound(f"Asset with ID {asset_id} not found")
    
    # Only process if asset is in storage and has a container
    if asset.status != AssetStatus.IN_STORAGE or not asset.container_id:
        logger.debug(
            f"Asset {asset.asset_tag} (ID: {asset_id}) is not in storage "
            f"(status: {asset.status}, container_id: {asset.container_id}). Skipping deployment."
        )
        return asset
    
    # Store the old container ID for stock checking
    old_container_id = asset.container_id
    
    # Remove asset from container and mark as deployed
    asset.container_id = None
    asset.status = AssetStatus.DEPLOYED
    
    # Commit the change
    db.commit()
    db.refresh(asset)
    
    logger.info(
        f"Asset {asset.asset_tag} (ID: {asset_id}) deployed from container {old_container_id}. "
        f"Status changed: IN_STORAGE -> DEPLOYED"
    )
    
    # Check stock levels of the container it left
    check_stock_levels(db, old_container_id)
    
    return asset


def check_stock_levels(db: Session, container_id: int) -> bool:
    """
    DEPRECATED: Check stock levels for a storage container and trigger low stock alerts.
    
    This function is deprecated. Use get_container_stock_summary() from inventory_service instead.
    All storage containers should use StorageContainer model with ContainerStockThreshold records.
    
    This function is kept for backward compatibility but should not be used for new code.
    
    Args:
        db: SQLAlchemy database session
        container_id: ID of the StorageContainer to check (not Asset ID)
        
    Returns:
        True if stock is low (below threshold), False otherwise
    """
    # Use the new inventory service method
    from app.services.inventory_service import get_container_stock_summary
    
    summary = get_container_stock_summary(container_id, db, is_storage_container=True)
    if not summary:
        return False
    
    # Return is_low_stock status
    is_low_stock = summary.get('is_low_stock', False)
    
    # Log warnings for low stock items
    if is_low_stock:
        low_stock_types = summary.get('low_stock_types', [])
        for item_type in low_stock_types:
            display_name = f"{item_type.get('manufacturer', '')} {item_type.get('model', '')} {item_type.get('asset_type', '')}".strip()
            if not display_name:
                display_name = item_type.get('asset_type', 'Unknown Item Type')
            
            logger.warning(
                f"LOW STOCK ALERT: Container '{summary.get('container_name', 'Unknown')}' (ID: {container_id}) "
                f"has {item_type['count']} items of type '{display_name}' remaining "
                f"(minimum threshold: {item_type.get('min_threshold', 'N/A')}). Time to reorder!"
            )
            
            # Send email alert if enabled
            try:
                from app.models.storage_container import StorageContainer
                from app.services.alert_service import AlertService
                
                storage_container = db.query(StorageContainer).filter(
                    StorageContainer.id == container_id
                ).first()
                
                if storage_container:
                    alert_service = AlertService(db)
                    alert_service.send_low_stock_alert(
                        container=storage_container,
                        item_type_key=item_type.get("item_type_key", ""),
                        asset_type=item_type.get("asset_type", ""),
                        manufacturer=item_type.get("manufacturer"),
                        model=item_type.get("model"),
                        current_count=item_type['count'],
                        threshold=item_type.get('min_threshold', 'N/A')
                    )
            except Exception as e:
                logger.error(f"Error sending low stock email alert: {e}")
    
    if not is_low_stock:
        total_items = summary.get('total_items', 0)
        item_types = summary.get('item_types', [])
        logger.debug(
            f"Container '{summary.get('container_name', 'Unknown')}' (ID: {container_id}) stock level OK: "
            f"{total_items} total items across {len(item_types)} item types"
        )
    
    return is_low_stock


def bulk_assign_to_storage_boxes(
    db: Session,
    tenant_id: Optional[int] = None,
    dry_run: bool = False
) -> dict:
    """
    Bulk assign all unassigned cables to storage boxes.
    
    This function finds all cables (DAC, fiber, etc.) that are not yet assigned
    to a storage box and automatically assigns them using sync_storage_box_for_cable.
    
    Args:
        db: SQLAlchemy database session
        tenant_id: Tenant ID to process (uses current tenant if not provided)
        dry_run: If True, only log what would be done without making changes
        
    Returns:
        Dictionary with assignment statistics
    """
    from app.core.tenant import get_current_tenant_id, set_current_tenant_id
    
    # Set tenant context if provided
    original_tenant_id = None
    if tenant_id:
        original_tenant_id = get_current_tenant_id()
        set_current_tenant_id(tenant_id)
    else:
        tenant_id = get_current_tenant_id()
    
    if not tenant_id:
        logger.error("Cannot run bulk assignment: no tenant context")
        return {
            "assigned": 0,
            "skipped": 0,
            "errors": 0,
            "message": "No tenant context available"
        }
    
    try:
        # Find all unassigned cables in the tenant
        asset_type_lower = None  # Will match any cable type
        cable_types = ['dac_cable', 'fiber_cable', 'ethernet_cable', 'network_cable', 'power_cable']
        
        query = db.query(Asset).filter(
            Asset.tenant_id == tenant_id,
            Asset.container_id.is_(None),
            Asset.asset_type.in_(cable_types)
        )
        query = apply_tenant_filter(query, Asset)
        unassigned_cables = query.all()
        
        assigned_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        
        for cable in unassigned_cables:
            try:
                if dry_run:
                    # In dry-run mode, just check if we can generate a box name
                    box_name = generate_storage_box_name(cable)
                    if box_name:
                        logger.info(
                            f"[DRY RUN] Would assign cable {cable.asset_tag} (ID: {cable.id}) "
                            f"to storage box '{box_name}'"
                        )
                        assigned_count += 1
                    else:
                        logger.warning(
                            f"[DRY RUN] Would skip cable {cable.asset_tag} (ID: {cable.id}): "
                            f"Missing required fields for box name generation"
                        )
                        skipped_count += 1
                else:
                    # Actually assign the cable
                    box = sync_storage_box_for_cable(db, cable)
                    if box:
                        assigned_count += 1
                        logger.info(
                            f"Assigned cable {cable.asset_tag} (ID: {cable.id}) "
                            f"to storage box {box.asset_tag} (ID: {box.id})"
                        )
                    else:
                        skipped_count += 1
                        logger.warning(
                            f"Skipped cable {cable.asset_tag} (ID: {cable.id}): "
                            f"Could not create/find storage box"
                        )
            except Exception as e:
                error_count += 1
                error_msg = f"Cable {cable.asset_tag} (ID: {cable.id}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        result = {
            "assigned": assigned_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_processed": len(unassigned_cables),
            "message": f"{'Would assign' if dry_run else 'Assigned'} {assigned_count} cable(s) to storage boxes"
        }
        
        if errors:
            result["error_details"] = errors[:10]  # Limit to first 10 errors
        
        return result
        
    finally:
        # Restore original tenant context
        if original_tenant_id is not None:
            set_current_tenant_id(original_tenant_id)
        elif tenant_id and original_tenant_id is None:
            # Clear tenant context if we set it and there wasn't one before
            from app.core.tenant import clear_tenant_id
            clear_tenant_id()
