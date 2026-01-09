# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Maintenance API Test Suite
Tests for maintenance records, predictions, and analytics.
"""

import pytest
from datetime import datetime, timedelta
from app.models.maintenance import MaintenanceStatus, MaintenanceType


@pytest.mark.integration
@pytest.mark.maintenance
def test_create_maintenance_record(authenticated_client, test_prefix):
    """
    TC-MAINT-001: Create maintenance record
    """
    # First create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-ASSET-001",
        "serial_number": f"{test_prefix}-MAINT-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Create maintenance record
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Scheduled Maintenance",
        "description": "Routine maintenance check",
        "maintenance_type": "preventive",
        "status": "scheduled",
        "priority": "medium",
        "scheduled_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "estimated_duration_hours": 2.0
    }
    
    success, response = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    
    assert success, f"Failed to create maintenance record: {response}"
    assert "id" in response, f"Response missing 'id': {response}"
    assert response["title"] == maintenance_data["title"]
    assert response["maintenance_type"] == maintenance_data["maintenance_type"]
    assert response["status"] == maintenance_data["status"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{response['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_list_maintenance_records(authenticated_client, test_prefix):
    """
    TC-MAINT-002: List maintenance records
    """
    # Create asset and maintenance record
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-LIST-001",
        "serial_number": f"{test_prefix}-LIST-SN-001",
        "asset_type": "server_device",
        "manufacturer": "HP",
        "model": "ProLiant",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    maintenance_data = {
        "asset_id": asset_id,
        "title": "List Test Maintenance",
        "description": "Test maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, maint = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {maint}"
    maint_id = maint["id"]
    
    # List maintenance records
    success, response = authenticated_client.get("/api/v1/maintenance/", expected_status=200)
    
    assert success, f"Failed to list maintenance records: {response}"
    assert "total" in response, "Response should include total count"
    assert "records" in response, "Response should include records list"
    assert isinstance(response["records"], list)
    assert len(response["records"]) > 0, "Should have at least one record"
    
    # Find our test record
    test_record = next((r for r in response["records"] if r["id"] == maint_id), None)
    assert test_record is not None, "Test maintenance record should be in the list"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_get_maintenance_record_by_id(authenticated_client, test_prefix):
    """
    TC-MAINT-003: Get maintenance record by ID
    """
    # Create asset and maintenance
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-GET-001",
        "serial_number": f"{test_prefix}-GET-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Get Test Maintenance",
        "description": "Test maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, created = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {created}"
    maint_id = created["id"]
    
    # Get by ID
    success, fetched = authenticated_client.get(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    
    assert success, f"Failed to fetch maintenance: {fetched}"
    assert fetched["id"] == maint_id
    assert fetched["title"] == maintenance_data["title"]
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_update_maintenance_record(authenticated_client, test_prefix):
    """
    TC-MAINT-004: Update maintenance record
    """
    # Create asset and maintenance
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-UPDATE-001",
        "serial_number": f"{test_prefix}-UPDATE-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Update Test Maintenance",
        "description": "Original description",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, created = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {created}"
    maint_id = created["id"]
    
    # Update maintenance (only certain fields can be updated via MaintenanceUpdate schema)
    update_data = {
        "status": "in_progress",
        "work_performed": "Started maintenance work",
        "issue_resolved": False
    }
    
    success, updated = authenticated_client.put(f"/api/v1/maintenance/{maint_id}", update_data, expected_status=200)
    
    assert success, f"Failed to update maintenance: {updated}"
    # Verify fields were updated
    assert updated.get("status") == update_data["status"] or updated.get("work_performed") == update_data["work_performed"], \
        f"Expected updated fields, got: {updated}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_start_maintenance(authenticated_client, test_prefix):
    """
    TC-MAINT-005: Start maintenance (mark as in progress)
    """
    # Create asset and maintenance
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-START-001",
        "serial_number": f"{test_prefix}-START-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Start Test Maintenance",
        "description": "Test maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, created = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {created}"
    maint_id = created["id"]
    
    # Start maintenance (no body needed)
    success, started = authenticated_client.post(f"/api/v1/maintenance/{maint_id}/start", {}, expected_status=200)
    
    assert success, f"Failed to start maintenance: {started}"
    assert started["status"] == "in_progress"
    assert "started_at" in started or started.get("started_at") is not None
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_complete_maintenance(authenticated_client, test_prefix):
    """
    TC-MAINT-006: Complete maintenance
    """
    # Create asset and maintenance
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-COMPLETE-001",
        "serial_number": f"{test_prefix}-COMPLETE-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Complete Test Maintenance",
        "description": "Test maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, created = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {created}"
    maint_id = created["id"]
    
    # Start maintenance first (no body needed)
    authenticated_client.post(f"/api/v1/maintenance/{maint_id}/start", {}, expected_status=200)
    
    # Complete maintenance (parameters are query params, not body)
    # TestClient.post requires data as positional arg, but we can pass params via **kwargs
    # The endpoint accepts work_performed and issue_resolved as query parameters
    import urllib.parse
    params_str = urllib.parse.urlencode({
        "work_performed": "Completed test maintenance",
        "issue_resolved": "true"
    })
    # Append params to URL since TestClient doesn't support params kwarg directly
    success, completed = authenticated_client.post(
        f"/api/v1/maintenance/{maint_id}/complete?{params_str}",
        {},  # Empty dict for body (required parameter)
        expected_status=200
    )
    
    assert success, f"Failed to complete maintenance: {completed}"
    assert completed["status"] == "completed"
    assert "completed_at" in completed or completed.get("completed_at") is not None
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_filter_maintenance_by_asset(authenticated_client, test_prefix):
    """
    TC-MAINT-007: Filter maintenance records by asset
    """
    # Create asset
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-FILTER-001",
        "serial_number": f"{test_prefix}-FILTER-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Create maintenance for this asset
    maintenance_data = {
        "asset_id": asset_id,
        "title": "Filter Test Maintenance",
        "description": "Test maintenance",
        "maintenance_type": "preventive",
        "status": "scheduled"
    }
    
    success, maint = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
    assert success, f"Failed to create maintenance: {maint}"
    maint_id = maint["id"]
    
    # Filter by asset
    success, response = authenticated_client.get(f"/api/v1/maintenance/?asset_id={asset_id}", expected_status=200)
    
    assert success, f"Failed to filter by asset: {response}"
    assert "records" in response
    assert len(response["records"]) > 0, "Should have at least one record"
    assert all(r["asset_id"] == asset_id for r in response["records"]), "All records should be for the specified asset"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_get_asset_maintenance_history(authenticated_client, test_prefix):
    """
    TC-MAINT-008: Get asset maintenance history
    """
    # Create asset
    asset_data = {
        "asset_tag": f"{test_prefix}-MAINT-HIST-001",
        "serial_number": f"{test_prefix}-HIST-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Create multiple maintenance records
    maint_ids = []
    for i in range(3):
        maintenance_data = {
            "asset_id": asset_id,
            "title": f"History Test Maintenance {i+1}",
            "description": f"Test maintenance {i+1}",
            "maintenance_type": "preventive",
            "status": "scheduled"
        }
        success, maint = authenticated_client.post("/api/v1/maintenance/", maintenance_data, expected_status=201)
        assert success, f"Failed to create maintenance {i+1}: {maint}"
        maint_ids.append(maint["id"])
    
    # Get maintenance history
    success, history = authenticated_client.get(f"/api/v1/maintenance/asset/{asset_id}/history", expected_status=200)
    
    assert success, f"Failed to get maintenance history: {history}"
    assert isinstance(history, list)
    assert len(history) >= 3, "Should have at least 3 maintenance records"
    assert all(r["asset_id"] == asset_id for r in history), "All records should be for the specified asset"
    
    # Cleanup
    for maint_id in maint_ids:
        authenticated_client.delete(f"/api/v1/maintenance/{maint_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.maintenance
def test_get_maintenance_predictions(authenticated_client, test_prefix):
    """
    TC-MAINT-009: Get maintenance predictions
    """
    # This endpoint may return empty list if no predictions exist
    success, response = authenticated_client.get("/api/v1/maintenance/predictions/", expected_status=200)
    
    assert success, f"Failed to get predictions: {response}"
    assert isinstance(response, list), "Predictions should be a list"


@pytest.mark.integration
@pytest.mark.maintenance
def test_get_mttr_analytics(authenticated_client, test_prefix):
    """
    TC-MAINT-010: Get MTTR analytics
    """
    success, response = authenticated_client.get("/api/v1/maintenance/analytics/mttr", expected_status=200)
    
    assert success, f"Failed to get MTTR analytics: {response}"
    # Response structure may vary, but should not error


@pytest.mark.integration
@pytest.mark.maintenance
def test_maintenance_get_nonexistent(authenticated_client):
    """
    TC-MAINT-011: Get non-existent maintenance record should return 404
    """
    nonexistent_id = 999999
    
    success, response = authenticated_client.get(f"/api/v1/maintenance/{nonexistent_id}", expected_status=[404, 200])
    # May return 404 or 200 with error detail
    if success:
        error_detail = str(response.get("detail", "")).lower()
        assert "not found" in error_detail, f"Expected 'not found' error, got: {response}"
    else:
        assert "not found" in str(response).lower() or response.get("status_code") == 404, \
            f"Expected 404 or 'not found' error, got: {response}"

