"""
Pytest-based connection/cable management tests.

Tests cable connections, circuit views, and lifecycle integration.
"""

import pytest
import time
import uuid


@pytest.mark.integration
@pytest.mark.connection
def test_create_connection(authenticated_client, test_prefix):
    """
    TC-CONNECTION-001: Create cable connection
    
    This test verifies that cables can be connected to devices.
    """
    # Create a cable
    cable_data = {
        "asset_tag": f"{test_prefix}-Cable-001",
        "serial_number": f"{test_prefix}-CBL-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "active"
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable: {cable}"
    cable_id = cable["id"]
    
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-Device-001",
        "serial_number": f"{test_prefix}-DEV-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]
    
    # Connect cable to device
    connect_data = {
        "cable_id": cable_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    
    success, connection = authenticated_client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    
    assert success, f"Failed to create connection: {connection}"
    assert "connection" in connection, f"Response missing 'connection': {connection}"
    assert connection["connection"]["cable_asset_id"] == cable_id
    assert connection["connection"]["device_asset_id"] == device_id
    assert "end_label" in connection, f"Response missing 'end_label': {connection}"
    assert connection["end_label"] in ["A", "B"], f"end_label should be 'A' or 'B', got {connection['end_label']}"
    
    # Cleanup: Delete connection
    connection_id = connection["connection"]["id"]
    authenticated_client.delete(f"/api/v1/connections/{connection_id}", expected_status=200)
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.connection
def test_connection_auto_deploy_cable(authenticated_client, test_prefix):
    """
    TC-CONNECTION-002: Test auto-deploy when connecting cable from storage
    
    This test verifies that cables in storage are automatically deployed when connected.
    """
    # Create a storage box
    box_data = {
        "asset_tag": f"{test_prefix}-AutoDeployBox-001",
        "serial_number": f"{test_prefix}-ADB-SN-001",
        "asset_type": "storage_device",
        "manufacturer": "Generic",
        "model": "Cable Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create a cable in storage
    cable_data = {
        "asset_tag": f"{test_prefix}-AutoDeployCable-001",
        "serial_number": f"{test_prefix}-ADC-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "in_storage",
        "container_id": box_id
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable: {cable}"
    cable_id = cable["id"]
    
    # Verify cable is in storage
    success, fetched_cable = authenticated_client.get(f"/api/v1/assets/{cable_id}", expected_status=200)
    assert success, f"Failed to fetch cable: {fetched_cable}"
    assert fetched_cable["status"] == "in_storage", f"Expected status 'in_storage', got {fetched_cable['status']}"
    assert fetched_cable["container_id"] == box_id, f"Expected container_id={box_id}, got {fetched_cable['container_id']}"
    
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-AutoDeployDevice-001",
        "serial_number": f"{test_prefix}-ADD-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]
    
    # Connect cable to device (should trigger auto-deploy)
    connect_data = {
        "cable_id": cable_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    
    success, connection = authenticated_client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    assert success, f"Failed to create connection: {connection}"
    
    # Verify cable was auto-deployed
    success, deployed_cable = authenticated_client.get(f"/api/v1/assets/{cable_id}", expected_status=200)
    assert success, f"Failed to fetch deployed cable: {deployed_cable}"
    assert deployed_cable["status"] == "deployed", \
        f"Expected status 'deployed' after connection, got {deployed_cable['status']}"
    assert deployed_cable["container_id"] is None, \
        f"Expected container_id=None after deployment, got {deployed_cable['container_id']}"
    
    # Cleanup: Delete connection
    connection_id = connection["connection"]["id"]
    authenticated_client.delete(f"/api/v1/connections/{connection_id}", expected_status=200)
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.connection
def test_get_cable_connections(authenticated_client, test_prefix):
    """
    TC-CONNECTION-003: Get all connections for a cable
    
    This test verifies that cable connections can be retrieved.
    """
    # Create a cable
    cable_data = {
        "asset_tag": f"{test_prefix}-GetConnCable-001",
        "serial_number": f"{test_prefix}-GCC-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "active"
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable: {cable}"
    cable_id = cable["id"]
    
    # Create two devices
    devices = []
    for i in range(2):
        device_data = {
            "asset_tag": f"{test_prefix}-GetConnDevice-{i+1}",
            "serial_number": f"{test_prefix}-GCD-SN-{i+1}",
            "asset_type": "server_device",
            "manufacturer": "Dell",
            "model": "PowerEdge",
            "status": "active"
        }
        success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
        assert success, f"Failed to create device {i+1}: {device}"
        devices.append(device["id"])
    
    # Connect cable to both devices (both ends)
    connections = []
    for i, device_id in enumerate(devices):
        connect_data = {
            "cable_id": cable_id,
            "device_id": device_id,
            "port_label": f"Port {i+1}"
        }
        success, connection = authenticated_client.post("/api/v1/connections/connect", connect_data, expected_status=201)
        assert success, f"Failed to create connection {i+1}: {connection}"
        connections.append(connection["connection"]["id"])
    
    # Get all connections for the cable
    success, cable_connections = authenticated_client.get(f"/api/v1/connections/cable/{cable_id}", expected_status=200)
    
    assert success, f"Failed to get cable connections: {cable_connections}"
    assert isinstance(cable_connections, list), f"Expected list, got {type(cable_connections)}"
    assert len(cable_connections) == 2, f"Expected 2 connections, got {len(cable_connections)}"
    
    # Verify both ends are connected
    end_labels = [conn["end_label"] for conn in cable_connections]
    assert "A" in end_labels, "Expected end 'A' to be connected"
    assert "B" in end_labels, "Expected end 'B' to be connected"
    
    # Cleanup: Delete connections
    for conn_id in connections:
        authenticated_client.delete(f"/api/v1/connections/{conn_id}", expected_status=200)
    
    # Cleanup handled by test_tenant fixture (cascade delete)


@pytest.mark.integration
@pytest.mark.connection
def test_get_all_circuits(authenticated_client, test_prefix):
    """
    TC-CONNECTION-004: Get all circuits (connection list view)
    
    This test verifies that the circuit view endpoint works.
    """
    # Create a cable
    cable_data = {
        "asset_tag": f"{test_prefix}-CircuitCable-001",
        "serial_number": f"{test_prefix}-CIR-SN-001",
        "asset_type": "ethernet_cable",
        "manufacturer": "Generic",
        "model": "CAT6",
        "status": "active"
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable: {cable}"
    cable_id = cable["id"]
    
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-CircuitDevice-001",
        "serial_number": f"{test_prefix}-CID-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]
    
    # Connect cable to device
    connect_data = {
        "cable_id": cable_id,
        "device_id": device_id,
        "port_label": "Port 1"
    }
    
    success, connection = authenticated_client.post("/api/v1/connections/connect", connect_data, expected_status=201)
    assert success, f"Failed to create connection: {connection}"
    connection_id = connection["connection"]["id"]
    
    # Get all circuits
    success, circuits = authenticated_client.get("/api/v1/connections/circuits", expected_status=200)
    
    assert success, f"Failed to get circuits: {circuits}"
    assert isinstance(circuits, list), f"Expected list, got {type(circuits)}"
    
    # Find our circuit
    our_circuit = None
    for circuit in circuits:
        if circuit.get("cable", {}).get("id") == cable_id:
            our_circuit = circuit
            break
    
    assert our_circuit is not None, "Our circuit should be in the list"
    assert "cable" in our_circuit, "Circuit should have 'cable' field"
    assert "end_a" in our_circuit or "end_b" in our_circuit, "Circuit should have at least one end"
    
    # Cleanup: Delete connection
    authenticated_client.delete(f"/api/v1/connections/{connection_id}", expected_status=200)
    
    # Cleanup handled by test_tenant fixture (cascade delete)

