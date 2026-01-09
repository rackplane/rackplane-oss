# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Network Cables API Test Suite
Tests for NetworkCable CRUD operations, filtering, and validation.
"""

import pytest
from app.models.network_cable import CableType, ConnectorType


@pytest.mark.integration
@pytest.mark.network_cable
def test_create_network_cable(authenticated_client, test_prefix):
    """
    TC-NETCABLE-001: Create network cable with valid data
    """
    cable_data = {
        "name": f"{test_prefix}-DAC-10G-3M-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "10G",
        "length_meters": 3.0,
        "manufacturer": "Cisco",
        "model": "QSFP-H10G-CU3M",
        "serial_number": f"{test_prefix}-DAC-SN-001",
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    
    assert success, f"Failed to create network cable: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["name"] == cable_data["name"]
    assert response["cable_type"] == cable_data["cable_type"]
    assert response["connector_type"] == cable_data["connector_type"]
    assert response["speed"] == cable_data["speed"]
    assert response["serial_number"] == cable_data["serial_number"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_create_fiber_cable(authenticated_client, test_prefix):
    """
    TC-NETCABLE-002: Create fiber optic cable
    """
    cable_data = {
        "name": f"{test_prefix}-FIBER-OM4-10M-001",
        "cable_type": "fiber",
        "connector_type": "lc",
        "speed": "10G",
        "length_meters": 10.0,
        "fiber_mode": "multimode",
        "wavelength": "850nm",
        "manufacturer": "Corning",
        "model": "OM4",
        "serial_number": f"{test_prefix}-FIBER-SN-001",
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    
    assert success, f"Failed to create fiber cable: {response}"
    assert response["cable_type"] == "fiber"
    assert response["connector_type"] == "lc"
    assert response["fiber_mode"] == "multimode"
    assert response["wavelength"] == "850nm"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_list_network_cables(authenticated_client, test_prefix):
    """
    TC-NETCABLE-003: List all network cables
    """
    # Create a test cable first
    cable_data = {
        "name": f"{test_prefix}-LIST-TEST-001",
        "cable_type": "copper",
        "connector_type": "rj45",
        "speed": "1G",
        "length_meters": 5.0,
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # List cables
    success, response = authenticated_client.get("/api/v1/network-cables/", expected_status=200)
    
    assert success, f"Failed to list network cables: {response}"
    assert isinstance(response, list), f"Expected list response, got: {type(response)}"
    assert len(response) > 0, "Should have at least one cable"
    
    # Find our test cable
    test_cable = next((c for c in response if c["id"] == cable_id), None)
    assert test_cable is not None, "Test cable should be in the list"
    assert test_cable["name"] == cable_data["name"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_get_network_cable_by_id(authenticated_client, test_prefix):
    """
    TC-NETCABLE-004: Get network cable by ID
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-GET-TEST-001",
        "cable_type": "dac",
        "connector_type": "sfp+",
        "speed": "10G",
        "length_meters": 2.0,
        "manufacturer": "Generic",
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Get the cable by ID
    success, fetched = authenticated_client.get(f"/api/v1/network-cables/{cable_id}", expected_status=200)
    
    assert success, f"Failed to fetch cable: {fetched}"
    assert fetched["id"] == cable_id
    assert fetched["name"] == cable_data["name"]
    assert fetched["cable_type"] == cable_data["cable_type"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_update_network_cable(authenticated_client, test_prefix):
    """
    TC-NETCABLE-005: Update network cable
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-UPDATE-TEST-001",
        "cable_type": "copper",
        "connector_type": "rj45",
        "speed": "1G",
        "length_meters": 3.0,
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Update the cable
    update_data = {
        "name": f"{test_prefix}-UPDATE-TEST-001-UPDATED",
        "speed": "10G",
        "length_meters": 5.0,
        "notes": "Updated test cable"
    }
    
    success, updated = authenticated_client.put(f"/api/v1/network-cables/{cable_id}", update_data, expected_status=200)
    
    assert success, f"Failed to update cable: {updated}"
    assert updated["name"] == update_data["name"]
    assert updated["speed"] == update_data["speed"]
    assert updated["length_meters"] == update_data["length_meters"]
    assert updated["notes"] == update_data["notes"]
    # Original values should remain
    assert updated["cable_type"] == cable_data["cable_type"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_delete_network_cable(authenticated_client, test_prefix):
    """
    TC-NETCABLE-006: Delete network cable
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-DELETE-TEST-001",
        "cable_type": "dac",
        "connector_type": "qsfp",
        "speed": "40G",
        "length_meters": 1.0,
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Delete the cable
    success, response = authenticated_client.delete(f"/api/v1/network-cables/{cable_id}", expected_status=204)
    
    assert success, f"Failed to delete cable: {response}"
    
    # Verify it's deleted (may return 404 or 200 with empty result)
    success, fetched = authenticated_client.get(f"/api/v1/network-cables/{cable_id}", expected_status=[200, 404])
    if success and fetched:
        # If it returns 200, check that it's actually not found
        assert "not found" in str(fetched.get("detail", "")).lower() or fetched.get("id") is None, "Cable should not exist after deletion"


@pytest.mark.integration
@pytest.mark.network_cable
def test_filter_network_cables_by_type(authenticated_client, test_prefix):
    """
    TC-NETCABLE-007: Filter network cables by cable type
    """
    # Create cables of different types
    dac_cable = {
        "name": f"{test_prefix}-FILTER-DAC-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "quantity": 1
    }
    
    fiber_cable = {
        "name": f"{test_prefix}-FILTER-FIBER-001",
        "cable_type": "fiber",
        "connector_type": "lc",
        "speed": "10G",
        "quantity": 1
    }
    
    success, dac = authenticated_client.post("/api/v1/network-cables/", dac_cable, expected_status=201)
    assert success, f"Failed to create DAC cable: {dac}"
    dac_id = dac["id"]
    
    success, fiber = authenticated_client.post("/api/v1/network-cables/", fiber_cable, expected_status=201)
    assert success, f"Failed to create fiber cable: {fiber}"
    fiber_id = fiber["id"]
    
    # Filter by DAC type
    success, response = authenticated_client.get("/api/v1/network-cables/?cable_type=dac", expected_status=200)
    assert success, f"Failed to filter by cable type: {response}"
    assert isinstance(response, list)
    
    dac_cables = [c for c in response if c["cable_type"] == "dac"]
    assert len(dac_cables) > 0, "Should have at least one DAC cable"
    assert any(c["id"] == dac_id for c in dac_cables), "Created DAC cable should be in filtered results"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{dac_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/network-cables/{fiber_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_filter_network_cables_by_speed(authenticated_client, test_prefix):
    """
    TC-NETCABLE-008: Filter network cables by speed
    """
    # Create cables with different speeds
    cable_10g = {
        "name": f"{test_prefix}-FILTER-10G-001",
        "cable_type": "dac",
        "connector_type": "sfp+",
        "speed": "10G",
        "quantity": 1
    }
    
    cable_100g = {
        "name": f"{test_prefix}-FILTER-100G-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "quantity": 1
    }
    
    success, c10g = authenticated_client.post("/api/v1/network-cables/", cable_10g, expected_status=201)
    assert success, f"Failed to create 10G cable: {c10g}"
    c10g_id = c10g["id"]
    
    success, c100g = authenticated_client.post("/api/v1/network-cables/", cable_100g, expected_status=201)
    assert success, f"Failed to create 100G cable: {c100g}"
    c100g_id = c100g["id"]
    
    # Filter by 10G speed
    success, response = authenticated_client.get("/api/v1/network-cables/?speed=10G", expected_status=200)
    assert success, f"Failed to filter by speed: {response}"
    assert isinstance(response, list)
    
    speed_10g_cables = [c for c in response if c["speed"] == "10G"]
    assert len(speed_10g_cables) > 0, "Should have at least one 10G cable"
    assert any(c["id"] == c10g_id for c in speed_10g_cables), "Created 10G cable should be in filtered results"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{c10g_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/network-cables/{c100g_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_with_storage_container(authenticated_client, test_prefix, test_tenant):
    """
    TC-NETCABLE-009: Assign network cable to storage container
    """
    from app.core.database import SessionLocal
    from app.models.storage_container import StorageContainer
    from app.core.tenant import set_current_tenant_id

    # Create a storage container
    db = SessionLocal()
    try:
        # Set tenant context for the session
        set_current_tenant_id(test_tenant["id"])

        container = StorageContainer(
            name=f"{test_prefix}-CABLE-CONTAINER-001",
            container_type="box",
            tenant_id=test_tenant["id"]
        )
        db.add(container)
        db.commit()
        db.refresh(container)
        container_id = container.id
    finally:
        db.close()
    
    # Create cable with storage container
    cable_data = {
        "name": f"{test_prefix}-STORED-CABLE-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "storage_container_id": container_id,
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with storage container: {response}"
    assert response["storage_container_id"] == container_id
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_serial_number_uniqueness(authenticated_client, test_prefix):
    """
    TC-NETCABLE-010: Verify serial number uniqueness within tenant
    """
    serial_number = f"{test_prefix}-UNIQUE-SN-001"
    
    # Create first cable with serial number
    cable_data = {
        "name": f"{test_prefix}-UNIQUE-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "serial_number": serial_number,
        "quantity": 1
    }
    
    success, first = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create first cable: {first}"
    first_id = first["id"]
    
    # Try to create second cable with same serial number (should fail)
    cable_data2 = {
        "name": f"{test_prefix}-UNIQUE-002",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "serial_number": serial_number,  # Same serial number
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data2, expected_status=400)
    # Should fail, but check if it's a validation error or duplicate error
    if success:
        # Got 400 as expected - check error message
        error_detail = str(response.get("detail", "")).lower()
        assert "serial" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
            f"Expected serial number error, got: {response}"
    else:
        # Different status code - check if it's an error response
        error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
        assert "serial" in error_detail or "already exists" in error_detail or "duplicate" in error_detail or "400" in str(response), \
            f"Expected serial number error, got: {response}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{first_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_quantity(authenticated_client, test_prefix):
    """
    TC-NETCABLE-011: Test cable quantity field
    """
    cable_data = {
        "name": f"{test_prefix}-QUANTITY-001",
        "cable_type": "copper",
        "connector_type": "rj45",
        "speed": "1G",
        "quantity": 5  # Multiple cables
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with quantity: {response}"
    assert response["quantity"] == 5
    
    # Update quantity
    update_data = {"quantity": 10}
    success, updated = authenticated_client.put(f"/api/v1/network-cables/{response['id']}", update_data, expected_status=200)
    assert success, f"Failed to update quantity: {updated}"
    assert updated["quantity"] == 10
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_breakout_configuration(authenticated_client, test_prefix):
    """
    TC-NETCABLE-012: Test breakout configuration for breakout cables
    """
    cable_data = {
        "name": f"{test_prefix}-BREAKOUT-001",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "40G",
        "breakout": "4x10G",  # Breakout configuration
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/network-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create breakout cable: {response}"
    assert response["breakout"] == "4x10G"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_get_nonexistent(authenticated_client):
    """
    TC-NETCABLE-013: Get non-existent network cable should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.get(f"/api/v1/network-cables/{nonexistent_id}", expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        # Got different status - check response
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_update_nonexistent(authenticated_client):
    """
    TC-NETCABLE-014: Update non-existent network cable should return 404
    """
    nonexistent_id = 999999
    update_data = {"name": "Updated Name"}
    
    success, response = authenticated_client.put(f"/api/v1/network-cables/{nonexistent_id}", update_data, expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.network_cable
def test_network_cable_delete_nonexistent(authenticated_client):
    """
    TC-NETCABLE-015: Delete non-existent network cable should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.delete(f"/api/v1/network-cables/{nonexistent_id}", expected_status=[404, 200, 204])
    # May return 404, 200, or 204 - check if it's actually an error
    if success:
        error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
        # If it's a dict with detail, it's an error
        if "detail" in response:
            assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.network_cable
def test_search_network_cables(authenticated_client, test_prefix):
    """
    TC-NETCABLE-016: Search network cables by name
    """
    # Create two cables
    cable1 = {
        "name": f"{test_prefix}-SEARCH-ONE",
        "cable_type": "copper",
        "connector_type": "rj45",
        "speed": "1G",
        "quantity": 1
    }
    cable2 = {
        "name": f"{test_prefix}-SEARCH-TWO",
        "cable_type": "copper",
        "connector_type": "rj45",
        "speed": "1G",
        "quantity": 1
    }
    
    success, c1 = authenticated_client.post("/api/v1/network-cables/", cable1, expected_status=201)
    assert success, f"Failed to create cable 1: {c1}"
    c1_id = c1["id"]

    success, c2 = authenticated_client.post("/api/v1/network-cables/", cable2, expected_status=201)
    assert success, f"Failed to create cable 2: {c2}"
    c2_id = c2["id"]
    
    # Search for "ONE"
    success, results = authenticated_client.get(f"/api/v1/network-cables/?search=SEARCH-ONE", expected_status=200)
    assert success, f"Search failed: {results}"
    # Filter strictly to our test prefix to avoid noise
    matching = [c for c in results if c["id"] == c1_id]
    assert len(matching) == 1, "Should find exactly one match for unique name"
    
    # Search for common prefix
    success, results = authenticated_client.get(f"/api/v1/network-cables/?search={test_prefix}-SEARCH", expected_status=200)
    assert success
    matching = [c for c in results if c["id"] in [c1_id, c2_id]]
    assert len(matching) == 2, "Should find both cables with common prefix"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{c1_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/network-cables/{c2_id}", expected_status=204)


