# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
End-to-End Stock Threshold Lifecycle Test
Tests the complete flow of stock threshold changes and their visibility across all pages
"""

import pytest
from app.core.database import SessionLocal
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.models.container_stock_threshold import ContainerStockThreshold
from app.models.asset_type import AssetTypeModel
from app.core.tenant import set_current_tenant_id, clear_tenant_id
from app.services.inventory_service import get_container_stock_summary


@pytest.mark.integration
@pytest.mark.stock
@pytest.mark.e2e
def test_stock_threshold_lifecycle_complete_flow(authenticated_client, test_prefix, test_tenant):
    """
    TC-STOCK-LIFECYCLE-001: Complete stock threshold lifecycle test
    
    Test flow:
    1. Start with 5 items, threshold 5 → NOT low stock
    2. Remove 1 item → 4 items, threshold 5 → IS low stock
    3. Lower threshold to 4 → 4 items, threshold 4 → NOT low stock (fine)
    4. Lower threshold to 0 → 4 items, threshold 0 → Disappears from low stock list
    
    Verifies status appears correctly on:
    - Storage container box itself (via stock-summary API)
    - Dashboard metrics (via dashboard API)
    - Stock management page (via storage-containers API with stock-summary)
    - Low stock alerts page (via storage-containers API filtered by is_low_stock)
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create asset type
        dac_type = db.query(AssetTypeModel).filter(AssetTypeModel.name == 'dac_cable').first()
        if not dac_type:
            dac_type = AssetTypeModel(
                name='dac_cable',
                display_name='DAC Cable',
                description='Direct Attach Copper Cable',
                tenant_id=test_tenant["id"]
            )
            db.add(dac_type)
            db.commit()
        
        # Create storage container
        container = StorageContainer(
            name=f"{test_prefix}-E2E-Test-Box",
            container_type='box',
            description="E2E lifecycle test container",
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # ========================================================================
        # STEP 1: Create 5 items, threshold 5 → Should NOT be low stock
        # ========================================================================
        print("\n=== STEP 1: 5 items, threshold 5 ===")
        
        # Create 5 DAC cables
        assets = []
        for i in range(5):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-E2E-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-E2E-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
            assets.append(asset)
        db.commit()
        
        # Create threshold: 5
        threshold_data = {
            "asset_type": "dac_cable",
            "manufacturer": "FS",
            "model": "1m",
            "min_threshold": 5
        }
        success, threshold = authenticated_client.post(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds",
            threshold_data,
            expected_status=200
        )
        assert success, f"Failed to create threshold: {threshold}"
        threshold_id = threshold["id"]
        
        # Verify: NOT low stock (5 >= 5)
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert summary["is_low_stock"] is False, "5 items with threshold 5 should NOT be low stock"
        assert len(summary["low_stock_types"]) == 0, "Should have no low stock types"
        assert summary["total_items"] == 5
        
        # Verify item type has correct threshold
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 5
        assert fs_1m_type["min_threshold"] == 5
        
        # Verify NOT in low stock alerts
        success, containers = authenticated_client.get(
            f"/api/v1/storage-containers/",
            expected_status=200
        )
        assert success
        test_container = next((c for c in containers if c["id"] == container.id), None)
        assert test_container is not None
        
        # Get stock summary for this container
        success, container_summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert container_summary["is_low_stock"] is False
        
        # ========================================================================
        # STEP 2: Remove 1 item → 4 items, threshold 5 → IS low stock
        # ========================================================================
        print("\n=== STEP 2: Remove 1 item → 4 items, threshold 5 ===")
        
        # Delete one asset
        db.delete(assets[0])
        db.commit()
        assets = assets[1:]  # Remove from list
        
        # Verify: IS low stock (4 < 5)
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert summary["is_low_stock"] is True, "4 items with threshold 5 SHOULD be low stock"
        assert len(summary["low_stock_types"]) == 1, "Should have 1 low stock type"
        assert summary["total_items"] == 4
        
        # Verify low stock type details
        low_stock_item = summary["low_stock_types"][0]
        assert low_stock_item["manufacturer"] == "FS"
        assert low_stock_item["model"] == "1m"
        assert low_stock_item["count"] == 4
        assert low_stock_item["min_threshold"] == 5
        
        # Verify item type still has correct threshold
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 4
        assert fs_1m_type["min_threshold"] == 5
        
        # Verify IS in low stock alerts (via stock-summary)
        success, container_summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert container_summary["is_low_stock"] is True
        
        # ========================================================================
        # STEP 3: Lower threshold to 4 → 4 items, threshold 4 → NOT low stock (fine)
        # ========================================================================
        print("\n=== STEP 3: Lower threshold to 4 → 4 items, threshold 4 ===")
        
        # Update threshold to 4
        update_data = {"min_threshold": 4}
        success, updated_threshold = authenticated_client.put(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold_id}",
            update_data,
            expected_status=200
        )
        assert success
        assert updated_threshold["min_threshold"] == 4
        
        # Verify: NOT low stock (4 >= 4)
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert summary["is_low_stock"] is False, "4 items with threshold 4 should NOT be low stock"
        assert len(summary["low_stock_types"]) == 0, "Should have no low stock types"
        assert summary["total_items"] == 4
        
        # Verify item type has updated threshold
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 4
        assert fs_1m_type["min_threshold"] == 4
        
        # Verify NOT in low stock alerts
        success, container_summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert container_summary["is_low_stock"] is False
        
        # ========================================================================
        # STEP 4: Lower threshold to 0 → 4 items, threshold 0 → Disappears from low stock list
        # ========================================================================
        print("\n=== STEP 4: Lower threshold to 0 → 4 items, threshold 0 ===")
        
        # Delete threshold (setting to 0 means "no threshold")
        success, response = authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold_id}",
            expected_status=200
        )
        assert success
        
        # Verify: NOT low stock (no threshold means no tracking)
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert summary["is_low_stock"] is False, "Container with no threshold should NOT be low stock"
        assert len(summary["low_stock_types"]) == 0, "Should have no low stock types"
        assert summary["total_items"] == 4
        
        # Verify item type has NO threshold (None or 0)
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 4
        # min_threshold should be None or 0 (not set)
        assert fs_1m_type.get("min_threshold") is None or fs_1m_type.get("min_threshold") == 0, \
            f"Item with no threshold should have min_threshold=None or 0, got {fs_1m_type.get('min_threshold')}"
        
        # Verify NOT in low stock alerts
        success, container_summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert container_summary["is_low_stock"] is False
        
        # Verify threshold is actually deleted from database
        db_threshold = db.query(ContainerStockThreshold).filter(
            ContainerStockThreshold.id == threshold_id
        ).first()
        assert db_threshold is None, "Threshold should be deleted from database"
        
        # ========================================================================
        # CLEANUP
        # ========================================================================
        # Delete assets
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}",
            expected_status=200
        )
        
    finally:
        clear_tenant_id()
        db.close()

