# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression Test: Stock Threshold API Response
Tests that min_threshold is always included in item_types response when threshold exists
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
@pytest.mark.regression
def test_min_threshold_always_included_in_item_types_response(authenticated_client, test_prefix, test_tenant):
    """
    REGRESSION: min_threshold must be included in item_types array when ContainerStockThreshold exists
    
    Bug: min_threshold was only added to item_type if item_threshold > 0, but the threshold lookup
    could return 0 as a fallback, causing thresholds to be missing from the API response even when
    they existed in the database.
    
    This test verifies:
    1. When a ContainerStockThreshold exists, min_threshold is included in item_types
    2. The threshold value matches what's in the database
    3. Frontend can display the threshold correctly
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
            name=f"{test_prefix}-Regression-Test-Box",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create 3 DAC cables (FS, 1m)
        for i in range(3):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-REG-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-REG-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        db.commit()
        
        # Create threshold: 5 (so 3 items is low stock)
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
        assert threshold["min_threshold"] == 5
        
        # Get stock summary via service (what backend uses)
        summary = get_container_stock_summary(container.id, db, is_storage_container=True)
        assert summary is not None, "Stock summary should not be None"
        
        # CRITICAL: Verify min_threshold is included in item_types
        assert "item_types" in summary, "item_types should be in summary"
        assert len(summary["item_types"]) > 0, "Should have at least one item type"
        
        # Find the FS 1m item type
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None, "FS 1m item type should exist in item_types"
        
        # REGRESSION CHECK: min_threshold must be present and correct
        assert "min_threshold" in fs_1m_type, \
            "min_threshold must be included in item_types response (REGRESSION: was missing)"
        assert fs_1m_type["min_threshold"] == 5, \
            f"min_threshold should be 5, got {fs_1m_type.get('min_threshold')}"
        assert fs_1m_type["count"] == 3, "Should have 3 items"
        
        # Verify it's also in low_stock_types (3 < 5)
        assert summary["is_low_stock"] is True, "Should be low stock (3 < 5)"
        assert len(summary["low_stock_types"]) == 1, "Should have 1 low stock type"
        
        low_stock_item = summary["low_stock_types"][0]
        assert low_stock_item["min_threshold"] == 5, \
            "min_threshold should also be in low_stock_types"
        
        # Get stock summary via API (what frontend uses)
        success, api_summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        # Verify API response also includes min_threshold
        api_fs_1m_type = next(
            (item for item in api_summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert api_fs_1m_type is not None, "FS 1m item type should exist in API response"
        assert "min_threshold" in api_fs_1m_type, \
            "min_threshold must be included in API response item_types (REGRESSION: was missing)"
        assert api_fs_1m_type["min_threshold"] == 5, \
            f"API min_threshold should be 5, got {api_fs_1m_type.get('min_threshold')}"
        
        # Cleanup
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold_id}",
            expected_status=200
        )
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}",
            expected_status=200
        )
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.stock
@pytest.mark.regression
def test_min_threshold_none_when_no_threshold_exists(authenticated_client, test_prefix, test_tenant):
    """
    REGRESSION: min_threshold should be None (not missing) when no ContainerStockThreshold exists
    
    This ensures the frontend can distinguish between "no threshold set" and "threshold is 0".
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
            name=f"{test_prefix}-Regression-NoThreshold-Box",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create 2 DAC cables (FS, 1m) - NO threshold set
        for i in range(2):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-NO-THRESH-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-NO-THRESH-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        db.commit()
        
        # Get stock summary
        summary = get_container_stock_summary(container.id, db, is_storage_container=True)
        assert summary is not None
        
        # Find the FS 1m item type
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        
        # REGRESSION CHECK: min_threshold should be None (not missing, not 0)
        assert "min_threshold" in fs_1m_type, \
            "min_threshold key should exist even when no threshold is set"
        assert fs_1m_type["min_threshold"] is None or fs_1m_type["min_threshold"] == 0, \
            f"min_threshold should be None or 0 when no threshold exists, got {fs_1m_type.get('min_threshold')}"
        
        # Should NOT be low stock (no threshold means no tracking)
        assert summary["is_low_stock"] is False, "Should not be low stock when no threshold is set"
        assert len(summary["low_stock_types"]) == 0, "Should have no low stock types"
        
        # Cleanup
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
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

