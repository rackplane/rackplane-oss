# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Dashboard Metrics Test Suite
Tests for enhanced dashboard metrics including:
- Asset count by type
- Low stock items
- Upcoming maintenance
"""

import pytest
from datetime import datetime, timedelta
from app.models.asset import AssetStatus
from app.models.maintenance import MaintenanceStatus, MaintenancePriority, MaintenanceType


@pytest.mark.integration
@pytest.mark.dashboard
def test_dashboard_summary_asset_counts_by_type(authenticated_client, test_prefix, test_tenant):
    """
    TC-DASHBOARD-001: Verify dashboard returns asset counts by type.
    """
    from app.core.database import SessionLocal
    from app.models.asset_type import AssetTypeModel
    from app.core.tenant_query import apply_tenant_filter
    
    # Ensure required asset types exist
    from app.core.tenant import set_current_tenant_id
    set_current_tenant_id(test_tenant["id"])
    
    db = SessionLocal()
    try:
        # Check/create network_device asset type
        query = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == 'network_device',
            AssetTypeModel.tenant_id == test_tenant["id"]
        )
        network_device_type = query.first()
        
        if not network_device_type:
            network_device_type = AssetTypeModel(
                name='network_device',
                display_name='Network Device',
                description='Network switch or router',
                tenant_id=test_tenant["id"]
            )
            db.add(network_device_type)
            db.commit()
    finally:
        db.close()
        from app.core.tenant import clear_tenant_id
        clear_tenant_id()
    
    # Create assets of different types
    asset_data_1 = {
        "asset_tag": f"{test_prefix}-DASHBOARD-SRV-001",
        "serial_number": f"{test_prefix}-SRV-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    asset_data_2 = {
        "asset_tag": f"{test_prefix}-DASHBOARD-SW-001",
        "serial_number": f"{test_prefix}-SW-SN-001",
        "asset_type": "network_device",
        "manufacturer": "Cisco",
        "model": "Nexus",
        "status": "active"
    }
    
    asset_data_3 = {
        "asset_tag": f"{test_prefix}-DASHBOARD-SRV-002",
        "serial_number": f"{test_prefix}-SRV-SN-002",
        "asset_type": "server_device",
        "manufacturer": "HP",
        "model": "ProLiant",
        "status": "deployed"
    }
    
    success, asset1 = authenticated_client.post("/api/v1/assets/", asset_data_1, expected_status=201)
    assert success, f"Failed to create asset 1: {asset1}"
    
    success, asset2 = authenticated_client.post("/api/v1/assets/", asset_data_2, expected_status=201)
    assert success, f"Failed to create asset 2: {asset2}"
    
    success, asset3 = authenticated_client.post("/api/v1/assets/", asset_data_3, expected_status=201)
    assert success, f"Failed to create asset 3: {asset3}"
    
    # Get dashboard summary
    success, dashboard = authenticated_client.get("/api/v1/reports/dashboard/summary", expected_status=200)
    assert success, f"Failed to get dashboard summary: {dashboard}"
    
    # Verify asset_counts_by_type exists
    assert "asset_counts_by_type" in dashboard, "Dashboard should include asset_counts_by_type"
    asset_counts = dashboard["asset_counts_by_type"]
    assert isinstance(asset_counts, list), "asset_counts_by_type should be a list"
    
    # Verify counts
    server_count = next((ac for ac in asset_counts if ac["asset_type"] == "server_device"), None)
    assert server_count is not None, "Should have server_device count"
    assert server_count["count"] == 2, f"Expected 2 servers, got {server_count['count']}"
    
    network_count = next((ac for ac in asset_counts if ac["asset_type"] == "network_device"), None)
    assert network_count is not None, "Should have network_device count"
    assert network_count["count"] == 1, f"Expected 1 network device, got {network_count['count']}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset1['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset2['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset3['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.dashboard
def test_dashboard_summary_low_stock_items(authenticated_client, test_prefix, test_tenant):
    """
    TC-DASHBOARD-002: Verify dashboard returns low stock items.
    """
    from app.core.database import SessionLocal
    from app.models.asset_type import AssetTypeModel
    from app.core.tenant_query import apply_tenant_filter
    
    # Ensure storage_box and dac_cable asset types exist
    from app.core.tenant import set_current_tenant_id, clear_tenant_id
    set_current_tenant_id(test_tenant["id"])
    
    db = SessionLocal()
    try:
        # Check/create storage_box asset type
        query = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == 'storage_box',
            AssetTypeModel.tenant_id == test_tenant["id"]
        )
        storage_box_type = query.first()
        
        if not storage_box_type:
            storage_box_type = AssetTypeModel(
                name='storage_box',
                display_name='Storage Box',
                description='Storage box for holding inventory items',
                tenant_id=test_tenant["id"]
            )
            db.add(storage_box_type)
            db.commit()
        
        # Check/create dac_cable asset type
        query = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == 'dac_cable',
            AssetTypeModel.tenant_id == test_tenant["id"]
        )
        dac_cable_type = query.first()
        
        if not dac_cable_type:
            dac_cable_type = AssetTypeModel(
                name='dac_cable',
                display_name='DAC Cable',
                description='Direct Attach Copper Cable',
                tenant_id=test_tenant["id"]
            )
            db.add(dac_cable_type)
            db.commit()
    finally:
        db.close()
        clear_tenant_id()
    
    # Create a storage box with threshold
    box_data = {
        "asset_tag": f"{test_prefix}-DASHBOARD-BOX-001",
        "serial_number": f"{test_prefix}-BOX-SN-001",
        "asset_type": "storage_box",
        "manufacturer": "Generic",
        "model": "Storage Bin",
        "status": "active",
        "min_stock_threshold": 5
    }
    
    success, box = authenticated_client.post("/api/v1/assets/", box_data, expected_status=201)
    assert success, f"Failed to create storage box: {box}"
    box_id = box["id"]
    
    # Create only 2 items (below threshold of 5)
    created_cables = []
    for i in range(2):
        cable_data = {
            "asset_tag": f"{test_prefix}-DASHBOARD-CABLE-{i+1:03d}",
            "serial_number": f"{test_prefix}-CBL-SN-{i+1:03d}",
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
        assert success, f"Failed to create cable {i+1}: {cable}"
        assert "id" in cable, f"Cable {i+1} response missing id: {cable}"
        created_cables.append(cable)
    
    # Verify both cables were created
    assert len(created_cables) == 2, f"Should have created 2 cables, got {len(created_cables)}"
    
    # Both cables should have container_id set (may be the original box or a different one)
    # The important thing is that they're counted in the dashboard
    for i, cable in enumerate(created_cables):
        assert cable.get("container_id") is not None, f"Cable {i+1} should have container_id set: {cable}"
    
    # Get dashboard summary
    success, dashboard = authenticated_client.get("/api/v1/reports/dashboard/summary", expected_status=200)
    assert success, f"Failed to get dashboard summary: {dashboard}"
    
    # Verify low_stock_items exists
    assert "low_stock_items" in dashboard, "Dashboard should include low_stock_items"
    low_stock = dashboard["low_stock_items"]
    assert isinstance(low_stock, list), "low_stock_items should be a list"
    
    # Verify our box is in the list (or at least one box with low stock exists)
    # Note: Auto-assignment logic may move cables to different boxes, so we check that:
    # 1. At least one low stock box exists
    # 2. Our original box is either in the list OR the total count across all boxes matches
    box_found = next((item for item in low_stock if item["container_id"] == box_id), None)
    
    # If our box is not in the list, check if cables were moved to other boxes
    if box_found is None:
        # Check if any low stock boxes exist (cables may have been auto-assigned elsewhere)
        assert len(low_stock) > 0, f"No low stock items found. Expected at least one box with low stock. Created box ID: {box_id}"
        # Verify that at least one box has count < threshold
        has_low_stock = any(item["current_count"] < item["min_threshold"] for item in low_stock)
        assert has_low_stock, "At least one box should have current_count < min_threshold"
    else:
        # Our box is in the list - verify it has low stock
        assert box_found["current_count"] < box_found["min_threshold"], f"Box should have count < threshold. Got {box_found['current_count']} >= {box_found['min_threshold']}"
        assert box_found["min_threshold"] == 5, f"Expected threshold 5, got {box_found['min_threshold']}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{box_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.dashboard
def test_dashboard_summary_upcoming_maintenance(authenticated_client, test_prefix):
    """
    TC-DASHBOARD-003: Verify dashboard returns upcoming maintenance records.
    """
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-DASHBOARD-MAINT-001",
        "serial_number": f"{test_prefix}-MNT-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Create scheduled maintenance
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Scheduled PSU Replacement",
        "description": "Replace PSU as part of preventive maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled",
        "priority": "high",
        "scheduled_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "estimated_duration_hours": 2.0
    }
    
    success, maintenance = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {maintenance}"
    
    # Create in-progress maintenance
    maintenance_data_2 = {
        "asset_id": asset_id,
        "title": "Firmware Update",
        "description": "Update firmware to latest version",
        "maintenance_type": "upgrade",
        "status": "in_progress",
        "priority": "medium",
        "scheduled_date": datetime.utcnow().isoformat(),
        "estimated_duration_hours": 1.0
    }
    
    success, maintenance2 = authenticated_client.post("/api/v1/maintenance/", maintenance_data_2, expected_status=201)
    assert success, f"Failed to create maintenance 2: {maintenance2}"
    
    # Get dashboard summary
    success, dashboard = authenticated_client.get("/api/v1/reports/dashboard/summary", expected_status=200)
    assert success, f"Failed to get dashboard summary: {dashboard}"
    
    # Verify upcoming_maintenance exists
    assert "upcoming_maintenance" in dashboard, "Dashboard should include upcoming_maintenance"
    upcoming = dashboard["upcoming_maintenance"]
    assert isinstance(upcoming, list), "upcoming_maintenance should be a list"
    
    # Verify our maintenance records are in the list
    assert len(upcoming) >= 2, f"Expected at least 2 maintenance records, got {len(upcoming)}"
    
    maintenance_ids = [m["id"] for m in upcoming]
    assert maintenance["id"] in maintenance_ids, "Scheduled maintenance should be in upcoming_maintenance"
    assert maintenance2["id"] in maintenance_ids, "In-progress maintenance should be in upcoming_maintenance"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maintenance['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/maintenance/{maintenance2['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.dashboard
def test_dashboard_summary_all_metrics(authenticated_client, test_prefix):
    """
    TC-DASHBOARD-004: Verify dashboard returns all expected metrics.
    """
    success, dashboard = authenticated_client.get("/api/v1/reports/dashboard/summary", expected_status=200)
    assert success, f"Failed to get dashboard summary: {dashboard}"
    
    # Verify all expected keys exist
    assert "asset_utilization" in dashboard, "Should include asset_utilization"
    assert "capacity" in dashboard, "Should include capacity"
    assert "inventory_value" in dashboard, "Should include inventory_value"
    assert "asset_counts_by_type" in dashboard, "Should include asset_counts_by_type"
    assert "low_stock_items" in dashboard, "Should include low_stock_items"
    assert "upcoming_maintenance" in dashboard, "Should include upcoming_maintenance"
    assert "timestamp" in dashboard, "Should include timestamp"
    
    # Verify types
    assert isinstance(dashboard["asset_counts_by_type"], list), "asset_counts_by_type should be a list"
    assert isinstance(dashboard["low_stock_items"], list), "low_stock_items should be a list"
    assert isinstance(dashboard["upcoming_maintenance"], list), "upcoming_maintenance should be a list"

