# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Container Stock Thresholds Test Suite
Tests for per-item-type stock threshold tracking and management
"""

import pytest
from app.core.database import SessionLocal
from app.models.asset import Asset, AssetStatus
from app.models.storage_container import StorageContainer
from app.models.container_stock_threshold import ContainerStockThreshold
from app.models.asset_type import AssetTypeModel
from app.core.tenant_query import apply_tenant_filter
from app.core.tenant import set_current_tenant_id, clear_tenant_id


@pytest.mark.integration
@pytest.mark.stock
@pytest.mark.thresholds
def test_create_stock_threshold(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-001: Create a stock threshold for a specific item type
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
            name=f"{test_prefix}-Test-Box",
            container_type='box',
            description="Test container for thresholds",
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create threshold via API
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
        assert threshold["asset_type"] == "dac_cable"
        assert threshold["manufacturer"] == "FS"
        assert threshold["model"] == "1m"
        assert threshold["min_threshold"] == 5
        assert threshold["storage_container_id"] == container.id
        
        # Verify in database
        db_threshold = db.query(ContainerStockThreshold).filter(
            ContainerStockThreshold.id == threshold["id"]
        ).first()
        assert db_threshold is not None
        assert db_threshold.min_threshold == 5
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_update_stock_threshold(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-002: Update an existing stock threshold
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
            name=f"{test_prefix}-Test-Box-Update",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create threshold
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
        assert success
        
        # Update threshold
        update_data = {"min_threshold": 10}
        success, updated = authenticated_client.put(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
            update_data,
            expected_status=200
        )
        assert success, f"Failed to update threshold: {updated}"
        assert updated["min_threshold"] == 10, f"Expected min_threshold=10, got {updated.get('min_threshold')}"
        
        # Verify in database
        db_threshold = db.query(ContainerStockThreshold).filter(
            ContainerStockThreshold.id == threshold["id"]
        ).first()
        assert db_threshold is not None, "Threshold not found in database"
        assert db_threshold.min_threshold == 10, f"Expected min_threshold=10 in DB, got {db_threshold.min_threshold}"
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_delete_stock_threshold(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-003: Delete a stock threshold
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
            name=f"{test_prefix}-Test-Box-Delete",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create threshold
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
        assert success
        threshold_id = threshold["id"]
        
        # Delete threshold
        success, response = authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold_id}",
            expected_status=200
        )
        assert success
        
        # Verify deleted
        db_threshold = db.query(ContainerStockThreshold).filter(
            ContainerStockThreshold.id == threshold_id
        ).first()
        assert db_threshold is None
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}",
            expected_status=200
        )
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.stock
@pytest.mark.thresholds
def test_list_stock_thresholds(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-004: List all stock thresholds for a container
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create asset types
        for asset_type_name, display_name in [
            ('dac_cable', 'DAC Cable'),
            ('ethernet_cable', 'Ethernet Cable')
        ]:
            at = db.query(AssetTypeModel).filter(AssetTypeModel.name == asset_type_name).first()
            if not at:
                at = AssetTypeModel(
                    name=asset_type_name,
                    display_name=display_name,
                    description=f"{display_name} type",
                    tenant_id=test_tenant["id"]
                )
                db.add(at)
        db.commit()
        
        # Create storage container
        container = StorageContainer(
            name=f"{test_prefix}-Test-Box-List",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create multiple thresholds
        thresholds_data = [
            {"asset_type": "dac_cable", "manufacturer": "FS", "model": "1m", "min_threshold": 5},
            {"asset_type": "dac_cable", "manufacturer": "FS", "model": "2m", "min_threshold": 3},
            {"asset_type": "ethernet_cable", "manufacturer": "Generic", "model": "CAT6", "min_threshold": 10}
        ]
        
        created_thresholds = []
        for threshold_data in thresholds_data:
            success, threshold = authenticated_client.post(
                f"/api/v1/storage-containers/{container.id}/stock-thresholds",
                threshold_data,
                expected_status=200
            )
            assert success
            created_thresholds.append(threshold)
        
        # List thresholds
        success, thresholds = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds",
            expected_status=200
        )
        assert success
        assert len(thresholds) == 3
        
        # Verify all thresholds are present
        threshold_ids = {t["id"] for t in thresholds}
        created_ids = {t["id"] for t in created_thresholds}
        assert threshold_ids == created_ids
        
        # Cleanup
        for threshold in created_thresholds:
            authenticated_client.delete(
                f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_stock_summary_with_thresholds(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-005: Stock summary correctly shows per-item-type thresholds and low stock
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
            name=f"{test_prefix}-Test-Box-Summary",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create 2 DAC cables (FS, 1m) - below threshold of 5
        for i in range(2):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        db.commit()
        
        # Create threshold for FS 1m DAC cables
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
        assert success
        
        # Get stock summary
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        # Verify summary structure
        assert "item_types" in summary
        assert "low_stock_types" in summary
        assert "is_low_stock" in summary
        assert summary["is_low_stock"] is True  # 2 < 5, so low stock
        
        # Find the FS 1m item type
        fs_1m_type = next(
            (item for item in summary["item_types"] 
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 2
        assert fs_1m_type["min_threshold"] == 5
        
        # Verify it's in low_stock_types
        low_stock_fs_1m = next(
            (item for item in summary["low_stock_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert low_stock_fs_1m is not None
        assert low_stock_fs_1m["count"] == 2
        
        # Cleanup
        # Delete assets
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_stock_summary_not_low_stock(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-006: Stock summary shows not low stock when count meets threshold
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
            name=f"{test_prefix}-Test-Box-NotLow",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create 5 DAC cables (FS, 1m) - exactly at threshold
        for i in range(5):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        db.commit()
        
        # Create threshold for FS 1m DAC cables
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
        assert success
        
        # Get stock summary
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        # Verify not low stock (5 >= 5)
        assert summary["is_low_stock"] is False
        assert len(summary["low_stock_types"]) == 0
        
        # Find the FS 1m item type
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 5
        assert fs_1m_type["min_threshold"] == 5
        
        # Cleanup
        # Delete assets
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_multiple_item_types_with_different_thresholds(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-007: Multiple item types with different thresholds in same container
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create asset types
        for asset_type_name, display_name in [
            ('dac_cable', 'DAC Cable'),
            ('ethernet_cable', 'Ethernet Cable')
        ]:
            at = db.query(AssetTypeModel).filter(AssetTypeModel.name == asset_type_name).first()
            if not at:
                at = AssetTypeModel(
                    name=asset_type_name,
                    display_name=display_name,
                    description=f"{display_name} type",
                    tenant_id=test_tenant["id"]
                )
                db.add(at)
        db.commit()
        
        # Create storage container
        container = StorageContainer(
            name=f"{test_prefix}-Test-Box-Multi",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create items: 2 FS 1m DAC (threshold 5 - low stock), 8 Generic CAT6 (threshold 10 - low stock)
        for i in range(2):
            asset = Asset(
                asset_tag=f"{test_prefix}-DAC-{i:03d}",
                serial_number=f"{test_prefix}-DAC-SN-{i:03d}",
                asset_type='dac_cable',
                manufacturer='FS',
                model='1m',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        
        for i in range(8):
            asset = Asset(
                asset_tag=f"{test_prefix}-ETH-{i:03d}",
                serial_number=f"{test_prefix}-ETH-SN-{i:03d}",
                asset_type='ethernet_cable',
                manufacturer='Generic',
                model='CAT6',
                status=AssetStatus.IN_STORAGE,
                storage_container_id=container.id,
                tenant_id=test_tenant["id"]
            )
            db.add(asset)
        db.commit()
        
        # Create thresholds
        thresholds_data = [
            {"asset_type": "dac_cable", "manufacturer": "FS", "model": "1m", "min_threshold": 5},
            {"asset_type": "ethernet_cable", "manufacturer": "Generic", "model": "CAT6", "min_threshold": 10}
        ]
        
        created_thresholds = []
        for threshold_data in thresholds_data:
            success, threshold = authenticated_client.post(
                f"/api/v1/storage-containers/{container.id}/stock-thresholds",
                threshold_data,
                expected_status=200
            )
            assert success
            created_thresholds.append(threshold)
        
        # Get stock summary
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        # Both should be low stock
        assert summary["is_low_stock"] is True
        assert len(summary["low_stock_types"]) == 2
        
        # Verify DAC cable threshold
        dac_type = next(
            (item for item in summary["item_types"]
             if item["asset_type"] == "dac_cable" and item["manufacturer"] == "FS"),
            None
        )
        assert dac_type is not None
        assert dac_type["count"] == 2
        assert dac_type["min_threshold"] == 5
        
        # Verify Ethernet cable threshold
        eth_type = next(
            (item for item in summary["item_types"]
             if item["asset_type"] == "ethernet_cable" and item["manufacturer"] == "Generic"),
            None
        )
        assert eth_type is not None
        assert eth_type["count"] == 8
        assert eth_type["min_threshold"] == 10
        
        # Cleanup
        # Delete assets
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        for threshold in created_thresholds:
            authenticated_client.delete(
                f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_duplicate_threshold_error(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-008: Cannot create duplicate threshold for same item type
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
            name=f"{test_prefix}-Test-Box-Duplicate",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create first threshold
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
        assert success
        
        # Try to create duplicate (should fail with 400)
        # Note: test client returns success=False for 4xx/5xx status codes
        success, response = authenticated_client.post(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds",
            threshold_data,
            expected_status=400
        )
        # When expected_status is 400, the client may return success=False OR the response may contain the error
        # Check both: either success is False, or response contains error detail
        if success:
            # If success=True but we expected 400, check the response for error details
            assert "detail" in response, f"Expected error detail in response: {response}"
            error_msg = str(response.get("detail", "")).lower()
            assert "already exists" in error_msg or "duplicate" in error_msg, \
                f"Expected 'already exists' or 'duplicate' in error message, got: {response}"
        else:
            # success=False means the request failed as expected
            error_msg = str(response).lower()
            assert "already exists" in error_msg or "duplicate" in error_msg or "400" in error_msg, \
                f"Expected error about duplicate, got: {response}"
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_threshold_without_manufacturer_model(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-009: Create threshold with None manufacturer/model (matches any)
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
            name=f"{test_prefix}-Test-Box-Any",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create threshold without manufacturer/model (matches any DAC cable)
        threshold_data = {
            "asset_type": "dac_cable",
            "manufacturer": None,
            "model": None,
            "min_threshold": 10
        }
        
        success, threshold = authenticated_client.post(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds",
            threshold_data,
            expected_status=200
        )
        assert success
        assert threshold["manufacturer"] is None or threshold["manufacturer"] == ""
        assert threshold["model"] is None or threshold["model"] == ""
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_threshold_zero_does_not_trigger_low_stock(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-010: Items with no threshold should NOT show as low stock (negative test)
    
    This verifies that items without a threshold (threshold=None or 0) should not appear
    in low_stock_types or trigger is_low_stock=True, even if count is very low.
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
            name=f"{test_prefix}-Test-Box-ZeroThreshold",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create 1 DAC cable (FS, 1m) - low count but NO threshold set
        asset = Asset(
            asset_tag=f"{test_prefix}-DAC-001",
            serial_number=f"{test_prefix}-DAC-SN-001",
            asset_type='dac_cable',
            manufacturer='FS',
            model='1m',
            status=AssetStatus.IN_STORAGE,
            storage_container_id=container.id,
            tenant_id=test_tenant["id"]
        )
        db.add(asset)
        db.commit()
        
        # Verify that with NO threshold, 1 item doesn't trigger low stock
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        assert summary["is_low_stock"] is False, "Container with no threshold should not be low stock"
        assert len(summary["low_stock_types"]) == 0, "Container with no threshold should have no low stock types"
        
        # Verify item_type doesn't have min_threshold set (or it's None/0)
        fs_1m_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "FS" and item["model"] == "1m"),
            None
        )
        assert fs_1m_type is not None
        assert fs_1m_type["count"] == 1
        # min_threshold should be None or 0 (not set)
        assert fs_1m_type.get("min_threshold") is None or fs_1m_type.get("min_threshold") == 0, \
            f"Item with no threshold should have min_threshold=None or 0, got {fs_1m_type.get('min_threshold')}"
        
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


@pytest.mark.integration
@pytest.mark.stock
@pytest.mark.thresholds
def test_items_with_threshold_zero_not_in_low_stock_types(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-011: Items with no threshold should NOT appear in low_stock_types array (negative test)
    
    This verifies that even if an item has a very low count (e.g., 1 item),
    if threshold is 0 or not set, it should NOT appear in low_stock_types.
    Only items with threshold > 0 and count < threshold should appear.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create asset types
        for asset_type_name, display_name in [
            ('dac_cable', 'DAC Cable'),
            ('ethernet_cable', 'Ethernet Cable')
        ]:
            at = db.query(AssetTypeModel).filter(AssetTypeModel.name == asset_type_name).first()
            if not at:
                at = AssetTypeModel(
                    name=asset_type_name,
                    display_name=display_name,
                    description=f"{display_name} type",
                    tenant_id=test_tenant["id"]
                )
                db.add(at)
        db.commit()
        
        # Create storage container
        container = StorageContainer(
            name=f"{test_prefix}-Test-Box-MixedThresholds",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create items: 1 FS 1m DAC (will have threshold 5 - low stock), 1 Generic CAT6 (no threshold - should NOT be low stock)
        dac_asset = Asset(
            asset_tag=f"{test_prefix}-DAC-001",
            serial_number=f"{test_prefix}-DAC-SN-001",
            asset_type='dac_cable',
            manufacturer='FS',
            model='1m',
            status=AssetStatus.IN_STORAGE,
            storage_container_id=container.id,
            tenant_id=test_tenant["id"]
        )
        db.add(dac_asset)
        
        eth_asset = Asset(
            asset_tag=f"{test_prefix}-ETH-001",
            serial_number=f"{test_prefix}-ETH-SN-001",
            asset_type='ethernet_cable',
            manufacturer='Generic',
            model='CAT6',
            status=AssetStatus.IN_STORAGE,
            storage_container_id=container.id,
            tenant_id=test_tenant["id"]
        )
        db.add(eth_asset)
        db.commit()
        
        # Create threshold ONLY for FS 1m DAC (threshold 5)
        # Generic CAT6 will have NO threshold (should not appear in low_stock_types)
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
        assert success
        
        # Get stock summary
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        # Should be low stock (because FS 1m DAC has 1 < 5)
        assert summary["is_low_stock"] is True
        
        # low_stock_types should ONLY contain FS 1m DAC, NOT Generic CAT6
        assert len(summary["low_stock_types"]) == 1, \
            f"Should have exactly 1 low stock type (FS 1m DAC), got {len(summary['low_stock_types'])}"
        
        low_stock_item = summary["low_stock_types"][0]
        assert low_stock_item["manufacturer"] == "FS"
        assert low_stock_item["model"] == "1m"
        assert low_stock_item["min_threshold"] == 5
        assert low_stock_item["count"] == 1
        
        # Verify Generic CAT6 is NOT in low_stock_types
        generic_cat6_in_low = any(
            item["manufacturer"] == "Generic" and item["model"] == "CAT6"
            for item in summary["low_stock_types"]
        )
        assert not generic_cat6_in_low, "Generic CAT6 (no threshold) should NOT be in low_stock_types"
        
        # Verify Generic CAT6 is in item_types but has no threshold
        generic_cat6_type = next(
            (item for item in summary["item_types"]
             if item["manufacturer"] == "Generic" and item["model"] == "CAT6"),
            None
        )
        assert generic_cat6_type is not None
        assert generic_cat6_type["count"] == 1
        # Should have no threshold (None or 0)
        assert generic_cat6_type.get("min_threshold") is None or generic_cat6_type.get("min_threshold") == 0, \
            f"Generic CAT6 with no threshold should have min_threshold=None or 0, got {generic_cat6_type.get('min_threshold')}"
        
        # Cleanup
        assets = db.query(Asset).filter(
            Asset.storage_container_id == container.id,
            Asset.tenant_id == test_tenant["id"]
        ).all()
        for asset in assets:
            db.delete(asset)
        db.commit()
        
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
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
@pytest.mark.thresholds
def test_max_quantity_logic(authenticated_client, test_prefix, test_tenant):
    """
    TC-THRESHOLD-011: Max quantity (Par Level) logic
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
            name=f"{test_prefix}-Test-Box-Max",
            container_type='box',
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        
        # Create threshold with max_quantity
        threshold_data = {
            "asset_type": "dac_cable",
            "manufacturer": "FS",
            "model": "1m",
            "min_threshold": 5,
            "max_quantity": 20
        }
        
        success, threshold = authenticated_client.post(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds",
            threshold_data,
            expected_status=200
        )
        assert success
        assert threshold["max_quantity"] == 20
        
        # Create an asset to ensure it shows up in summary
        asset = Asset(
            asset_tag=f"{test_prefix}-DAC-MAX-001",
            serial_number=f"{test_prefix}-DAC-MAX-SN-001",
            asset_type='dac_cable',
            manufacturer='FS',
            model='1m',
            status=AssetStatus.IN_STORAGE,
            storage_container_id=container.id,
            tenant_id=test_tenant["id"]
        )
        db.add(asset)
        db.commit()

        # Check summary
        success, summary = authenticated_client.get(
            f"/api/v1/storage-containers/{container.id}/stock-summary",
            expected_status=200
        )
        assert success
        
        item = next(
            (i for i in summary["item_types"] if i["asset_type"] == "dac_cable"),
            None
        )
        assert item is not None
        assert item["max_quantity"] == 20
        
        # Update max_quantity
        update_data = {
            "max_quantity": 25
        }
        success, updated = authenticated_client.put(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
            update_data,
            expected_status=200
        )
        assert success
        assert updated["max_quantity"] == 25
        
        # Cleanup
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}/stock-thresholds/{threshold['id']}",
            expected_status=200
        )
        db.delete(asset)
        db.commit()
        authenticated_client.delete(
            f"/api/v1/storage-containers/{container.id}",
            expected_status=200
        )
    finally:
        clear_tenant_id()
        db.close()
