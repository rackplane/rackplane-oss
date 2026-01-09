
import pytest
import os
import sys
from sqlalchemy.orm import Session
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.core.tenant import set_current_tenant_id

from scripts.migrate_asset_boxes_to_storage_containers import migrate_tenant

@pytest.mark.integration
@pytest.mark.regression
def test_storage_migration_logic(db_session: Session):
    """
    Test the migration logic:
    1. Create a dummy Asset acting as a storage box (min_stock_threshold > 0)
    2. Create dummy items inside it (container_id = asset.id)
    3. Run migration function (dry run and live)
    4. Verify StorageContainer created and items moved.
    """
    db = db_session
    # Setup - Tenant 1
    tenant_id = 1
    set_current_tenant_id(tenant_id)

    import time
    unique_id = int(time.time())
    
    # 1. Create Storage Box Asset
    box = Asset(
        tenant_id=tenant_id,
        asset_tag=f"TEST-BOX-REGRESSION-{unique_id}",
        status=AssetStatus.ACTIVE,
        model="Test Box Regression",
        min_stock_threshold=5, # This makes it a storage box
        asset_type="storage_box",
        serial_number=f"SN-TEST-BOX-{unique_id}"
    )
    db.add(box)
    db.commit()
    db.refresh(box)
    
    # 2. Create Item inside Box
    item = Asset(
        tenant_id=tenant_id,
        asset_tag=f"TEST-ITEM-REGRESSION-{unique_id}",
        status=AssetStatus.IN_STORAGE,
        model="Test Item Regression",
        container_id=box.id, # Legacy location
        asset_type="server_component",
        serial_number=f"SN-TEST-ITEM-{unique_id}"
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Verify setup
    assert box.min_stock_threshold == 5
    assert item.container_id == box.id
    assert item.storage_container_id is None

    # 3. Run Migration (Live)
    migrate_tenant(db, tenant_id, dry_run=False)
    
    # 4. Refresh & Verify
    db.expire_all() # Force refresh
    
    box_refreshed = db.query(Asset).filter(Asset.id == box.id).first()
    item_refreshed = db.query(Asset).filter(Asset.id == item.id).first()
    
    # Box should be 'cleared' of being a box (min_stock_threshold None)
    # The script sets it to None
    assert box_refreshed.min_stock_threshold is None 
    
    # New StorageContainer should exist with same name
    new_container = db.query(StorageContainer).filter(StorageContainer.name == f"TEST-BOX-REGRESSION-{unique_id}").first()
    assert new_container is not None
    assert new_container.tenant_id == tenant_id
    
    # Item should be moved
    assert item_refreshed.container_id is None
    assert item_refreshed.storage_container_id == new_container.id
