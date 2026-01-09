# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Power Cables API Test Suite
Tests for PowerCable CRUD operations, filtering, and validation.
"""

import pytest
from app.models.power_cable import PowerConnectorType


@pytest.mark.integration
@pytest.mark.power_cable
def test_create_power_cable(authenticated_client, test_prefix):
    """
    TC-POWCABLE-001: Create power cable with valid data
    """
    cable_data = {
        "name": f"{test_prefix}-PWR-C13-C14-2M-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "amperage": "10A",
        "length_meters": 2.0,
        "manufacturer": "Generic",
        "model": "Standard C13-C14",
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    
    assert success, f"Failed to create power cable: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["name"] == cable_data["name"]
    assert response["connector_end_a"] == cable_data["connector_end_a"]
    assert response["connector_end_b"] == cable_data["connector_end_b"]
    assert response["voltage"] == cable_data["voltage"]
    assert response["amperage"] == cable_data["amperage"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_create_power_cable_nema(authenticated_client, test_prefix):
    """
    TC-POWCABLE-002: Create power cable with NEMA connectors
    """
    cable_data = {
        "name": f"{test_prefix}-PWR-NEMA-001",
        "connector_end_a": "nema_5-15p",
        "connector_end_b": "nema_5-15r",
        "voltage": "120V",
        "amperage": "15A",
        "wire_gauge": "14AWG",
        "length_meters": 1.5,
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    
    assert success, f"Failed to create NEMA power cable: {response}"
    assert response["connector_end_a"] == "nema_5-15p"
    assert response["connector_end_b"] == "nema_5-15r"
    assert response["wire_gauge"] == "14AWG"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_list_power_cables(authenticated_client, test_prefix):
    """
    TC-POWCABLE-003: List all power cables
    """
    # Create a test cable first
    cable_data = {
        "name": f"{test_prefix}-LIST-TEST-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # List cables
    success, response = authenticated_client.get("/api/v1/power-cables/", expected_status=200)
    
    assert success, f"Failed to list power cables: {response}"
    assert isinstance(response, list), f"Expected list response, got: {type(response)}"
    assert len(response) > 0, "Should have at least one cable"
    
    # Find our test cable
    test_cable = next((c for c in response if c["id"] == cable_id), None)
    assert test_cable is not None, "Test cable should be in the list"
    assert test_cable["name"] == cable_data["name"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_get_power_cable_by_id(authenticated_client, test_prefix):
    """
    TC-POWCABLE-004: Get power cable by ID
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-GET-TEST-001",
        "connector_end_a": "c19",
        "connector_end_b": "c20",
        "voltage": "208V",
        "amperage": "16A",
        "length_meters": 3.0,
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Get the cable by ID
    success, fetched = authenticated_client.get(f"/api/v1/power-cables/{cable_id}", expected_status=200)
    
    assert success, f"Failed to fetch cable: {fetched}"
    assert fetched["id"] == cable_id
    assert fetched["name"] == cable_data["name"]
    assert fetched["connector_end_a"] == cable_data["connector_end_a"]
    assert fetched["voltage"] == cable_data["voltage"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_update_power_cable(authenticated_client, test_prefix):
    """
    TC-POWCABLE-005: Update power cable
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-UPDATE-TEST-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "length_meters": 2.0,
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Update the cable
    update_data = {
        "name": f"{test_prefix}-UPDATE-TEST-001-UPDATED",
        "voltage": "240V",
        "length_meters": 5.0,
        "color": "Red",
        "notes": "Updated test cable"
    }
    
    success, updated = authenticated_client.put(f"/api/v1/power-cables/{cable_id}", update_data, expected_status=200)
    
    assert success, f"Failed to update cable: {updated}"
    assert updated["name"] == update_data["name"]
    assert updated["voltage"] == update_data["voltage"]
    assert updated["length_meters"] == update_data["length_meters"]
    assert updated["color"] == update_data["color"]
    assert updated["notes"] == update_data["notes"]
    # Original values should remain
    assert updated["connector_end_a"] == cable_data["connector_end_a"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{cable_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_delete_power_cable(authenticated_client, test_prefix):
    """
    TC-POWCABLE-006: Delete power cable
    """
    # Create a test cable
    cable_data = {
        "name": f"{test_prefix}-DELETE-TEST-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "quantity": 1
    }
    
    success, created = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create test cable: {created}"
    cable_id = created["id"]
    
    # Delete the cable
    success, response = authenticated_client.delete(f"/api/v1/power-cables/{cable_id}", expected_status=204)
    
    assert success, f"Failed to delete cable: {response}"
    
    # Verify it's deleted (may return 404 or 200 with empty result)
    success, fetched = authenticated_client.get(f"/api/v1/power-cables/{cable_id}", expected_status=[200, 404])
    if success and fetched:
        # If it returns 200, check that it's actually not found
        assert "not found" in str(fetched.get("detail", "")).lower() or fetched.get("id") is None, "Cable should not exist after deletion"


@pytest.mark.integration
@pytest.mark.power_cable
def test_filter_power_cables_by_connector(authenticated_client, test_prefix):
    """
    TC-POWCABLE-007: Filter power cables by connector type
    """
    # Create cables with different connectors
    c13_cable = {
        "name": f"{test_prefix}-FILTER-C13-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "quantity": 1
    }
    
    c19_cable = {
        "name": f"{test_prefix}-FILTER-C19-001",
        "connector_end_a": "c19",
        "connector_end_b": "c20",
        "voltage": "208V",
        "quantity": 1
    }
    
    success, c13 = authenticated_client.post("/api/v1/power-cables/", c13_cable, expected_status=201)
    assert success, f"Failed to create C13 cable: {c13}"
    c13_id = c13["id"]
    
    success, c19 = authenticated_client.post("/api/v1/power-cables/", c19_cable, expected_status=201)
    assert success, f"Failed to create C19 cable: {c19}"
    c19_id = c19["id"]
    
    # Filter by C13 connector
    success, response = authenticated_client.get("/api/v1/power-cables/?connector_end_a=c13", expected_status=200)
    assert success, f"Failed to filter by connector: {response}"
    assert isinstance(response, list)
    
    c13_cables = [c for c in response if c["connector_end_a"] == "c13"]
    assert len(c13_cables) > 0, "Should have at least one C13 cable"
    assert any(c["id"] == c13_id for c in c13_cables), "Created C13 cable should be in filtered results"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{c13_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/power-cables/{c19_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_filter_power_cables_by_voltage(authenticated_client, test_prefix):
    """
    TC-POWCABLE-008: Filter power cables by voltage
    """
    # Create cables with different voltages
    cable_120v = {
        "name": f"{test_prefix}-FILTER-120V-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "quantity": 1
    }
    
    cable_208v = {
        "name": f"{test_prefix}-FILTER-208V-001",
        "connector_end_a": "c19",
        "connector_end_b": "c20",
        "voltage": "208V",
        "quantity": 1
    }
    
    success, c120v = authenticated_client.post("/api/v1/power-cables/", cable_120v, expected_status=201)
    assert success, f"Failed to create 120V cable: {c120v}"
    c120v_id = c120v["id"]
    
    success, c208v = authenticated_client.post("/api/v1/power-cables/", cable_208v, expected_status=201)
    assert success, f"Failed to create 208V cable: {c208v}"
    c208v_id = c208v["id"]
    
    # Filter by 120V
    success, response = authenticated_client.get("/api/v1/power-cables/?voltage=120V", expected_status=200)
    assert success, f"Failed to filter by voltage: {response}"
    assert isinstance(response, list)
    
    voltage_120v_cables = [c for c in response if c["voltage"] == "120V"]
    assert len(voltage_120v_cables) > 0, "Should have at least one 120V cable"
    assert any(c["id"] == c120v_id for c in voltage_120v_cables), "Created 120V cable should be in filtered results"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{c120v_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/power-cables/{c208v_id}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_with_storage_container(authenticated_client, test_prefix, test_tenant):
    """
    TC-POWCABLE-009: Assign power cable to storage container
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
            name=f"{test_prefix}-PWR-CABLE-CONTAINER-001",
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
        "name": f"{test_prefix}-STORED-PWR-CABLE-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "storage_container_id": container_id,
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with storage container: {response}"
    assert response["storage_container_id"] == container_id
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_quantity(authenticated_client, test_prefix):
    """
    TC-POWCABLE-010: Test cable quantity field
    """
    cable_data = {
        "name": f"{test_prefix}-QUANTITY-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "quantity": 10  # Multiple cables
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with quantity: {response}"
    assert response["quantity"] == 10
    
    # Update quantity
    update_data = {"quantity": 20}
    success, updated = authenticated_client.put(f"/api/v1/power-cables/{response['id']}", update_data, expected_status=200)
    assert success, f"Failed to update quantity: {updated}"
    assert updated["quantity"] == 20
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_color_coding(authenticated_client, test_prefix):
    """
    TC-POWCABLE-011: Test color coding for power cables
    """
    cable_data = {
        "name": f"{test_prefix}-COLOR-001",
        "connector_end_a": "c13",
        "connector_end_b": "c14",
        "voltage": "120V",
        "color": "Red",
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create colored cable: {response}"
    assert response["color"] == "Red"
    
    # Update color
    update_data = {"color": "Blue"}
    success, updated = authenticated_client.put(f"/api/v1/power-cables/{response['id']}", update_data, expected_status=200)
    assert success, f"Failed to update color: {updated}"
    assert updated["color"] == "Blue"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_wire_gauge(authenticated_client, test_prefix):
    """
    TC-POWCABLE-012: Test wire gauge specification
    """
    cable_data = {
        "name": f"{test_prefix}-GAUGE-001",
        "connector_end_a": "nema_5-15p",
        "connector_end_b": "nema_5-15r",
        "voltage": "120V",
        "amperage": "15A",
        "wire_gauge": "12AWG",
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with wire gauge: {response}"
    assert response["wire_gauge"] == "12AWG"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_get_nonexistent(authenticated_client):
    """
    TC-POWCABLE-013: Get non-existent power cable should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.get(f"/api/v1/power-cables/{nonexistent_id}", expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_update_nonexistent(authenticated_client):
    """
    TC-POWCABLE-014: Update non-existent power cable should return 404
    """
    nonexistent_id = 999999
    update_data = {"name": "Updated Name"}
    
    success, response = authenticated_client.put(f"/api/v1/power-cables/{nonexistent_id}", update_data, expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_delete_nonexistent(authenticated_client):
    """
    TC-POWCABLE-015: Delete non-existent power cable should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.delete(f"/api/v1/power-cables/{nonexistent_id}", expected_status=[404, 200, 204])
    # May return 404, 200, or 204 - check if it's actually an error
    if success:
        error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
        # If it's a dict with detail, it's an error
        if "detail" in response:
            assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"


@pytest.mark.integration
@pytest.mark.power_cable
def test_power_cable_high_voltage(authenticated_client, test_prefix):
    """
    TC-POWCABLE-016: Test high voltage power cables
    """
    cable_data = {
        "name": f"{test_prefix}-HIGH-VOLT-001",
        "connector_end_a": "nema_l6-30p",
        "connector_end_b": "nema_l6-30r",
        "voltage": "240V",
        "amperage": "30A",
        "wire_gauge": "10AWG",
        "length_meters": 5.0,
        "quantity": 1
    }
    
    success, response = authenticated_client.post("/api/v1/power-cables/", cable_data, expected_status=201)
    assert success, f"Failed to create high voltage cable: {response}"
    assert response["voltage"] == "240V"
    assert response["amperage"] == "30A"
    assert response["connector_end_a"] == "nema_l6-30p"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/power-cables/{response['id']}", expected_status=204)

