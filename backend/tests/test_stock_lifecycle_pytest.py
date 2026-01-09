"""
Test cases for stock lifecycle and storage box management.

Tests the complete workflow:
1. Generate a storage box
2. Add items to the box
3. Verify stock counts
4. Remove items and verify low stock alerts
5. Update threshold and verify box visibility
"""

import pytest
from app.models.asset import Asset, AssetStatus
from app.models.asset_type import AssetTypeModel
from app.core.tenant_query import apply_tenant_filter


@pytest.mark.stock
@pytest.mark.integration
def test_storage_box_lifecycle_complete_workflow(
    authenticated_client,
    test_user,
    test_tenant
):
    """
    Complete test of storage box lifecycle:
    1. Generate a storage box with threshold 5
    2. Add 5 items to the box
    3. Verify box shows up and is in good state (not low stock)
    4. Remove one item (now 4 items)
    5. Verify box shows 4 out of 5 and indicates low stock/place order
    6. Update threshold to 2 (box has 2 items, should still show up)
    7. Verify box remains visible in "All Storage Boxes" list
    """
    from app.core.tenant import set_current_tenant_id
    from app.core.database import SessionLocal
    set_current_tenant_id(test_tenant["id"])
    
    # Get database session
    db = SessionLocal()
    try:
        # Step 1: Create a DAC cable asset type if it doesn't exist
        asset_type_query = db.query(AssetTypeModel).filter(AssetTypeModel.name == 'dac_cable')
        asset_type_query = apply_tenant_filter(asset_type_query, AssetTypeModel)
        dac_type = asset_type_query.first()
        
        if not dac_type:
            dac_type = AssetTypeModel(
                name='dac_cable',
                display_name='DAC Cable',
                description='Direct Attach Copper Cable',
                tenant_id=test_tenant["id"]
            )
            db.add(dac_type)
            db.commit()
            db.refresh(dac_type)
        
        # Step 2: Generate a storage box using the auto-generate endpoint
        success, box_response = authenticated_client.post(
            "/api/v1/stock-boxes/find-or-create-temp",
            {
                "asset_type": "dac_cable",
                "custom_fields": {
                    "dac_speed": "800G",
                    "dac_connector_a": "OSFP112",
                    "dac_connector_b": "OSFP112",
                    "cable_length": "1M"
                },
                "min_stock_threshold": 5
            },
            expected_status=200
        )
        
        assert success, f"Failed to create box: {box_response}"
        assert box_response["box_name"] == "DAC-800G-OSFP112-OSFP112-1M", "Box name should match naming convention"
        assert box_response["min_stock_threshold"] == 5, "Box threshold should be 5"
        box_id = box_response["box_id"]
        print(f"DEBUG: Created box with ID {box_id}")
        
        # Step 3: Verify box shows up in storage boxes list
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        assert success, f"Failed to get storage boxes: {boxes}"
        box_found = any(box["id"] == box_id for box in boxes)
        assert box_found, f"Box {box_id} should appear in storage boxes list"
        
        # Step 4: Get stock summary - should show 0 items initially
        success, stock_summary = authenticated_client.get(
            f"/api/v1/assets/containers/{box_id}/stock-summary",
            expected_status=200
        )
        assert success, f"Failed to get stock summary: {stock_summary}"
        assert stock_summary["total_items"] == 0, "Box should start with 0 items"
        assert stock_summary["is_low_stock"] == True, "Box with 0 items should be low stock (threshold: 5)"
        
        # Step 5: Create 5 DAC cable items and add them to the box
        cable_ids = []
        for i in range(5):
            success, cable_data = authenticated_client.post(
                "/api/v1/assets/",
                {
                    "asset_tag": f"TEST-CABLE-{i+1}",
                    "serial_number": f"TEST-SN-{i+1}",
                    "asset_type": "dac_cable",
                    "manufacturer": "Test Manufacturer",
                    "model": "Test Model",
                    "status": "in_storage",
                    "container_id": box_id,
                    "custom_fields": {
                        "dac_speed": "800G",
                        "dac_connector_a": "OSFP112",
                        "dac_connector_b": "OSFP112",
                        "cable_length": "1M"
                    }
                },
                expected_status=201
            )
            assert success, f"Failed to create cable {i+1}: {cable_data}"
            cable_ids.append(cable_data["id"])
            print(f"Created cable {i+1} with ID {cable_data['id']}, container_id={cable_data.get('container_id')}")

        print(f"DEBUG: Created {len(cable_ids)} cables: {cable_ids}")

        # Step 6: Verify box now shows 5 items and is NOT low stock
        success, stock_summary = authenticated_client.get(
            f"/api/v1/assets/containers/{box_id}/stock-summary",
            expected_status=200
        )
        assert success
        assert stock_summary["total_items"] == 5, f"Box should have 5 items, got {stock_summary['total_items']}"
        assert stock_summary["is_low_stock"] == False, "Box with 5 items (threshold: 5) should NOT be low stock"
        
        # Verify box still appears in storage boxes list
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        assert success
        box_found = any(box["id"] == box_id for box in boxes)
        assert box_found, "Box should still appear in storage boxes list with 5 items"
        
        # Step 7: Remove one item (set its container_id to None and status to DEPLOYED)
        success, _ = authenticated_client.put(
            f"/api/v1/assets/{cable_ids[0]}",
            {
                "container_id": None,
                "status": "deployed"
            },
            expected_status=200
        )
        assert success, "Failed to remove item"
        
        # Step 8: Verify box now shows 4 items and IS low stock
        success, stock_summary = authenticated_client.get(
            f"/api/v1/assets/containers/{box_id}/stock-summary",
            expected_status=200
        )
        assert success
        assert stock_summary["total_items"] == 4, f"Box should have 4 items after removing one, got {stock_summary['total_items']}"
        assert stock_summary["is_low_stock"] == True, "Box with 4 items (threshold: 5) should be low stock"
        assert len(stock_summary["low_stock_types"]) > 0, "Should have low stock item types"
        
        # Verify box still appears in storage boxes list (even when low stock)
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        assert success
        box_found = any(box["id"] == box_id for box in boxes)
        assert box_found, "Box should still appear in storage boxes list even when low stock"
        
        # Step 9: Update threshold to 2 (box has 4 items, but we'll verify it still shows up)
        success, _ = authenticated_client.put(
            f"/api/v1/assets/{box_id}",
            {
                "min_stock_threshold": 2
            },
            expected_status=200
        )
        assert success, "Failed to update threshold"
        
        # Step 10: Verify box still shows up in storage boxes list after threshold update
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        assert success
        box_found = any(box["id"] == box_id for box in boxes)
        assert box_found, "Box should still appear in storage boxes list after threshold update"
        
        # Verify updated threshold is correct
        box_data = next((box for box in boxes if box["id"] == box_id), None)
        assert box_data is not None, "Box should be found in list"
        assert box_data["min_stock_threshold"] == 2, f"Box threshold should be 2, got {box_data.get('min_stock_threshold')}"
        
        # Step 11: Remove 2 more items so we have 2 items (matching threshold)
        for cable_id in cable_ids[1:3]:  # Remove 2 more items
            success, _ = authenticated_client.put(
                f"/api/v1/assets/{cable_id}",
                {
                    "container_id": None,
                    "status": "deployed"
                },
                expected_status=200
            )
            assert success, "Failed to remove item"
        
        # Step 12: Verify box has 2 items and is NOT low stock (threshold: 2)
        success, stock_summary = authenticated_client.get(
            f"/api/v1/assets/containers/{box_id}/stock-summary",
            expected_status=200
        )
        assert success
        assert stock_summary["total_items"] == 2, f"Box should have 2 items, got {stock_summary['total_items']}"
        assert stock_summary["is_low_stock"] == False, "Box with 2 items (threshold: 2) should NOT be low stock"
        
        # Step 13: CRITICAL - Verify box STILL appears in storage boxes list
        # This is the bug fix: boxes should not disappear when threshold equals stock count
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        assert success
        box_found = any(box["id"] == box_id for box in boxes)
        assert box_found, "Box should STILL appear in storage boxes list when threshold equals stock count (2 items, threshold: 2)"
        
        # Cleanup: Remove remaining test items
        for cable_id in cable_ids[2:]:  # Remove remaining items
            authenticated_client.delete(f"/api/v1/assets/{cable_id}", expected_status=200)
        
        # Delete the box
        authenticated_client.delete(f"/api/v1/assets/{box_id}", expected_status=200)
        
        # Delete the asset type we created
        if dac_type:
            db.delete(dac_type)
            db.commit()
        
        # Verify cleanup
        success, boxes = authenticated_client.get("/api/v1/assets/storage-boxes", expected_status=200)
        if success:
            box_found = any(box["id"] == box_id for box in boxes)
            assert not box_found, "Box should be deleted after cleanup"
    finally:
        db.close()
