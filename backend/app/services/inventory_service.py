# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Inventory Service
Handles stock level checking and low stock alerts for StorageContainers
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.core.tenant_query import apply_tenant_filter

logger = logging.getLogger(__name__)


def check_low_stock(container_id: int, db: Session) -> None:
    """
    Checks if a storage container has fallen below its minimum threshold.
    Creates a notification/log if stock is low.
    """
    # Get the Container (e.g., "Cat6 Cable Bin")
    container_query = db.query(Asset).filter(Asset.id == container_id)
    container_query = apply_tenant_filter(container_query, Asset)
    container = container_query.first()
    
    if not container or container.min_stock_threshold is None:
        return
    
    # Count items currently inside this container
    # Only count items with status IN_STORAGE to get accurate stock counts
    # Items that are DEPLOYED or in other statuses should not be counted as "in stock"
    items_query = db.query(Asset).filter(
        Asset.container_id == container_id,
        Asset.status == AssetStatus.IN_STORAGE  # Only count items actually in storage
    )
    items_query = apply_tenant_filter(items_query, Asset)
    current_count = items_query.count()
    
    # Trigger Alert if needed
    if current_count < container.min_stock_threshold:
        logger.warning(
            f"LOW STOCK ALERT: {container.asset_tag} ({container.model or 'N/A'}) "
            f"is low on stock! Current: {current_count}, Minimum: {container.min_stock_threshold}"
        )
        
        # Create a System Notification (for future implementation)
        # For MVP, we'll just log it. You can extend this to:
        # - Create a notification record in a notifications table
        # - Send an email
        # - Create a purchase order draft
        # - Update a dashboard alert
        
        # TODO: Implement notification system
        # create_notification(
        #     tenant_id=container.tenant_id,
        #     title="Low Stock Alert",
        #     message=f"Time to reorder items for {container.asset_tag}. Only {current_count} remaining (minimum: {container.min_stock_threshold})."
        # )


def get_container_stock_info(container_id: int, db: Session) -> dict:
    """
    Get current stock count and status for a container.
    Returns: {
        'current_count': int,
        'min_threshold': int,
        'is_low_stock': bool,
        'container_name': str
    }
    """
    container_query = db.query(Asset).filter(Asset.id == container_id)
    container_query = apply_tenant_filter(container_query, Asset)
    container = container_query.first()
    
    if not container:
        return None
    
    # Count items in container
    # Only count items with status IN_STORAGE to get accurate stock counts
    # Items that are DEPLOYED or in other statuses should not be counted as "in stock"
    items_query = db.query(Asset).filter(
        Asset.container_id == container_id,
        Asset.status == AssetStatus.IN_STORAGE  # Only count items actually in storage
    )
    items_query = apply_tenant_filter(items_query, Asset)
    current_count = items_query.count()
    
    min_threshold = container.min_stock_threshold or 0
    is_low_stock = current_count < min_threshold if min_threshold > 0 else False
    
    return {
        'current_count': current_count,
        'min_threshold': min_threshold,
        'is_low_stock': is_low_stock,
        'container_name': container.asset_tag,
        'container_id': container_id
    }


def get_stock_by_item_type(container_id: int, db: Session, is_storage_container: bool = True) -> List[Dict]:
    """
    Get stock levels grouped by item type (manufacturer + model + asset_type).
    This is the correct way to track stock - items are grouped by their type,
    not by their unique asset_tag.
    
    Args:
        container_id: The ID of the container (StorageContainer.id or Asset.id for legacy boxes)
        db: SQLAlchemy database session
        is_storage_container: True if container_id refers to a StorageContainer, False for Asset-based box
    
    Returns: [
        {
            'item_type_key': str,  # Combination of asset_type|manufacturer|model
            'asset_type': str,
            'manufacturer': str,
            'model': str,
            'count': int,  # Number of items of this type in the container
            'items': List[Dict]  # List of actual item IDs and tags
        },
        ...
    ]
    """
    # Verify container exists
    if is_storage_container:
        container_query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
        container_query = apply_tenant_filter(container_query, StorageContainer)
        container = container_query.first()
    else:
        # Legacy: Asset-based storage box
        container_query = db.query(Asset).filter(Asset.id == container_id)
        container_query = apply_tenant_filter(container_query, Asset)
        container = container_query.first()
    
    if not container:
        return []
    
    # Get all items in this container
    # Only count items with status IN_STORAGE to get accurate stock counts
    # Items that are DEPLOYED or in other statuses should not be counted as "in stock"
    if is_storage_container:
        items_query = db.query(Asset).filter(
            Asset.storage_container_id == container_id,
            Asset.status == AssetStatus.IN_STORAGE  # Only count items actually in storage
        )
    else:
        # Legacy: Asset-based storage box
        items_query = db.query(Asset).filter(
            Asset.container_id == container_id,
            Asset.status == AssetStatus.IN_STORAGE  # Only count items actually in storage
        )
    items_query = apply_tenant_filter(items_query, Asset)
    items = items_query.all()
    
    # Group items by type (asset_type + manufacturer + model)
    # Use a normalized key to handle None values
    type_groups: Dict[str, Dict] = defaultdict(lambda: {
        'asset_type': None,
        'manufacturer': None,
        'model': None,
        'count': 0,
        'items': []
    })
    
    for item in items:
        # Create a normalized key for grouping
        # Handle None values by converting to empty string
        asset_type = item.asset_type or ''
        manufacturer = (item.manufacturer or '').strip()
        model = (item.model or '').strip()
        
        # Get quantity from custom_fields if present, otherwise default to 1
        quantity = 1
        if item.custom_fields and isinstance(item.custom_fields, dict):
            quantity = item.custom_fields.get('quantity', 1)
            # Ensure quantity is a valid positive integer
            try:
                quantity = max(1, int(quantity))
            except (ValueError, TypeError):
                quantity = 1
        
        # Create a unique key for this item type
        type_key = f"{asset_type}|{manufacturer}|{model}"
        
        # Initialize group if first item of this type
        if type_key not in type_groups:
            type_groups[type_key] = {
                'item_type_key': type_key,
                'asset_type': asset_type,
                'manufacturer': manufacturer,
                'model': model,
                'count': 0,
                'items': []
            }
        
        # Add this item to the group, accounting for quantity
        type_groups[type_key]['count'] += quantity
        type_groups[type_key]['items'].append({
            'id': item.id,
            'asset_tag': item.asset_tag,
            'serial_number': item.serial_number,
            'status': item.status.value if hasattr(item.status, 'value') else str(item.status),
            'description': item.description or None,
            'quantity': quantity  # Include quantity in item details
        })
    
    # Convert to list and sort by count (descending)
    result = list(type_groups.values())
    result.sort(key=lambda x: x['count'], reverse=True)
    
    return result


def get_container_stock_summary(container_id: int, db: Session, is_storage_container: bool = True) -> dict:
    """
    Get a comprehensive stock summary for a container, including:
    - Total item count
    - Stock levels grouped by item type
    - Low stock alerts per item type (if min_threshold is set on container)
    
    Args:
        container_id: The ID of the container (StorageContainer.id or Asset.id for legacy boxes)
        db: SQLAlchemy database session
        is_storage_container: True if container_id refers to a StorageContainer, False for Asset-based box
    
    Returns: {
        'container_id': int,
        'container_name': str,
        'min_threshold': int,  # Global threshold for the container
        'total_items': int,  # Total count of all items
        'item_types': List[Dict],  # Stock levels by item type
        'low_stock_types': List[Dict]  # Item types below threshold (if applicable)
        'is_low_stock': bool  # Whether the container is below threshold
    }
    """
    # Get container (only StorageContainer is supported now, no legacy Asset-based boxes)
    if not is_storage_container:
        # Legacy Asset-based storage boxes are no longer supported
        # All storage containers should use StorageContainer model
        return None
    
    container_query = db.query(StorageContainer).filter(StorageContainer.id == container_id)
    container_query = apply_tenant_filter(container_query, StorageContainer)
    container = container_query.first()
    container_name = container.name if container else "Unknown"
    # Note: min_threshold is now per-item-type via ContainerStockThreshold, not on container itself
    min_threshold = 0  # Legacy field, not used anymore
    
    if not container:
        return None
    
    # Get stock by item type
    stock_by_type = get_stock_by_item_type(container_id, db, is_storage_container)
    
    total_items = sum(item_type['count'] for item_type in stock_by_type)
    
    # Check per-item-type thresholds if this is a StorageContainer
    from app.models.container_stock_threshold import ContainerStockThreshold
    
    low_stock_types = []
    if is_storage_container:
        # Get all thresholds for this container
        thresholds_query = db.query(ContainerStockThreshold).filter(
            ContainerStockThreshold.storage_container_id == container_id
        )
        thresholds_query = apply_tenant_filter(thresholds_query, ContainerStockThreshold)
        thresholds = thresholds_query.all()
        
        # Create a lookup map: (asset_type, manufacturer, model) -> threshold
        threshold_map = {}
        for threshold in thresholds:
            # Normalize None to empty string for matching
            key = (
                threshold.asset_type or '',
                (threshold.manufacturer or '').strip(),
                (threshold.model or '').strip()
            )
            threshold_map[key] = {
                'min': threshold.min_threshold,
                'max': threshold.max_quantity
            }
        
        # Check each item type against its specific threshold
        for item_type in stock_by_type:
            # Normalize for matching
            item_key = (
                item_type['asset_type'] or '',
                (item_type['manufacturer'] or '').strip(),
                (item_type['model'] or '').strip()
            )
            
            # Get threshold for this item type (check if it exists in threshold_map)
            # If it exists in the map, use it (even if 0, which means "no threshold")
            # If it doesn't exist, there's no threshold for this item type
            # Get threshold for this item type
            min_threshold = None
            max_quantity = None
            
            if item_key in threshold_map:
                min_threshold = threshold_map[item_key]['min']
                max_quantity = threshold_map[item_key]['max']
            
            # Set min_threshold if set (>0)
            if min_threshold is not None and min_threshold > 0:
                item_type['min_threshold'] = min_threshold
            else:
                item_type['min_threshold'] = None
                
            # Set max_quantity if set (>0)
            if max_quantity is not None and max_quantity > 0:
                item_type['max_quantity'] = max_quantity
            else:
                item_type['max_quantity'] = None
            
            # If threshold is set (> 0) and count is below threshold, mark as low stock
            if min_threshold is not None and min_threshold > 0 and item_type['count'] < min_threshold:
                low_stock_types.append(item_type)
    
    # Calculate is_low_stock:
    # - If any item types are below their specific threshold, it's low stock
    # - Only use ContainerStockThreshold records (no legacy Asset.min_stock_threshold fallback)
    is_low_stock = len(low_stock_types) > 0
    
    return {
        'container_id': container_id,
        'container_name': container_name,
        'min_threshold': min_threshold,
        'total_items': total_items,
        'item_types': stock_by_type,
        'low_stock_types': low_stock_types,
        'is_low_stock': is_low_stock
    }
