"""
Pytest-based cable assembly tests.

Tests cable assembly creation, deployment, and undeployment.
"""

import pytest


@pytest.mark.regression
@pytest.mark.integration
def test_create_cable_assembly(authenticated_client, test_prefix):
    """
    TC-ASSEMBLY-001: Create a cable assembly from 3 assets.
    
    This test verifies that a cable assembly can be created
    by bundling 1 fiber cable + 2 transceivers.
    """
    # Create fiber cable
    fiber_data = {
        "asset_tag": f"{test_prefix}-FIBER-001",
        "serial_number": f"{test_prefix}-FIB-SN-001",
        "asset_type": "fiber_cable",
        "manufacturer": "Corning",
        "model": "LC-LC SMF 10m",
        "status": "in_storage"
    }
    success, fiber = authenticated_client.post("/api/v1/assets/", fiber_data, expected_status=201)
    assert success, f"Failed to create fiber cable: {fiber}"
    
    # Create transceiver A
    trans_a_data = {
        "asset_tag": f"{test_prefix}-TRANS-A-001",
        "serial_number": f"{test_prefix}-TRA-SN-001",
        "asset_type": "optical_transceiver",
        "manufacturer": "Intel",
        "model": "X710-SR",
        "status": "in_storage"
    }
    success, trans_a = authenticated_client.post("/api/v1/assets/", trans_a_data, expected_status=201)
    assert success, f"Failed to create transceiver A: {trans_a}"
    
    # Create transceiver B
    trans_b_data = {
        "asset_tag": f"{test_prefix}-TRANS-B-001",
        "serial_number": f"{test_prefix}-TRB-SN-001",
        "asset_type": "optical_transceiver",
        "manufacturer": "Intel",
        "model": "X710-SR",
        "status": "in_storage"
    }
    success, trans_b = authenticated_client.post("/api/v1/assets/", trans_b_data, expected_status=201)
    assert success, f"Failed to create transceiver B: {trans_b}"
    
    # Create assembly
    assembly_data = {
        "name": f"{test_prefix}-100G-10M-Assembly",
        "description": "100G fiber assembly with transceivers",
        "fiber_cable_id": fiber["id"],
        "transceiver_a_id": trans_a["id"],
        "transceiver_b_id": trans_b["id"]
    }
    success, assembly = authenticated_client.post("/api/v1/cable-assemblies/", assembly_data, expected_status=201)
    assert success, f"Failed to create cable assembly: {assembly}"
    
    assert assembly["name"] == assembly_data["name"]
    assert assembly["fiber_cable_id"] == fiber["id"]
    assert assembly["transceiver_a_id"] == trans_a["id"]
    assert assembly["transceiver_b_id"] == trans_b["id"]
    assert assembly["status"] == "available"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/cable-assemblies/{assembly['id']}", expected_status=204)
    authenticated_client.delete(f"/api/v1/assets/{fiber['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{trans_a['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{trans_b['id']}", expected_status=200)


@pytest.mark.regression
@pytest.mark.integration
def test_list_cable_assemblies(authenticated_client, test_prefix):
    """
    TC-ASSEMBLY-002: List cable assemblies.
    """
    success, assemblies = authenticated_client.get("/api/v1/cable-assemblies/", expected_status=200)
    assert success, f"Failed to list assemblies: {assemblies}"
    assert isinstance(assemblies, list)


@pytest.mark.regression
@pytest.mark.integration  
def test_install_transceiver_in_port(authenticated_client, test_prefix):
    """
    TC-ASSEMBLY-003: Install transceiver into a port.
    
    Tests the install-transceiver endpoint.
    """
    # Create server asset
    server_data = {
        "asset_tag": f"{test_prefix}-SRV-TRANS-001",
        "serial_number": f"{test_prefix}-SRV-T-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "R750",
        "status": "deployed"
    }
    success, server = authenticated_client.post("/api/v1/assets/", server_data, expected_status=201)
    assert success, f"Failed to create server: {server}"
    
    # Create port on server
    port_data = {
        "asset_id": server["id"],
        "port_number": "eth0",
        "port_type": "SFP_PLUS"
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create port: {port}"
    
    # Create transceiver
    trans_data = {
        "asset_tag": f"{test_prefix}-TRANS-PORT-001",
        "serial_number": f"{test_prefix}-TRP-SN-001",
        "asset_type": "optical_transceiver",
        "manufacturer": "Intel",
        "model": "X710-SR",
        "status": "in_storage"
    }
    success, trans = authenticated_client.post("/api/v1/assets/", trans_data, expected_status=201)
    assert success, f"Failed to create transceiver: {trans}"
    
    # Install transceiver into port
    success, result = authenticated_client.post(
        f"/api/v1/network-ports/{port['id']}/install-transceiver",
        {},  # Empty body - params go in query string
        params={"transceiver_id": trans["id"]},
        expected_status=200
    )
    assert success, f"Failed to install transceiver: {result}"
    assert "installed" in result["message"].lower()
    
    # Verify port has transceiver
    success, updated_port = authenticated_client.get(f"/api/v1/network-ports/{port['id']}", expected_status=200)
    assert success
    assert updated_port["installed_transceiver_id"] == trans["id"]
    
    # Uninstall transceiver
    success, uninstall_result = authenticated_client.delete(
        f"/api/v1/network-ports/{port['id']}/uninstall-transceiver",
        expected_status=200
    )
    assert success, f"Failed to uninstall: {uninstall_result}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-ports/{port['id']}", expected_status=204)
    authenticated_client.delete(f"/api/v1/assets/{server['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{trans['id']}", expected_status=200)
