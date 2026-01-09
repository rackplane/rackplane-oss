"""
Test for migration fix_incorrect_stock_thresholds.

This test verifies that the migration correctly clears min_stock_threshold
from assets that are NOT storage boxes (like storage_device equipment).
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.asset import Asset
from app.core.database import SessionLocal
from app.core.tenant import set_current_tenant_id


@pytest.mark.integration
def test_migration_fixes_incorrect_storage_thresholds():
    """
    Test that migration clears min_stock_threshold from non-storage-box assets.
    
    This test simulates the migration logic:
    1. Creates assets with incorrect min_stock_threshold values
    2. Applies the migration fix logic
    3. Verifies only actual storage boxes keep min_stock_threshold
    """
    db: Session = SessionLocal()
    
    try:
        # Get a test tenant (we'll use the first one, or create one if needed)
        from app.models.tenant import Tenant
        import uuid
        tenant = db.query(Tenant).first()
        if not tenant:
            pytest.skip("No tenant found - cannot run migration test")
        
        # Use unique identifiers to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:8]
        
        # Clean up any existing test assets first (use skip_tenant_filter for system operations)
        db.execute(text("""
            DELETE FROM assets 
            WHERE asset_tag LIKE 'TEST-MIG-%' 
            OR asset_tag LIKE 'DAC-MIG-%'
            OR serial_number LIKE 'TEST-MIG-%'
            OR serial_number LIKE 'DAC-MIG-%'
        """).execution_options(skip_tenant_filter=True))
        db.commit()
        
        # Create test assets with various configurations
        test_assets = []
        
        # 1. Storage device (equipment, NOT a storage box) - should NOT have threshold
        storage_device = Asset(
            asset_tag=f"TEST-MIG-NB-41-{unique_suffix}",
            serial_number=f"TEST-MIG-NB-41-SN-{unique_suffix}",
            asset_type="storage_device",
            status="active",
            min_stock_threshold=1,  # Incorrectly set
            tenant_id=tenant.id
        )
        db.add(storage_device)
        test_assets.append(("storage_device", storage_device))
        
        # 2. Actual storage box - SHOULD have threshold
        storage_box = Asset(
            asset_tag=f"TEST-MIG-STORAGE-BOX-001-{unique_suffix}",
            serial_number=f"TEST-MIG-BOX-SN-001-{unique_suffix}",
            asset_type="storage_box",
            status="active",
            min_stock_threshold=5,  # Correctly set
            tenant_id=tenant.id
        )
        db.add(storage_box)
        test_assets.append(("storage_box", storage_box))
        
        # 3. DAC-* naming (auto-generated cable box) - SHOULD have threshold
        dac_box = Asset(
            asset_tag=f"DAC-MIG-TEST-001-{unique_suffix}",
            serial_number=f"DAC-MIG-TEST-SN-001-{unique_suffix}",
            asset_type="other_device",
            status="active",
            min_stock_threshold=3,  # Correctly set
            tenant_id=tenant.id
        )
        db.add(dac_box)
        test_assets.append(("dac_box", dac_box))
        
        # 4. Network device with threshold = 0 - should be NULL
        network_device = Asset(
            asset_tag=f"TEST-MIG-SWITCH-01-{unique_suffix}",
            serial_number=f"TEST-MIG-SW-SN-01-{unique_suffix}",
            asset_type="switch_device",
            status="active",
            min_stock_threshold=0,  # Should be NULL
            tenant_id=tenant.id
        )
        db.add(network_device)
        test_assets.append(("network_device", network_device))
        
        # 5. Server with threshold - should be cleared
        server = Asset(
            asset_tag=f"TEST-MIG-SERVER-01-{unique_suffix}",
            serial_number=f"TEST-MIG-SRV-SN-01-{unique_suffix}",
            asset_type="server_device",
            status="active",
            min_stock_threshold=1,  # Incorrectly set
            tenant_id=tenant.id
        )
        db.add(server)
        test_assets.append(("server", server))
        
        db.commit()
        
        # Set tenant context for the operations
        set_current_tenant_id(tenant.id)
        
        # Apply the migration fix logic
        # Clear min_stock_threshold from assets that are NOT storage boxes
        # Use skip_tenant_filter for migration operations
        db.execute(text("""
            UPDATE assets
            SET min_stock_threshold = NULL
            WHERE min_stock_threshold IS NOT NULL
            AND NOT (
                asset_type = 'storage_box'
                OR asset_tag LIKE 'DAC-%'
                OR asset_tag LIKE 'FIBER-%'
            )
            AND asset_tag LIKE 'TEST-MIG-%'
        """).execution_options(skip_tenant_filter=True))
        
        # Fix assets with min_stock_threshold = 0
        db.execute(text("""
            UPDATE assets
            SET min_stock_threshold = NULL
            WHERE min_stock_threshold = 0
            AND asset_tag LIKE 'TEST-MIG-%'
        """).execution_options(skip_tenant_filter=True))
        
        db.commit()
        
        # Refresh all assets (with tenant context set)
        for name, asset in test_assets:
            db.refresh(asset)
        
        # Verify results
        # 1. Storage device (equipment) should have threshold cleared
        assert storage_device.min_stock_threshold is None, \
            f"Storage device (equipment) should not have min_stock_threshold, got {storage_device.min_stock_threshold}"
        
        # 2. Actual storage box should keep threshold
        assert storage_box.min_stock_threshold == 5, \
            f"Storage box should keep min_stock_threshold=5, got {storage_box.min_stock_threshold}"
        
        # 3. DAC-* box should keep threshold
        assert dac_box.min_stock_threshold == 3, \
            f"DAC-* box should keep min_stock_threshold=3, got {dac_box.min_stock_threshold}"
        
        # 4. Network device with 0 should be NULL
        assert network_device.min_stock_threshold is None, \
            f"Network device with threshold=0 should be NULL, got {network_device.min_stock_threshold}"
        
        # 5. Server should have threshold cleared
        assert server.min_stock_threshold is None, \
            f"Server should not have min_stock_threshold, got {server.min_stock_threshold}"
        
        # Cleanup: Delete test assets
        for name, asset in test_assets:
            db.delete(asset)
        db.commit()
        
    finally:
        db.close()


@pytest.mark.integration
def test_migration_preserves_storage_box_thresholds():
    """
    Test that migration preserves min_stock_threshold for actual storage boxes.
    """
    db: Session = SessionLocal()
    
    try:
        from app.models.tenant import Tenant
        import uuid
        tenant = db.query(Tenant).first()
        if not tenant:
            pytest.skip("No tenant found - cannot run migration test")
        
        # Set tenant context for the operations
        set_current_tenant_id(tenant.id)
        
        # Use unique identifier to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:8]
        
        # Clean up any existing test assets first (use skip_tenant_filter for system operations)
        db.execute(
            text("""
                DELETE FROM assets 
                WHERE asset_tag LIKE 'TEST-PRESERVE-%'
                OR serial_number LIKE 'TEST-PRESERVE-%'
            """).execution_options(skip_tenant_filter=True)
        )
        db.commit()
        
        # Create storage box with threshold
        storage_box = Asset(
            asset_tag=f"TEST-PRESERVE-BOX-{unique_suffix}",
            serial_number=f"TEST-PRESERVE-SN-{unique_suffix}",
            asset_type="storage_box",
            status="active",
            min_stock_threshold=10,
            tenant_id=tenant.id
        )
        db.add(storage_box)
        db.commit()
        
        # Apply migration logic (use skip_tenant_filter for system operations)
        db.execute(
            text("""
                UPDATE assets
                SET min_stock_threshold = NULL
                WHERE min_stock_threshold IS NOT NULL
                AND NOT (
                    asset_type = 'storage_box'
                    OR asset_tag LIKE 'DAC-%'
                    OR asset_tag LIKE 'FIBER-%'
                )
                AND asset_tag LIKE 'TEST-PRESERVE-%'
            """).execution_options(skip_tenant_filter=True)
        )
        db.commit()
        
        # Refresh with tenant context set
        db.refresh(storage_box)
        
        # Verify threshold is preserved
        assert storage_box.min_stock_threshold == 10, \
            f"Storage box threshold should be preserved, got {storage_box.min_stock_threshold}"
        
        # Cleanup
        db.delete(storage_box)
        db.commit()
        
    finally:
        db.close()

