"""
Pytest-based stock management tests.

Tests inventory lifecycle, stock tracking, and low stock alerts.
"""

import pytest
import time


@pytest.mark.integration
@pytest.mark.stock
def test_create_storage_box(authenticated_client, test_prefix):
    """
    TC-STOCK-001: Create storage box with min_stock_threshold
    
    This test verifies that storage boxes can be created with stock thresholds.
    """
    box_data = {
        "asset_tag": f"{test_prefix}-StorageBox-001",
        "serial_number": f"{test_prefix}-BOX-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Cable Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, response = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    
    assert success, f"Failed to create storage box: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["min_stock_threshold"] == 5, f"Expected min_stock_threshold=5, got {response.get('min_stock_threshold')}"
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.stock
def test_add_items_to_storage_box(authenticated_client, test_prefix):
    """
    TC-STOCK-002: Add items to storage box (container_id, status=IN_STORAGE)
    
    This test verifies that items can be added to storage boxes.
    """
    # Create storage box first
    box_data = {
        "asset_tag": f"{test_prefix}-StockBox-001",
        "serial_number": f"{test_prefix}-SB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create items to add to the box
    items = []
    for i in range(3):
        item_data = {
            "asset_tag": f"{test_prefix}-Cable-{i+1}",
            "serial_number": f"{test_prefix}-CABLE-SN-{i+1}",
            "asset_type": "dac_cable",
            "manufacturer": "Generic",
            "model": "SFP+ DAC",
            "status": "in_storage",  # Critical: must be lowercase
            "container_id": box_id  # Link to storage box
        }
        success, response = authenticated_client.post("/api/v1/assets/", item_data, expected_status=201)
        assert success, f"Failed to create item {i+1}: {response}"
        items.append(response["id"])
    
    assert len(items) == 3, f"Expected 3 items, created {len(items)}"
    
    # Verify items are in the box
    success, stock_info = authenticated_client.get(f"/api/v1/assets/containers/{box_id}/stock-summary", expected_status=200)
    assert success, f"Failed to get stock summary: {stock_info}"
    assert stock_info["total_items"] >= 3, f"Expected at least 3 items in box, got {stock_info.get('total_items')}"
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.stock
def test_get_stock_summary(authenticated_client, test_prefix):
    """
    TC-STOCK-003: Get stock level information for storage box
    
    This test verifies that stock summaries can be retrieved.
    """
    # Create storage box with items
    box_data = {
        "asset_tag": f"{test_prefix}-SummaryBox-001",
        "serial_number": f"{test_prefix}-SUM-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Add 3 items
    for i in range(3):
        item_data = {
            "asset_tag": f"{test_prefix}-SummaryItem-{i+1}",
            "serial_number": f"{test_prefix}-SI-SN-{i+1}",
            "asset_type": "ethernet_cable",
            "manufacturer": "Generic",
            "model": "CAT6",
            "status": "in_storage",
            "container_id": box_id
        }
        success, _ = authenticated_client.post("/api/v1/assets/", item_data, expected_status=201)
        assert success, f"Failed to create item {i+1}"
    
    # Get stock summary
    success, stock_info = authenticated_client.get(f"/api/v1/assets/containers/{box_id}/stock-summary", expected_status=200)
    
    assert success, f"Failed to get stock summary: {stock_info}"
    assert "total_items" in stock_info, f"Missing 'total_items' in response: {stock_info}"
    assert "min_threshold" in stock_info, f"Missing 'min_threshold' in response: {stock_info}"
    assert "is_low_stock" in stock_info, f"Missing 'is_low_stock' in response: {stock_info}"
    assert stock_info["total_items"] == 3, f"Expected 3 items, got {stock_info['total_items']}"
    assert stock_info["is_low_stock"] is True, f"Expected low stock (3 < 5), got {stock_info['is_low_stock']}"
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.stock
def test_stock_lifecycle_consumption(authenticated_client, test_prefix):
    """
    TC-STOCK-LIFECYCLE-001: Test complete lifecycle consumption workflow
    
    This test verifies the "Consume on Connect" workflow where assets
    are automatically deployed from storage when connected.
    """
    # Create storage box
    box_data = {
        "asset_tag": f"{test_prefix}-LifecycleBox-001",
        "serial_number": f"{test_prefix}-LCB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Test Storage Box",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create 5 cables in storage
    cables = []
    for i in range(5):
        cable_data = {
            "asset_tag": f"{test_prefix}-LifecycleCable-{i+1:03d}",
            "serial_number": f"{test_prefix}-LCC-SN-{i+1:03d}",
            "asset_type": "ethernet_cable",
            "manufacturer": "Test Cable Co",
            "model": "CAT6",
            "status": "in_storage",
            "container_id": box_id
        }
        success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
        assert success, f"Failed to create cable {i+1}: {cable}"
        cables.append(cable["id"])
    
    # Verify initial state: 5 cables in box
    success, stock_info = authenticated_client.get(f"/api/v1/assets/containers/{box_id}/stock-summary", expected_status=200)
    assert success, f"Failed to get stock summary: {stock_info}"
    assert stock_info["total_items"] == 5, f"Expected 5 cables initially, got {stock_info['total_items']}"
    
    # Create a device to connect to
    device_data = {
        "asset_tag": f"{test_prefix}-LifecycleDevice-001",
        "serial_number": f"{test_prefix}-LCD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Test Server Co",
        "model": "Test Server",
        "status": "active"
    }
    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]
    
    # Connect the first cable to the device (this should trigger deploy_asset)
    cable_to_deploy_id = cables[0]
    connect_data = {
        "cable_id": cable_to_deploy_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    success, connect_response = authenticated_client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    assert success, f"Failed to connect cable: {connect_response}"
    
    # Verify cable is removed from box (container_id=None) and status is DEPLOYED
    success, deployed_cable = authenticated_client.get(f"/api/v1/assets/{cable_to_deploy_id}", expected_status=200)
    assert success, f"Failed to fetch deployed cable: {deployed_cable}"
    assert deployed_cable.get("container_id") is None, \
        f"Expected container_id to be None after deployment, got {deployed_cable.get('container_id')}"
    assert deployed_cable.get("status") == "deployed", \
        f"Expected status to be 'deployed', got {deployed_cable.get('status')}"
    
    # Verify box has 4 items remaining
    success, stock_info_after = authenticated_client.get(f"/api/v1/assets/containers/{box_id}/stock-summary", expected_status=200)
    assert success, f"Failed to get stock info after deployment: {stock_info_after}"
    assert stock_info_after["total_items"] == 4, \
        f"Expected 4 cables remaining in box, found {stock_info_after['total_items']}"
    
    # Verify low stock alert was triggered (4 < 5)
    assert stock_info_after["is_low_stock"] is True, \
        f"Expected low stock alert (4 < 5), but is_low_stock is {stock_info_after.get('is_low_stock')}"
    
    # Cleanup: Delete connection
    connection_id = connect_response.get("connection", {}).get("id")
    if connection_id:
        authenticated_client.delete(f"/api/v1/connections/{connection_id}", expected_status=200)
    
    # Cleanup handled by test_tenant fixture (cascade delete)

