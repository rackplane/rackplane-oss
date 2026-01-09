# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Logs Test Suite
Tests for audit logging functionality

This test suite verifies:
- Audit log creation for create/update/delete operations
- Audit log query endpoints
- Before/after value capture
- Tenant isolation for audit logs
- Filtering and pagination
"""

import pytest
from typing import Dict, Any
from datetime import datetime, timedelta


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_asset_create(authenticated_client, test_prefix, ensure_asset_types):
    """Test that asset creation is logged in audit logs"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-TEST-001",
        "serial_number": f"{test_prefix}-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Verify asset exists by fetching it
    success_asset, asset_check = authenticated_client.get(
        f"/api/v1/assets/{asset_id}",
        expected_status=200
    )
    assert success_asset, f"Asset {asset_id} should exist but couldn't be retrieved"
    
    # The audit log should be created in the same transaction as the asset
    # Query audit logs for this asset
    success, logs_response = authenticated_client.get(
        f"/api/v1/audit-logs/record/assets/{asset_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert isinstance(logs_response, list), f"Audit logs should be a list, got: {type(logs_response)}"
    
    # If no logs found, provide detailed debugging info
    if len(logs_response) == 0:
        # Try querying all audit logs to see if any exist for this tenant
        success_all, all_logs = authenticated_client.get(
            "/api/v1/audit-logs/",
            params={"limit": 10},
            expected_status=200
        )
        
        # Also try querying by table name without record_id
        success_table, table_logs = authenticated_client.get(
            "/api/v1/audit-logs/table/assets",
            params={"limit": 10},
            expected_status=200
        )
        
        # Verify asset exists and get its tenant
        success_asset, asset_check = authenticated_client.get(
            f"/api/v1/assets/{asset_id}",
            expected_status=200
        )
        
        assert success_asset, f"Asset {asset_id} should exist but couldn't be retrieved"
        asset_tenant_from_get = asset_check.get("tenant_id") if isinstance(asset_check, dict) else None
        
        # Build comprehensive error message
        error_msg = (
            f"No audit logs found for asset {asset_id}. "
            f"Asset exists: {success_asset}. "
            f"Total audit logs for tenant: {len(all_logs) if success_all else 'unknown'}. "
            f"Asset audit logs (all tenants): {len(table_logs) if success_table else 'unknown'}. "
            f"This suggests audit logging may not be working for asset creation, or the audit log "
            f"was created with a different tenant_id than the asset."
        )
        
        # If we got some logs but not for this asset, show what we got
        if success_all and len(all_logs) > 0:
            error_msg += f" Recent audit logs: {[(log.get('table_name'), log.get('record_id'), log.get('tenant_id')) for log in all_logs[:3]]}"
        
        assert len(logs_response) > 0, error_msg
    
    # Find the create log entry
    create_logs = [log for log in logs_response if log["action"] == "create"]
    assert len(create_logs) > 0, (
        f"Should have at least one create log entry. "
        f"Found {len(logs_response)} total logs for asset {asset_id}: "
        f"{[log.get('action') for log in logs_response]}. "
        f"All logs: {logs_response}"
    )
    
    create_log = create_logs[0]
    assert create_log["table_name"] == "assets", "Table name should be 'assets'"
    assert create_log["record_id"] == asset_id, "Record ID should match asset ID"
    assert create_log["action"] == "create", "Action should be 'create'"
    assert create_log["after_values"] is not None, "After values should be present"
    assert create_log["before_values"] is None, "Before values should be None for creates"
    
    # Verify after_values contains the asset data
    after_values = create_log["after_values"]
    assert after_values["asset_tag"] == asset_data["asset_tag"], "Asset tag should match"
    assert after_values["serial_number"] == asset_data["serial_number"], "Serial number should match"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_asset_update(authenticated_client, test_prefix):
    """Test that asset updates are logged with before/after values"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-UPDATE-001",
        "serial_number": f"{test_prefix}-SN-UPDATE-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Update the asset
    update_data = {
        "manufacturer": "Updated Manufacturer",
        "model": "Updated Model",
        "status": "deployed"
    }
    
    success, updated_asset = authenticated_client.put(
        f"/api/v1/assets/{asset_id}",
        update_data,
        expected_status=200
    )
    
    assert success, f"Failed to update asset: {updated_asset}"
    
    # Query audit logs for this asset
    success, logs_response = authenticated_client.get(
        f"/api/v1/audit-logs/record/assets/{asset_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    
    # Find the update log entry
    update_logs = [log for log in logs_response if log["action"] == "update"]
    assert len(update_logs) > 0, "Should have at least one update log entry"
    
    update_log = update_logs[0]
    assert update_log["table_name"] == "assets", "Table name should be 'assets'"
    assert update_log["record_id"] == asset_id, "Record ID should match asset ID"
    assert update_log["action"] == "update", "Action should be 'update'"
    assert update_log["before_values"] is not None, "Before values should be present"
    assert update_log["after_values"] is not None, "After values should be present"
    assert update_log["changes"] is not None, "Changes should be present"
    
    # Verify changes contain the updated fields
    changes = update_log["changes"]
    assert "manufacturer" in changes, "Manufacturer should be in changes"
    assert "model" in changes, "Model should be in changes"
    assert "status" in changes, "Status should be in changes"
    
    # Verify before/after values
    before_values = update_log["before_values"]
    after_values = update_log["after_values"]
    assert before_values["manufacturer"] == asset_data["manufacturer"], "Before manufacturer should match original"
    assert after_values["manufacturer"] == update_data["manufacturer"], "After manufacturer should match updated"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_asset_delete(authenticated_client, test_prefix):
    """Test that asset deletion is logged with before values"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-DELETE-001",
        "serial_number": f"{test_prefix}-SN-DELETE-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Delete the asset
    success, _ = authenticated_client.delete(
        f"/api/v1/assets/{asset_id}",
        expected_status=204
    )
    
    assert success, "Failed to delete asset"
    
    # Query audit logs for this asset
    success, logs_response = authenticated_client.get(
        f"/api/v1/audit-logs/record/assets/{asset_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    
    # Find the delete log entry
    delete_logs = [log for log in logs_response if log["action"] == "delete"]
    assert len(delete_logs) > 0, "Should have at least one delete log entry"
    
    delete_log = delete_logs[0]
    assert delete_log["table_name"] == "assets", "Table name should be 'assets'"
    assert delete_log["record_id"] == asset_id, "Record ID should match asset ID"
    assert delete_log["action"] == "delete", "Action should be 'delete'"
    assert delete_log["before_values"] is not None, "Before values should be present"
    assert delete_log["after_values"] is None, "After values should be None for deletes"
    
    # Verify before_values contains the asset data
    before_values = delete_log["before_values"]
    assert before_values["asset_tag"] == asset_data["asset_tag"], "Asset tag should match"
    assert before_values["serial_number"] == asset_data["serial_number"], "Serial number should match"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_list_with_filters(authenticated_client, test_prefix):
    """Test audit log listing with various filters"""
    # Create an asset to generate audit logs
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-FILTER-001",
        "serial_number": f"{test_prefix}-SN-FILTER-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Test filter by table name
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"table_name": "assets"},
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert isinstance(logs_response, dict), "Audit logs response should be a dict (paginated)"
    assert "logs" in logs_response, "Response should contain 'logs' key"
    logs_list = logs_response["logs"]
    assert isinstance(logs_list, list), "Logs should be a list"
    assert len(logs_list) > 0, "Should have at least one log entry"
    assert all(log["table_name"] == "assets" for log in logs_list), "All logs should be for assets table"
    
    # Test filter by action
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"action": "create"},
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    logs_list = logs_response["logs"]
    assert all(log["action"] == "create" for log in logs_list), "All logs should be create actions"
    
    # Test filter by record_id
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"record_id": asset_id},
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    logs_list = logs_response["logs"]
    assert all(log["record_id"] == asset_id for log in logs_list), "All logs should be for the same record"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_pagination(authenticated_client, test_prefix):
    """Test audit log pagination"""
    # Create multiple assets to generate multiple audit logs
    for i in range(5):
        asset_data = {
            "asset_tag": f"{test_prefix}-AUDIT-PAGE-{i:03d}",
            "serial_number": f"{test_prefix}-SN-PAGE-{i:03d}",
            "asset_type": "server_device",
            "manufacturer": "Test Manufacturer",
            "model": "Test Model",
            "status": "in_storage"
        }
        
        success, _ = authenticated_client.post(
            "/api/v1/assets/",
            asset_data,
            expected_status=201
        )
        assert success, f"Failed to create asset {i}"
    
    # Test limit
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"limit": 2, "table_name": "assets"},
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    logs_list = logs_response["logs"]
    assert len(logs_list) <= 2, "Should respect limit parameter"
    
    # Test offset
    success, logs_page1 = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"limit": 2, "offset": 0, "table_name": "assets"},
        expected_status=200
    )
    
    success, logs_page2 = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={"limit": 2, "offset": 2, "table_name": "assets"},
        expected_status=200
    )
    
    assert success, "Failed to get paginated audit logs"
    logs_list1 = logs_page1["logs"]
    logs_list2 = logs_page2["logs"]
    
    # Pages should have different entries (assuming we have enough logs)
    if len(logs_list1) > 0 and len(logs_list2) > 0:
        assert logs_list1[0]["id"] != logs_list2[0]["id"], "Pages should have different entries"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_tenant_isolation(authenticated_client, test_user, admin_token, api_client, test_prefix):
    """Test that audit logs are tenant-isolated"""
    # Create an asset as the test user
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-ISOLATE-001",
        "serial_number": f"{test_prefix}-SN-ISOLATE-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Query audit logs as the test user (should see their tenant's logs)
    success, logs_response = authenticated_client.get(
        f"/api/v1/audit-logs/record/assets/{asset_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert len(logs_response) > 0, "Should see audit logs for own tenant"
    
    # Verify all logs are for the test user's tenant
    test_tenant_id = test_user["tenant"]["id"]
    for log in logs_response:
        assert log["tenant_id"] == test_tenant_id, "All logs should be for the test tenant"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_get_by_id(authenticated_client, test_prefix):
    """Test getting a specific audit log entry by ID"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-GET-001",
        "serial_number": f"{test_prefix}-SN-GET-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    asset_id = asset_response["id"]
    
    # Get audit logs for this asset
    success, logs_response = authenticated_client.get(
        f"/api/v1/audit-logs/record/assets/{asset_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert len(logs_response) > 0, "Should have at least one log entry"
    
    log_id = logs_response[0]["id"]
    
    # Get the specific log entry by ID
    success, log_entry = authenticated_client.get(
        f"/api/v1/audit-logs/{log_id}",
        expected_status=200
    )
    
    assert success, f"Failed to get audit log by ID: {log_entry}"
    assert log_entry["id"] == log_id, "Log ID should match"
    assert log_entry["table_name"] == "assets", "Table name should match"
    assert log_entry["record_id"] == asset_id, "Record ID should match"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_get_by_table(authenticated_client, test_prefix):
    """Test getting audit logs filtered by table name"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-TABLE-001",
        "serial_number": f"{test_prefix}-SN-TABLE-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    
    # Get audit logs for assets table
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/table/assets",
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert isinstance(logs_response, list), "Audit logs should be a list"
    assert len(logs_response) > 0, "Should have at least one log entry"
    assert all(log["table_name"] == "assets" for log in logs_response), "All logs should be for assets table"


@pytest.mark.audit
@pytest.mark.integration
def test_audit_log_date_filtering(authenticated_client, test_prefix):
    """Test filtering audit logs by date range"""
    # Create an asset
    asset_data = {
        "asset_tag": f"{test_prefix}-AUDIT-DATE-001",
        "serial_number": f"{test_prefix}-SN-DATE-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "in_storage"
    }
    
    success, asset_response = authenticated_client.post(
        "/api/v1/assets/",
        asset_data,
        expected_status=201
    )
    
    assert success, f"Failed to create asset: {asset_response}"
    
    # Get current time (timezone-aware)
    from datetime import timezone
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(hours=1))
    end_date = (now + timedelta(hours=1))
    
    # Get audit logs with date filter
    success, logs_response = authenticated_client.get(
        "/api/v1/audit-logs/",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "table_name": "assets"
        },
        expected_status=200
    )
    
    assert success, f"Failed to get audit logs: {logs_response}"
    assert isinstance(logs_response, dict), "Audit logs response should be a dict"
    logs_list = logs_response["logs"]
    
    # Verify all logs are within the date range
    for log in logs_list:
        # Parse the log date (handle both with and without timezone)
        log_date_str = log["created_at"]
        if log_date_str.endswith("Z"):
            log_date_str = log_date_str.replace("Z", "+00:00")
        log_date = datetime.fromisoformat(log_date_str)
        
        # Make timezone-aware if needed
        if log_date.tzinfo is None:
            log_date = log_date.replace(tzinfo=timezone.utc)
        
        assert log_date >= start_date, f"Log should be after start date: {log_date} >= {start_date}"
        assert log_date <= end_date, f"Log should be before end date: {log_date} <= {end_date}"

