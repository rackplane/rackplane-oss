"""
Pytest-based PortTemplate API tests.

Tests port template CRUD operations and applying templates to devices.
Part of Phase 1: Port-to-Port Connections.
"""

import pytest


@pytest.mark.integration
@pytest.mark.regression
def test_create_port_template(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-001: Create port template

    REGRESSION: Verifies PortTemplate create endpoint works correctly.
    """
    template_data = {
        "manufacturer": "Cisco",
        "model": f"{test_prefix}-Catalyst-2960-24TT",
        "description": "24-port Gigabit switch",
        "port_definitions": [
            {
                "port_number": str(i),
                "port_type": "rj45",
                "speed_mbps": 1000,
                "duplex": "full",
                "poe_capable": True,
                "poe_max_watts": 15.4
            }
            for i in range(1, 5)  # Create 4 ports for testing
        ]
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)

    assert success, f"Failed to create template: {template}"
    assert template["manufacturer"] == "Cisco"
    assert len(template["port_definitions"]) == 4


@pytest.mark.integration
@pytest.mark.regression
def test_list_port_templates(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-002: List port templates

    REGRESSION: Verifies PortTemplate list endpoint works correctly.
    """
    # Create a template first
    template_data = {
        "manufacturer": "Arista",
        "model": f"{test_prefix}-DCS-7050",
        "description": "Test switch",
        "port_definitions": [
            {"port_number": "1", "port_type": "sfp_plus", "speed_mbps": 10000, "duplex": "full", "poe_capable": False, "poe_max_watts": 0}
        ]
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create template: {template}"

    # List templates
    success, templates = authenticated_client.get("/api/v1/port-templates/", expected_status=200)

    assert success, f"Failed to list templates: {templates}"
    assert isinstance(templates, list)
    assert len(templates) >= 1


@pytest.mark.integration
@pytest.mark.regression
def test_apply_template_to_device(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-003: Apply template to device creates ports

    REGRESSION: Verifies applying a port template creates NetworkPorts on a device.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-TemplateDevice-001",
        "serial_number": f"{test_prefix}-TD-SN-001",
        "asset_type": "switch_device",
        "manufacturer": "Juniper",
        "model": "EX4300",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create a template
    template_data = {
        "manufacturer": "Juniper",
        "model": f"{test_prefix}-EX4300-24T",
        "description": "24-port switch template",
        "port_definitions": [
            {
                "port_number": str(i),
                "port_type": "rj45",
                "speed_mbps": 1000,
                "duplex": "full",
                "poe_capable": False,
                "poe_max_watts": 0
            }
            for i in range(1, 9)  # Create 8 ports for testing
        ]
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create template: {template}"
    template_id = template["id"]

    # Apply template to device
    apply_data = {
        "asset_id": device_id,
        "template_id": template_id,
        "overwrite": False
    }

    success, result = authenticated_client.post("/api/v1/port-templates/apply", apply_data, expected_status=200)

    assert success, f"Failed to apply template: {result}"
    assert result["ports_created"] == 8

    # Verify ports were created
    success, ports_result = authenticated_client.get(f"/api/v1/network-ports/?asset_id={device_id}", expected_status=200)
    assert success, f"Failed to list ports: {ports_result}"
    assert ports_result["total"] == 8


@pytest.mark.integration
@pytest.mark.regression
def test_apply_template_overwrite(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-004: Apply template with overwrite replaces existing ports

    REGRESSION: Verifies overwrite flag works correctly when applying templates.
    """
    # Create a device
    device_data = {
        "asset_tag": f"{test_prefix}-OverwriteDevice-001",
        "serial_number": f"{test_prefix}-OD-SN-001",
        "asset_type": "switch_device",
        "manufacturer": "Dell",
        "model": "S4048",
        "status": "active"
    }

    success, device = authenticated_client.post("/api/v1/assets/", device_data, expected_status=201)
    assert success, f"Failed to create device: {device}"
    device_id = device["id"]

    # Create an initial port manually
    port_data = {
        "asset_id": device_id,
        "port_number": "manual-1",
        "port_type": "RJ45",  # Use uppercase to match PortType enum
        "speed_mbps": 100
    }
    success, port = authenticated_client.post("/api/v1/network-ports/", port_data, expected_status=201)
    assert success, f"Failed to create manual port: {port}"

    # Create a template
    template_data = {
        "manufacturer": "Dell",
        "model": f"{test_prefix}-S4048-ON",
        "description": "48-port switch template",
        "port_definitions": [
            {
                "port_number": str(i),
                "port_type": "QSFP28",  # Use uppercase to match PortType enum
                "speed_mbps": 100000,
                "duplex": "full",
                "poe_capable": False,
                "poe_max_watts": 0
            }
            for i in range(1, 5)  # Create 4 ports
        ]
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create template: {template}"
    template_id = template["id"]

    # Apply template WITHOUT overwrite (should fail - ports already exist)
    apply_data = {
        "asset_id": device_id,
        "template_id": template_id,
        "overwrite": False
    }

    success, error_result = authenticated_client.post("/api/v1/port-templates/apply", apply_data, expected_status=400)
    assert not success or "already has" in str(error_result), f"Expected rejection without overwrite: {error_result}"

    # Apply template WITH overwrite (should succeed)
    apply_data["overwrite"] = True
    success, result = authenticated_client.post("/api/v1/port-templates/apply", apply_data, expected_status=200)

    assert success, f"Failed to apply template with overwrite: {result}"
    assert result["ports_created"] == 4

    # Verify old manual port was replaced
    success, ports_result = authenticated_client.get(f"/api/v1/network-ports/?asset_id={device_id}", expected_status=200)
    assert success, f"Failed to list ports: {ports_result}"
    assert ports_result["total"] == 4  # Only template ports, not the manual one


@pytest.mark.integration
@pytest.mark.regression
def test_duplicate_template_rejected(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-005: Reject duplicate manufacturer+model combination

    REGRESSION: Verifies duplicate template validation works correctly.
    """
    # Create first template
    template_data = {
        "manufacturer": "Ubiquiti",
        "model": f"{test_prefix}-EdgeSwitch-48",
        "description": "48-port switch",
        "port_definitions": []
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create first template: {template}"

    # Try to create duplicate template (same manufacturer + model)
    success, error = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=400)

    assert not success or "already exists" in str(error), f"Expected duplicate rejection, got: {error}"


@pytest.mark.integration
@pytest.mark.regression
def test_get_port_template(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-006: Get specific port template by ID

    REGRESSION: Verifies PortTemplate get endpoint works correctly.
    """
    # Create a template
    template_data = {
        "manufacturer": "Mellanox",
        "model": f"{test_prefix}-SN2700",
        "description": "32-port 100GbE switch",
        "port_definitions": [
            {"port_number": "1", "port_type": "qsfp28", "speed_mbps": 100000, "duplex": "full", "poe_capable": False, "poe_max_watts": 0}
        ]
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create template: {template}"
    template_id = template["id"]

    # Get the template
    success, fetched = authenticated_client.get(f"/api/v1/port-templates/{template_id}", expected_status=200)

    assert success, f"Failed to get template: {fetched}"
    assert fetched["id"] == template_id
    assert fetched["manufacturer"] == "Mellanox"
    assert len(fetched["port_definitions"]) == 1


@pytest.mark.integration
@pytest.mark.regression
def test_delete_port_template(authenticated_client, test_prefix):
    """
    TC-TEMPLATE-007: Delete port template

    REGRESSION: Verifies PortTemplate delete endpoint works correctly.
    """
    # Create a template
    template_data = {
        "manufacturer": "Netgear",
        "model": f"{test_prefix}-XS728T",
        "description": "28-port switch",
        "port_definitions": []
    }

    success, template = authenticated_client.post("/api/v1/port-templates/", template_data, expected_status=201)
    assert success, f"Failed to create template: {template}"
    template_id = template["id"]

    # Delete the template
    success, _ = authenticated_client.delete(f"/api/v1/port-templates/{template_id}", expected_status=204)
    assert success, "Failed to delete template"

    # Verify template is deleted
    success, result = authenticated_client.get(f"/api/v1/port-templates/{template_id}", expected_status=404)
    assert not success or "not found" in str(result).lower(), "Template should be deleted"
