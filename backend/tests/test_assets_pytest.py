"""
Pytest-based asset management tests.

Tests asset creation, listing, and management functionality.
"""

import pytest
import time


@pytest.mark.integration
@pytest.mark.asset
def test_create_asset(authenticated_client, test_prefix, ensure_asset_types):
    """
    TC-ASSET-001: Create asset with valid data
    
    This test verifies that assets can be created via the API.
    """
    asset_data = {
        "asset_tag": f"{test_prefix}-Test-Asset-001",
        "serial_number": f"{test_prefix}-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge R720",
        "status": "active"
    }
    
    success, response = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    assert success, f"Failed to create asset: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["asset_tag"] == asset_data["asset_tag"]
    assert response["asset_type"] == asset_data["asset_type"]
    assert response["manufacturer"] == asset_data["manufacturer"]
    
    # Cleanup: Delete the asset we created
    authenticated_client.delete(f"/api/v1/assets/{response['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.asset
def test_list_assets(authenticated_client):
    """
    TC-ASSET-002: List all assets
    
    This test verifies that assets can be listed.
    """
    success, response = authenticated_client.get("/api/v1/assets/", expected_status=200)
    
    assert success, f"Failed to list assets: {response}"
    assert isinstance(response, dict), f"Expected dict response, got: {type(response)}"
    assert "assets" in response or "total" in response, f"Unexpected response structure: {response}"
    
    # Verify response structure
    if "assets" in response:
        assert isinstance(response["assets"], list), "Assets should be a list"
        assert "total" in response, "Response should include total count"


@pytest.mark.integration
@pytest.mark.asset
def test_get_asset_by_id(authenticated_client, test_prefix, ensure_asset_types):
    """
    TC-ASSET-003: Get asset by ID
    
    This test verifies that assets can be retrieved by ID.
    """
    # Create an asset first
    asset_data = {
        "asset_tag": f"{test_prefix}-Get-Test-001",
        "serial_number": f"{test_prefix}-GET-SN-001",
        "asset_type": "server_device",
        "manufacturer": "HP",
        "model": "ProLiant DL380",
        "status": "active"
    }
    
    success, created_asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {created_asset}"
    asset_id = created_asset["id"]
    
    # Get the asset by ID
    success, fetched_asset = authenticated_client.get(f"/api/v1/assets/{asset_id}", expected_status=200)
    
    assert success, f"Failed to fetch asset: {fetched_asset}"
    assert fetched_asset["id"] == asset_id
    assert fetched_asset["asset_tag"] == asset_data["asset_tag"]
    assert fetched_asset["serial_number"] == asset_data["serial_number"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.asset
def test_update_asset(authenticated_client, test_prefix, ensure_asset_types):
    """
    TC-ASSET-004: Update asset
    
    This test verifies that assets can be updated.
    """
    # Create an asset first
    asset_data = {
        "asset_tag": f"{test_prefix}-Update-Test-001",
        "serial_number": f"{test_prefix}-UPD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "IBM",
        "model": "System x3650",
        "status": "active"
    }
    
    success, created_asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {created_asset}"
    asset_id = created_asset["id"]
    
    # Update the asset
    update_data = {
        "model": "System x3650 M4",
        "status": "maintenance"
    }
    
    success, updated_asset = authenticated_client.put(f"/api/v1/assets/{asset_id}", update_data, expected_status=200)
    
    assert success, f"Failed to update asset: {updated_asset}"
    assert updated_asset["id"] == asset_id
    assert updated_asset["model"] == update_data["model"]
    assert updated_asset["status"] == update_data["status"]
    # Original fields should remain unchanged
    assert updated_asset["asset_tag"] == asset_data["asset_tag"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.asset
def test_delete_asset(authenticated_client, test_prefix):
    """
    TC-ASSET-005: Delete asset
    
    This test verifies that assets can be deleted.
    """
    # Create an asset first
    asset_data = {
        "asset_tag": f"{test_prefix}-Delete-Test-001",
        "serial_number": f"{test_prefix}-DEL-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Supermicro",
        "model": "X9DRi-LN4F+",
        "status": "active"
    }
    
    success, created_asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {created_asset}"
    asset_id = created_asset["id"]
    
    # Delete the asset (returns 204 No Content)
    success, response = authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=204)
    
    assert success, f"Failed to delete asset: {response}"
    
    # Verify asset is deleted (should get 404)
    success, response = authenticated_client.get(f"/api/v1/assets/{asset_id}", expected_status=404)
    assert success, f"Asset should be deleted (404), but got: {response}"


@pytest.mark.integration
@pytest.mark.asset
def test_create_asset_auto_generate_serial(authenticated_client, test_prefix, test_tenant):
    """
    TC-ASSET-006: Verify assets auto-generate serial numbers when not provided.
    
    This test verifies that when creating an asset without a serial_number,
    the system automatically generates one following the TYPE-TENANT-RANDOM-CHECK format.
    """
    from app.services.serial_service import validate_check_digit
    
    # Create asset without serial_number (should auto-generate)
    asset_data = {
        "asset_tag": f"{test_prefix}-AUTO-SERIAL-001",
        # No serial_number - should be auto-generated
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    assert success, f"Failed to create asset: {asset}"
    assert "serial_number" in asset, "Asset should have auto-generated serial_number"
    assert asset["serial_number"], "Serial number should not be empty"
    
    # Verify serial number format: TYPE-TENANT-RANDOM-CHECK
    serial = asset["serial_number"]
    parts = serial.split("-")
    assert len(parts) == 4, \
        f"Serial should follow format TYPE-TENANT-RANDOM-CHECK, got: {serial}"
    
    # Verify format components
    assert parts[0] == "SRV", f"Server should have SRV prefix, got: {parts[0]}"
    assert len(parts[1]) == 4, f"Tenant code should be 4 chars, got: {parts[1]}"
    assert len(parts[2]) == 6, f"Random block should be 6 chars, got: {parts[2]}"
    assert len(parts[3]) == 1, f"Check digit should be 1 char, got: {parts[3]}"
    
    # Verify check digit is valid
    assert validate_check_digit(serial), f"Auto-generated serial should have valid check digit: {serial}"
    
    # Verify asset_tag was also auto-generated if not provided
    assert asset["asset_tag"], "Asset tag should be auto-generated if not provided"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.asset
def test_create_asset_auto_generate_both(authenticated_client, test_prefix, test_tenant):
    """
    TC-ASSET-007: Verify assets auto-generate both serial_number and asset_tag when not provided.
    """
    # Create asset without serial_number or asset_tag (both should auto-generate)
    asset_data = {
        # No asset_tag - should be auto-generated
        # No serial_number - should be auto-generated
        "asset_type": "dac_cable",
        "manufacturer": "FS",
        "model": "10G DAC",
        "status": "received"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    assert success, f"Failed to create asset: {asset}"
    assert "serial_number" in asset and asset["serial_number"], \
        "Asset should have auto-generated serial_number"
    assert "asset_tag" in asset and asset["asset_tag"], \
        "Asset should have auto-generated asset_tag"
    
    # Verify serial number format
    serial = asset["serial_number"]
    assert serial.startswith("DAC-"), f"Serial should start with DAC prefix, got: {serial}"
    
    # Verify asset tag format
    tag = asset["asset_tag"]
    assert tag.startswith("DAC-"), f"Tag should start with DAC prefix, got: {tag}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset['id']}", expected_status=200)

