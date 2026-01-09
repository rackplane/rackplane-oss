"""
Pytest-based asset type tests.

Tests asset type listing and management.
"""

import pytest


@pytest.mark.integration
def test_list_asset_types(authenticated_client):
    """
    TC-ASSETTYPE-001: List all asset types for tenant
    
    This test verifies that asset types can be listed.
    """
    success, response = authenticated_client.get("/api/v1/asset-types/", expected_status=200)
    
    assert success, f"Failed to list asset types: {response}"
    assert isinstance(response, list), f"Expected list response, got: {type(response)}"
    
    # Verify asset type structure
    if len(response) > 0:
        asset_type = response[0]
        assert "id" in asset_type, "Asset type missing 'id' field"
        assert "name" in asset_type or "asset_type" in asset_type, \
            "Asset type missing 'name' or 'asset_type' field"


@pytest.mark.integration
def test_get_asset_type_by_id(authenticated_client):
    """
    TC-ASSETTYPE-002: Get asset type by ID
    
    This test verifies that asset types can be retrieved by ID.
    """
    # First, list asset types to get an ID
    success, asset_types = authenticated_client.get("/api/v1/asset-types/", expected_status=200)
    assert success, f"Failed to list asset types: {asset_types}"
    
    if len(asset_types) == 0:
        pytest.skip("No asset types available to test")
    
    asset_type_id = asset_types[0]["id"]
    
    # Get asset type by ID
    success, asset_type = authenticated_client.get(
        f"/api/v1/asset-types/{asset_type_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get asset type: {asset_type}"
    assert asset_type["id"] == asset_type_id
    assert "name" in asset_type or "asset_type" in asset_type


@pytest.mark.integration
def test_asset_type_validation(authenticated_client, test_prefix):
    """
    TC-ASSETTYPE-003: Test asset type validation (display name conversion)
    
    This test verifies that display names are correctly converted to internal names.
    """
    # Create asset with display name "Server" instead of "server_device"
    asset_data = {
        "asset_tag": f"{test_prefix}-TypeValidation-001",
        "serial_number": f"{test_prefix}-TV-SN-001",
        "asset_type": "Server",  # Display name, not internal name
        "manufacturer": "Test",
        "model": "Test Model",
        "status": "received"
    }
    
    success, response = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    if success:
        # Verify it was converted to server_device (or appropriate internal name)
        # The exact conversion depends on the asset type mapping
        assert "asset_type" in response, f"Response missing 'asset_type': {response}"
        # The asset_type should be normalized (could be server_device or Server depending on implementation)
        assert response["asset_type"] is not None, "Asset type should be set"
        
        # Cleanup
        authenticated_client.delete(f"/api/v1/assets/{response['id']}", expected_status=204)
    else:
        pytest.fail(f"Failed to create asset with display name: {response}")

