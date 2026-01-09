# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Cable Creation Test Suite
Tests for creating cables with various statuses and configurations.

This test suite specifically verifies:
- Cables can be created without storage box validation errors
- Cables can be created with different statuses (deployed, active, in_storage)
- Cables can have manual serial numbers or auto-generated ones
- Storage box validation does not incorrectly apply to cables
"""

import pytest
from app.models.asset import AssetStatus


@pytest.mark.integration
@pytest.mark.cable
def test_create_dac_cable_deployed_status(authenticated_client, test_prefix):
    """
    TC-CABLE-001: Create DAC cable with deployed status (no storage box).
    
    This test would have caught the storage box validation bug where cables
    with asset_tags starting with "DAC-" were incorrectly identified as storage boxes.
    """
    cable_data = {
        "asset_tag": f"{test_prefix}-DAC-DEPLOYED-001",
        "serial_number": f"{test_prefix}-DAC-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "DAC Cable",
        "status": "deployed",
        "custom_fields": {
            "dac_speed": "100G",
            "dac_connector_a": "QSFP28",
            "dac_connector_b": "QSFP28",
            "cable_length": "3M"
        }
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create DAC cable with deployed status: {cable}"
    assert cable["status"] == "deployed"
    assert cable["asset_type"] == "dac_cable"
    assert cable["min_stock_threshold"] is None, "Cables should not have min_stock_threshold"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{cable['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.cable
def test_create_fiber_cable_active_status(authenticated_client, test_prefix):
    """
    TC-CABLE-002: Create fiber cable with active status (no storage box).
    
    Verifies fiber cables can be created without storage box validation errors.
    """
    cable_data = {
        "asset_tag": f"{test_prefix}-FBR-ACTIVE-001",
        "serial_number": f"{test_prefix}-FBR-SN-001",
        "asset_type": "fiber_cable",
        "manufacturer": "Generic",
        "model": "Fiber Cable",
        "status": "active",
        "custom_fields": {
            "fiber_type": "OM4",
            "fiber_connector_a": "LC",
            "fiber_connector_b": "LC",
            "cable_length": "5M"
        }
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create fiber cable with active status: {cable}"
    assert cable["status"] == "active"
    assert cable["asset_type"] == "fiber_cable"
    assert cable["min_stock_threshold"] is None, "Cables should not have min_stock_threshold"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{cable['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.cable
def test_create_dac_cable_with_auto_generated_serial(authenticated_client, test_prefix):
    """
    TC-CABLE-003: Create DAC cable with auto-generated serial number.
    
    Verifies that cables can use the serial generation API endpoint.
    """
    # First, generate serial number and asset tag
    success, serial_data = authenticated_client.post(
        "/api/v1/assets/generate-serial",
        {"asset_type": "dac_cable"},
        expected_status=200
    )
    assert success, f"Failed to generate serial: {serial_data}"
    assert "serial_number" in serial_data
    assert "asset_tag" in serial_data
    
    # Create cable with auto-generated serial
    cable_data = {
        "asset_tag": serial_data["asset_tag"],
        "serial_number": serial_data["serial_number"],
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "DAC Cable",
        "status": "deployed",
        "custom_fields": {
            "dac_speed": "100G",
            "dac_connector_a": "QSFP28",
            "dac_connector_b": "QSFP28"
        }
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with auto-generated serial: {cable}"
    assert cable["serial_number"] == serial_data["serial_number"]
    assert cable["asset_tag"] == serial_data["asset_tag"]
    assert cable["min_stock_threshold"] is None, "Cables should not have min_stock_threshold"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{cable['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.cable
def test_create_dac_cable_with_manual_serial(authenticated_client, test_prefix):
    """
    TC-CABLE-004: Create DAC cable with manual serial number.
    
    Verifies that cables can be created with manually entered serial numbers
    (some DACs come with existing serial numbers from manufacturer).
    """
    cable_data = {
        "asset_tag": f"{test_prefix}-DAC-MANUAL-001",
        "serial_number": "MANUFACTURER-SN-12345",  # Manual serial from manufacturer
        "asset_type": "dac_cable",
        "manufacturer": "Cisco",
        "model": "QSFP-H40G-CU3M",
        "status": "deployed",
        "custom_fields": {
            "dac_speed": "40G",
            "dac_connector_a": "QSFP+",
            "dac_connector_b": "QSFP+",
            "cable_length": "3M"
        }
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable with manual serial: {cable}"
    assert cable["serial_number"] == "MANUFACTURER-SN-12345"
    assert cable["min_stock_threshold"] is None, "Cables should not have min_stock_threshold"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{cable['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.cable
def test_create_cable_cannot_have_min_stock_threshold(authenticated_client, test_prefix):
    """
    TC-CABLE-005: Verify cables cannot have min_stock_threshold set.
    
    Cables should never be storage boxes - they go INTO storage boxes.
    """
    cable_data = {
        "asset_tag": f"{test_prefix}-DAC-NO-THRESHOLD-001",
        "serial_number": f"{test_prefix}-DAC-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "DAC Cable",
        "status": "deployed",
        "min_stock_threshold": 5  # This should be rejected
    }
    
    # Don't pass expected_status - we want to check the actual status
    # The API should return 400 for invalid cable data
    success, response = authenticated_client.post("/api/v1/assets/", cable_data)
    
    # Should fail (not 200/201) when cable has invalid min_stock_threshold
    assert not success, f"Cable with min_stock_threshold should be rejected: {response}"
    # Check the error detail
    error_detail = str(response.get("detail", "")).lower() if isinstance(response, dict) else str(response).lower()
    assert "cannot have min_stock_threshold" in error_detail or \
           "cables should be placed inside storage boxes" in error_detail or \
           "400" in str(response).lower(), \
           f"Expected error about cables not having min_stock_threshold, got: {response}"


@pytest.mark.integration
@pytest.mark.cable
def test_create_cable_with_storage_box(authenticated_client, test_prefix, test_tenant):
    """
    TC-CABLE-006: Create cable and assign it to a storage box.
    
    Verifies cables can be placed in storage boxes without validation errors.
    """
    # First, ensure storage_box asset type exists
    from app.core.database import SessionLocal
    from app.models.asset_type import AssetTypeModel
    from app.core.tenant_query import apply_tenant_filter
    from app.core.tenant import set_current_tenant_id, clear_tenant_id
    
    # Set tenant context before creating database session
    set_current_tenant_id(test_tenant["id"])
    
    db = SessionLocal()
    try:
        # Check if storage_box type exists
        query = db.query(AssetTypeModel).filter(AssetTypeModel.name == 'storage_box')
        query = apply_tenant_filter(query, AssetTypeModel)
        storage_box_type = query.first()
        
        if not storage_box_type:
            # Create storage_box asset type
            storage_box_type = AssetTypeModel(
                name='storage_box',
                display_name='Storage Box',
                description='Storage box for holding inventory items like cables',
                tenant_id=test_tenant["id"]
            )
            db.add(storage_box_type)
            db.commit()
            db.refresh(storage_box_type)
    finally:
        clear_tenant_id()
        db.close()
    
    # Now create a storage box
    box_data = {
        "asset_tag": f"{test_prefix}-STORAGE-BOX-001",
        "serial_number": f"{test_prefix}-BOX-SN-001",
        "asset_type": "storage_box",
        "manufacturer": "Generic",
        "model": "Storage Bin",
        "status": "active",
        "min_stock_threshold": 10
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create cable in storage box
    cable_data = {
        "asset_tag": f"{test_prefix}-DAC-IN-BOX-001",
        "serial_number": f"{test_prefix}-DAC-SN-001",
        "asset_type": "dac_cable",
        "manufacturer": "Generic",
        "model": "DAC Cable",
        "status": "in_storage",
        "container_id": box_id,
        "custom_fields": {
            "dac_speed": "100G",
            "dac_connector_a": "QSFP28",
            "dac_connector_b": "QSFP28"
        }
    }
    
    success, cable = authenticated_client.post("/api/v1/assets/", cable_data, expected_status=201)
    assert success, f"Failed to create cable in storage box: {cable}"
    assert cable["container_id"] == box_id
    assert cable["status"] == "in_storage"
    assert cable["min_stock_threshold"] is None, "Cables should not have min_stock_threshold"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{cable['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{box_id}", expected_status=200)

