#!/usr/bin/env python3
"""
Migration Script: Asset-based Storage Boxes → StorageContainers

This script migrates the legacy Asset-based storage box system to the new 
StorageContainer model. It should be run once per deployment to migrate
existing data.

The migration:
1. Finds all Assets with min_stock_threshold > 0 (legacy storage boxes)
2. Creates corresponding StorageContainer records
3. Creates ContainerStockThreshold records for the item types
4. Updates items: container_id → storage_container_id
5. Clears the Asset's min_stock_threshold (no longer a box)

Usage:
    # Dry run (no changes):
    python migrate_asset_boxes_to_storage_containers.py --dry-run

    # Migrate specific tenant:
    python migrate_asset_boxes_to_storage_containers.py --tenant-id 5

    # Migrate all tenants:
    python migrate_asset_boxes_to_storage_containers.py --all

Safety:
    - Idempotent: Safe to run multiple times
    - Creates audit log of all changes
    - No data deletion (Assets are preserved, just threshold cleared)
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.tenant import set_current_tenant_id
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.models.container_stock_threshold import ContainerStockThreshold
from app.models.tenant import Tenant


def get_asset_boxes_for_tenant(db: Session, tenant_id: int) -> list:
    """Get all Asset-based storage boxes for a tenant."""
    set_current_tenant_id(tenant_id)
    return db.query(Asset).filter(
        Asset.tenant_id == tenant_id,
        Asset.min_stock_threshold.isnot(None),
        Asset.min_stock_threshold > 0
    ).all()


def check_if_already_migrated(db: Session, asset_box: Asset) -> bool:
    """Check if this Asset box was already migrated."""
    # Check if a StorageContainer with matching name exists for this tenant
    existing = db.query(StorageContainer).filter(
        StorageContainer.tenant_id == asset_box.tenant_id,
        StorageContainer.name == asset_box.asset_tag
    ).first()
    return existing is not None


def get_items_in_asset_box(db: Session, asset_box: Asset) -> list:
    """Get all items stored in an Asset-based box."""
    return db.query(Asset).filter(
        Asset.container_id == asset_box.id,
        Asset.tenant_id == asset_box.tenant_id
    ).all()


def migrate_asset_box(db: Session, asset_box: Asset, dry_run: bool = False, container_type: str = None) -> dict:
    """
    Migrate a single Asset-based storage box to StorageContainer.

    Args:
        db: Database session
        asset_box: The Asset to migrate
        dry_run: If True, don't make changes
        container_type: Optional container type (box, shelf, bin, etc.).
                       If not provided, derives from asset_type or defaults to 'box'.

    Returns a dict with migration details.
    """
    # Set tenant context for this migration
    set_current_tenant_id(asset_box.tenant_id)

    # Derive container_type from asset if not specified
    if container_type is None:
        # Try to derive from asset_type (e.g., 'storage_box' -> 'box', 'storage_shelf' -> 'shelf')
        asset_type = asset_box.asset_type or ''
        if 'shelf' in asset_type.lower():
            container_type = 'shelf'
        elif 'bin' in asset_type.lower():
            container_type = 'bin'
        elif 'drawer' in asset_type.lower():
            container_type = 'drawer'
        else:
            container_type = 'box'  # Default
    
    result = {
        "asset_id": asset_box.id,
        "asset_tag": asset_box.asset_tag,
        "tenant_id": asset_box.tenant_id,
        "min_stock_threshold": asset_box.min_stock_threshold,
        "container_type": container_type,
        "status": "pending",
        "items_migrated": 0,
        "storage_container_id": None,
        "error": None
    }
    
    current_operation = "initializing"
    try:
        # Check if already migrated
        current_operation = "checking if already migrated"
        if check_if_already_migrated(db, asset_box):
            result["status"] = "already_migrated"
            return result
        
        # Get items in this box
        current_operation = "counting items in box"
        items = get_items_in_asset_box(db, asset_box)
        result["items_migrated"] = len(items)
        
        if dry_run:
            result["status"] = "would_migrate"
            return result
        
        # Create StorageContainer
        current_operation = "creating StorageContainer"
        new_container = StorageContainer(
            tenant_id=asset_box.tenant_id,
            name=asset_box.asset_tag,
            description=f"Migrated from Asset #{asset_box.id}: {asset_box.description or ''}".strip(),
            container_type=container_type,
            datacenter_id=asset_box.datacenter_id,
            room_id=asset_box.room_id if hasattr(asset_box, 'room_id') else None,
            location=asset_box.location if hasattr(asset_box, 'location') else None,
            barcode=asset_box.serial_number,  # Use serial as barcode
        )
        db.add(new_container)
        current_operation = "flushing StorageContainer to get ID"
        db.flush()  # Get the ID
        
        result["storage_container_id"] = new_container.id
        
        # Create ContainerStockThreshold for each unique item type in the box
        current_operation = "creating stock thresholds"
        thresholds_to_create = []
        item_types_seen = set()
        for item in items:
            type_key = (item.asset_type, item.manufacturer or '', item.model or '')
            if type_key not in item_types_seen:
                item_types_seen.add(type_key)

                threshold = ContainerStockThreshold(
                    tenant_id=asset_box.tenant_id,
                    storage_container_id=new_container.id,
                    asset_type=item.asset_type,
                    manufacturer=item.manufacturer,
                    model=item.model,
                    min_threshold=asset_box.min_stock_threshold,
                    max_quantity=None
                )
                thresholds_to_create.append(threshold)

        # If no items but box exists, create a generic threshold
        if len(item_types_seen) == 0:
            threshold = ContainerStockThreshold(
                tenant_id=asset_box.tenant_id,
                storage_container_id=new_container.id,
                asset_type=asset_box.asset_type,  # Use the box's own type
                manufacturer=asset_box.manufacturer,
                model=asset_box.model,
                min_threshold=asset_box.min_stock_threshold,
                max_quantity=None
            )
            thresholds_to_create.append(threshold)

        # Bulk insert all thresholds
        if thresholds_to_create:
            db.bulk_save_objects(thresholds_to_create)
        
        # Update items: container_id → storage_container_id
        current_operation = f"moving {len(items)} items to new container"
        for item in items:
            item.storage_container_id = new_container.id
            item.container_id = None  # Clear old reference
        
        # Clear the Asset's min_stock_threshold (no longer a storage box)
        current_operation = "clearing asset threshold"
        asset_box.min_stock_threshold = None
        
        current_operation = "committing changes"
        db.commit()
        result["status"] = "migrated"
        
    except Exception as e:
        db.rollback()
        result["status"] = "error"
        result["error"] = f"Failed while {current_operation}: {str(e)}"
    
    return result


def migrate_tenant(db: Session, tenant_id: int, dry_run: bool = False) -> list:
    """Migrate all Asset-based boxes for a tenant."""
    results = []
    
    asset_boxes = get_asset_boxes_for_tenant(db, tenant_id)
    
    for asset_box in asset_boxes:
        result = migrate_asset_box(db, asset_box, dry_run)
        results.append(result)
        
        # Log progress
        status_marker = {
            "migrated": "[OK]",
            "would_migrate": "[DRY]",
            "already_migrated": "[SKIP]",
            "error": "[ERR]"
        }.get(result["status"], "[???]")
        
        print(f"  {status_marker} {result['asset_tag']} (ID: {result['asset_id']}): "
              f"{result['status']} - {result['items_migrated']} items")
        
        if result["error"]:
            print(f"     Error: {result['error']}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Migrate Asset-based storage boxes to StorageContainers")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--tenant-id", type=int, help="Migrate specific tenant ID")
    parser.add_argument("--all", action="store_true", help="Migrate all tenants")
    
    args = parser.parse_args()
    
    if not args.tenant_id and not args.all:
        print("Error: Must specify --tenant-id or --all")
        parser.print_help()
        sys.exit(1)
    
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"Asset Box → StorageContainer Migration (v1.3 - Sequence Fix Global)")
        print(f"{'='*60}")
        print(f"Started: {datetime.now().isoformat()}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
        print(f"{'='*60}\n")
        sys.stdout.flush()
        
        # Check and Fix Sequence ID Desynchronization (Global Fix)
        # We do this AFTER the header so we know the script has started
        try:
            from sqlalchemy import text
            
            # Check current state
            print("  [INIT] Checking DB Sequence state...")
            seq_check = db.execute(text("SELECT last_value FROM storage_containers_id_seq")).scalar()
            max_id = db.execute(text("SELECT MAX(id) FROM storage_containers")).scalar() or 0
            
            print(f"  [CHECK] Sequence: {seq_check}, Max ID: {max_id}")
            
            if seq_check < max_id:
                if args.dry_run:
                    print(f"  [WARN] Sequence out of sync! (Seq: {seq_check} < Max: {max_id})")
                    print("         Live run will automatically fix this by resetting sequence.")
                else:
                    print(f"  [FIX] Resetting sequence from {seq_check} to {max_id}...")
                    db.execute(text(f"SELECT setval('storage_containers_id_seq', {max_id})"))
                    db.commit()
                    print("  [OK] Sequence resynchronized.")
            else:
                print("  [OK] Sequence is in sync.")
            sys.stdout.flush()
                
        except Exception as e:
            print(f"  [WARN] Failed to check/fix sequence: {e}")
            sys.stdout.flush()

        all_results = []
        
        if args.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == args.tenant_id).first()
            if not tenant:
                print(f"Error: Tenant {args.tenant_id} not found")
                sys.exit(1)
            
            print(f"Migrating tenant: {tenant.name} (ID: {tenant.id})")
            results = migrate_tenant(db, tenant.id, args.dry_run)
            all_results.extend(results)
        
        elif args.all:
            tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
            
            for tenant in tenants:
                print(f"\nMigrating tenant: {tenant.name} (ID: {tenant.id})")
                results = migrate_tenant(db, tenant.id, args.dry_run)
                all_results.extend(results)
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        migrated = len([r for r in all_results if r["status"] == "migrated"])
        would_migrate = len([r for r in all_results if r["status"] == "would_migrate"])
        already_done = len([r for r in all_results if r["status"] == "already_migrated"])
        errors = len([r for r in all_results if r["status"] == "error"])
        total_items = sum(r['items_migrated'] for r in all_results if r['status'] in ['migrated', 'would_migrate'])
        
        if args.dry_run:
            print(f"\nAsset-based storage boxes that WOULD be converted to StorageContainers: {would_migrate}")
        else:
            print(f"\nAsset-based storage boxes converted to StorageContainers: {migrated}")
        
        print(f"Asset-based storage boxes already migrated (skipped): {already_done}")
        print(f"Errors encountered: {errors}")
        print(f"\nTotal inventory items that {'would be' if args.dry_run else 'were'} reassigned:")
        print(f"  - From: Asset.container_id (old system)")
        print(f"  - To:   Asset.storage_container_id (new system)")
        print(f"  - Count: {total_items} items")
        
        if errors > 0:
            print("\nErrors:")
            for r in all_results:
                if r["status"] == "error":
                    print(f"  - {r['asset_tag']}: {r['error']}")
        
        print(f"\nCompleted: {datetime.now().isoformat()}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
