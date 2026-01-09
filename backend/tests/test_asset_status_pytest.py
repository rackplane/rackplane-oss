"""
Pytest-based asset status tests.

Tests asset status management and normalization.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asset
def test_asset_status_in_storage(authenticated_client, test_prefix):
    """
    TC-STATUS-001: Test IN_STORAGE status
    
    This test verifies that assets can be set to IN_STORAGE status.
    """
    # Create a storage box
    box_data = {
        "asset_tag": f"{test_prefix}-StatusBox-001",
        "serial_number": f"{test_prefix}-SB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Cable Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create an asset with IN_STORAGE status
    asset_data = {
        "asset_tag": f"{test_prefix}-StatusTest-001",
        "serial_number": f"{test_prefix}-ST-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "in_storage",  # Must be lowercase
        "container_id": box_id
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    
    # Verify status is IN_STORAGE
    assert asset["status"] == "in_storage", \
        f"Expected status 'in_storage', got {asset['status']}"
    assert asset["container_id"] == box_id, \
        f"Expected container_id={box_id}, got {asset['container_id']}"
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.asset
def test_asset_status_normalization(authenticated_client, test_prefix):
    """
    TC-STATUS-002: Test status normalization (case-insensitive)
    
    This test verifies that status values are normalized correctly.
    """
    # Test various status formats
    status_tests = [
        ("IN_STORAGE", "in_storage"),
        ("in_storage", "in_storage"),
        ("In_Storage", "in_storage"),
        ("DEPLOYED", "deployed"),
        ("deployed", "deployed"),
    ]
    
    for input_status, expected_status in status_tests:
        asset_data = {
            "asset_tag": f"{test_prefix}-StatusNorm-{input_status}",
            "serial_number": f"{test_prefix}-SN-{input_status}",
            "asset_type": "ethernet_cable",
            "manufacturer": "Generic",
            "model": "CAT6",
            "status": input_status
        }
        
        success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
        
        if success:
            # Verify status was normalized
            assert asset["status"] == expected_status, \
                f"Status '{input_status}' should be normalized to '{expected_status}', got '{asset['status']}'"
            
            # Cleanup
            authenticated_client.delete(f"/api/v1/assets/{asset['id']}", expected_status=204)
        else:
            pytest.fail(f"Failed to create asset with status '{input_status}': {asset}")


@pytest.mark.integration
@pytest.mark.asset
def test_asset_status_rma_retired(authenticated_client, test_prefix):
    """
    TC-STATUS-003: Test RMA and RETIRED statuses
    
    This test verifies that RMA and RETIRED statuses work correctly.
    """
    # Create asset with RMA status
    rma_asset_data = {
        "asset_tag": f"{test_prefix}-RMA-001",
        "serial_number": f"{test_prefix}-RMA-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "rma"
    }
    
    success, rma_asset = authenticated_client.post("/api/v1/assets/", rma_asset_data, expected_status=201)
    assert success, f"Failed to create RMA asset: {rma_asset}"
    assert rma_asset["status"] == "rma", f"Expected status 'rma', got {rma_asset['status']}"
    
    # Create asset with RETIRED status
    retired_asset_data = {
        "asset_tag": f"{test_prefix}-RETIRED-001",
        "serial_number": f"{test_prefix}-RET-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "retired"
    }
    
    success, retired_asset = authenticated_client.post("/api/v1/assets/", retired_asset_data, expected_status=201)
    assert success, f"Failed to create retired asset: {retired_asset}"
    assert retired_asset["status"] == "retired", \
        f"Expected status 'retired', got {retired_asset['status']}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{rma_asset['id']}", expected_status=204)
    authenticated_client.delete(f"/api/v1/assets/{retired_asset['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.asset
def test_auto_status_on_container(authenticated_client, test_prefix):
    """
    TC-STATUS-004: Test auto-set status to IN_STORAGE when container_id is set
    
    This test verifies that setting container_id automatically sets status to IN_STORAGE.
    """
    # Create a storage box
    box_data = {
        "asset_tag": f"{test_prefix}-AutoStatusBox-001",
        "serial_number": f"{test_prefix}-ASB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Cable Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create asset with container_id - should auto-set status to IN_STORAGE
    asset_data = {
        "asset_tag": f"{test_prefix}-AutoStatus-001",
        "serial_number": f"{test_prefix}-AS-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "received",  # Explicit status
        "container_id": box_id  # Setting container_id should override status
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    
    # Verify status was auto-set to IN_STORAGE
    assert asset["status"] == "in_storage", \
        f"Expected status 'in_storage' when container_id is set, got {asset['status']}"
    assert asset["container_id"] == box_id, \
        f"Expected container_id={box_id}, got {asset['container_id']}"
    
    # Cleanup handled by test_tenant fixture (cascade delete)

