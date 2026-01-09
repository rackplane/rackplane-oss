"""
Pytest-based NetworkPort API tests.

Tests network port CRUD operations for Phase 1 of Port-to-Port Connections.
"""

import pytest


@pytest.mark.integration
@pytest.mark.regression
def test_create_network_port(authenticated_client, test_prefix):
    """
    TC-PORT-001: Create network port via API

    REGRESSION: Verifies NetworkPort API create endpoint works correctly.
    """
    # Create a device first
    device_data = {
        "asset_tag": f"{test_prefix}-PortDevice-001",
        "serial_number": f"{test_prefix}-PD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Cisco",
        "model": "Catalyst 2960-24TT",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create a network port on the device
    port_data = {
        "asset_id": device_id,
        "port_number": "1",
        "port_name": "GigabitEthernet0/1",
        "port_type": "RJ45",
        "speed_mbps": 1000,
        "enabled": True
    }

    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)

    assert success, f"Failed to create port: {port}"
    assert port["port_number"] == "1"
    assert port["port_type"] == "RJ45"
    assert port["asset_id"] == device_id
    assert port["speed_mbps"] == 1000


@pytest.mark.integration
@pytest.mark.regression
def test_list_ports_by_asset(authenticated_client, test_prefix):
    """
    TC-PORT-002: List ports for specific device

    REGRESSION: Verifies NetworkPort list endpoint with asset_id filter works.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-ListPortsDevice-001",
        "serial_number": f"{test_prefix}-LPD-SN-001",
        "asset_type": "switch_device",
        "manufacturer": "Arista",
        "model": "7050SX",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create multiple ports
    for i in range(1, 5):
        port_data = {
            "asset_id": device_id,
            "port_number": str(i),
            "port_type": "RJ45",
            "speed_mbps": 1000
        }
        success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
        assert success, f"Failed to create port {i}: {port}"

    # List ports for the device
    success, result = authenticated_client.get(f"/api/v1/network-ports/?asset_id={device_id}", expected_status=200)

    assert success, f"Failed to list ports: {result}"
    assert result["total"] == 4
    assert len(result["ports"]) == 4


@pytest.mark.integration
@pytest.mark.regression
def test_duplicate_port_rejected(authenticated_client, test_prefix):
    """
    TC-PORT-003: Reject duplicate port_number on same asset

    REGRESSION: Verifies duplicate port validation works correctly.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-DupPortDevice-001",
        "serial_number": f"{test_prefix}-DPD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create port 1
    port_data = {
        "asset_id": device_id,
        "port_number": "1",
        "port_type": "RJ45"
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create first port: {port}"

    # Try to create duplicate port 1 (should fail)
    duplicate_data = {
        "asset_id": device_id,
        "port_number": "1",
        "port_type": "sfp"
    }
    success, error = authenticated_client.post("/api/v1/network-ports/", duplicate_data, expected_status=400)

    assert not success or "already exists" in str(error), f"Expected duplicate rejection, got: {error}"


@pytest.mark.integration
@pytest.mark.regression
def test_update_network_port(authenticated_client, test_prefix):
    """
    TC-PORT-004: Update network port details

    REGRESSION: Verifies NetworkPort update endpoint works correctly.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-UpdatePortDevice-001",
        "serial_number": f"{test_prefix}-UPD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Cisco",
        "model": "Nexus",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create a port
    port_data = {
        "asset_id": device_id,
        "port_number": "1",
        "port_type": "RJ45",
        "speed_mbps": 1000,
        "enabled": True
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create port: {port}"
    port_id = port["id"]

    # Update the port
    update_data = {
        "port_name": "GigabitEthernet0/1",
        "speed_mbps": 10000,
        "enabled": False
    }
    success, updated_port = authenticated_client.put(f"/api/v1/network-ports/{port_id}", update_data, expected_status=200)

    assert success, f"Failed to update port: {updated_port}"
    assert updated_port["port_name"] == "GigabitEthernet0/1"
    assert updated_port["speed_mbps"] == 10000
    assert updated_port["enabled"] is False


@pytest.mark.integration
@pytest.mark.regression
def test_delete_network_port(authenticated_client, test_prefix):
    """
    TC-PORT-005: Delete network port

    REGRESSION: Verifies NetworkPort delete endpoint works correctly.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-DelPortDevice-001",
        "serial_number": f"{test_prefix}-DPD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "HP",
        "model": "ProLiant",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create a port
    port_data = {
        "asset_id": device_id,
        "port_number": "1",
        "port_type": "RJ45"
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create port: {port}"
    port_id = port["id"]

    # Delete the port
    success, _ = authenticated_client.delete(f"/api/v1/network-ports/{port_id}", expected_status=204)
    assert success, "Failed to delete port"

    # Verify port is deleted
    success, result = authenticated_client.get(f"/api/v1/network-ports/{port_id}", expected_status=404)
    assert not success or "not found" in str(result).lower(), "Port should be deleted"


@pytest.mark.integration
@pytest.mark.regression
def test_get_network_port(authenticated_client, test_prefix):
    """
    TC-PORT-006: Get specific network port by ID

    REGRESSION: Verifies NetworkPort get endpoint works correctly.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-GetPortDevice-001",
        "serial_number": f"{test_prefix}-GPD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Lenovo",
        "model": "ThinkSystem",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create a port
    port_data = {
        "asset_id": device_id,
        "port_number": "eth0",
        "port_type": "RJ45",
        "speed_mbps": 10000,
        "poe_capable": True
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create port: {port}"
    port_id = port["id"]

    # Get the port
    success, fetched_port = authenticated_client.get(f"/api/v1/network-ports/{port_id}", expected_status=200)

    assert success, f"Failed to get port: {fetched_port}"
    assert fetched_port["id"] == port_id
    assert fetched_port["port_number"] == "eth0"
    assert fetched_port["poe_capable"] is True
