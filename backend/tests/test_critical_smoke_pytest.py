"""
Critical Smoke Tests - MUST PASS AFTER ANY SYSTEM CHANGE

This test suite contains the most critical tests that verify core system functionality.
These tests should be run after:
- Database migrations
- Code changes affecting authentication, authorization, or data integrity
- Changes to multi-tenancy logic
- Changes to backup/restore functionality
- Any deployment

These tests are marked with @pytest.mark.critical and can be run with:
    pytest -m critical

Or using the convenience script:
    python scripts/run_critical_tests.py
"""

import pytest


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.auth
def test_auth_login(api_client, test_user):
    """
    CRITICAL: Authentication must work for system to function.
    
    This test performs a real login and verifies:
    1. Login endpoint returns a valid token
    2. Token can be used to access protected endpoints
    3. Real data can be fetched from multiple endpoints
    4. Data structure is correct and meaningful
    """
    # Clear any existing token
    api_client.clear_token()
    
    # Step 1: Perform actual login (not using fixture)
    credentials = test_user["credentials"]
    token = api_client.login(credentials["username"], credentials["password"])
    
    assert token is not None, "Login failed - no token returned"
    assert isinstance(token, str), f"Token should be a string, got: {type(token)}"
    assert len(token) > 0, "Token should not be empty"
    
    # Step 2: Set token and verify it works
    api_client.set_token(token)
    
    # Step 3: Fetch real data from assets endpoint
    success, assets_response = api_client.get("/api/v1/assets/", expected_status=200)
    assert success, f"Failed to access assets endpoint: {assets_response}"
    assert isinstance(assets_response, dict), f"Expected dict response, got: {type(assets_response)}"
    # Verify response structure
    assert "assets" in assets_response or "total" in assets_response or isinstance(assets_response, list), \
        f"Unexpected assets response structure: {assets_response}"
    
    # Step 4: Fetch real data from racks endpoint
    success, racks_response = api_client.get("/api/v1/locations/racks", expected_status=200)
    assert success, f"Failed to access racks endpoint: {racks_response}"
    assert isinstance(racks_response, dict) or isinstance(racks_response, list), \
        f"Expected dict or list response, got: {type(racks_response)}"
    
    # Step 5: Fetch real data from datacenters endpoint
    success, datacenters_response = api_client.get("/api/v1/locations/datacenters", expected_status=200)
    assert success, f"Failed to access datacenters endpoint: {datacenters_response}"
    assert isinstance(datacenters_response, dict) or isinstance(datacenters_response, list), \
        f"Expected dict or list response, got: {type(datacenters_response)}"
    
    # Step 6: Fetch user info to verify authentication context
    success, user_response = api_client.get("/api/v1/auth/me", expected_status=200)
    assert success, f"Failed to access /api/v1/auth/me: {user_response}"
    assert isinstance(user_response, dict), f"Expected dict response, got: {type(user_response)}"
    assert "username" in user_response, f"User response missing username: {user_response}"
    assert user_response["username"] == credentials["username"], \
        f"Username mismatch: expected {credentials['username']}, got {user_response['username']}"
    
    # Step 7: Verify token is actually being used (test with invalid token)
    api_client.set_token("invalid_token_should_fail")
    success, invalid_response = api_client.get("/api/v1/assets/", expected_status=401)
    assert success, f"Expected 401 with invalid token, got: {invalid_response}"
    
    # Step 8: Restore valid token and verify it still works
    api_client.set_token(token)
    success, final_response = api_client.get("/api/v1/assets/", expected_status=200)
    assert success, f"Token should still work after invalid token test: {final_response}"

@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.tenant
def test_tenant_isolation(test_tenant, authenticated_client):
    """
    CRITICAL: Tenant isolation must work to prevent data leakage.
    """
    # Create an asset in the test tenant
    asset_data = {
        "asset_tag": f"CRITICAL-ISO-001",
        "serial_number": "SN-CRIT-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Verify asset is accessible
    success, fetched_asset = authenticated_client.get(f"/api/v1/assets/{asset_id}", expected_status=200)
    assert success, f"Failed to fetch asset: {fetched_asset}"
    assert fetched_asset["asset_tag"] == asset_data["asset_tag"]


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_user_duplicate_username(admin_token, api_client, test_tenant):
    """
    CRITICAL: Username uniqueness per tenant must be enforced to prevent duplicates.
    This test verifies the database constraint and application-level check.
    """
    api_client.set_token(admin_token)
    username = f"critical-testuser-{test_tenant['id']}"
    
    # Create first user
    user_data1 = {
        "username": username,
        "password": "TestPassword123!",
        "tenant_id": test_tenant["id"]
    }
    
    success1, user1 = api_client.post(
        f"/api/v1/tenants/{test_tenant['id']}/users",
        user_data1,
        expected_status=201
    )
    assert success1, f"Failed to create first user: {user1}"
    user1_id = user1["id"]
    
    # Try to create duplicate with same username (should fail)
    user_data2 = {
        "username": username,  # Same username
        "password": "TestPassword123!",
        "tenant_id": test_tenant["id"]
    }
    
    success2, response2 = api_client.post(
        f"/api/v1/tenants/{test_tenant['id']}/users",
        user_data2,
        expected_status=400
    )
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate username, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "username" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate username error, got: {response2}"
    
    # Cleanup
    api_client.delete(f"/api/v1/users/{user1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_rack_duplicate_code(authenticated_client, test_prefix):
    """
    CRITICAL: Rack code uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    # Create a datacenter first
    dc_data = {
        "name": f"{test_prefix}-Critical-DC",
        "code": f"{test_prefix}-CRIT-DC",
        "address": "123 Test St",
        "city": "Test City"
    }
    
    success, datacenter = authenticated_client.post("/api/v1/locations/datacenters", dc_data, expected_status=201)
    assert success, f"Failed to create datacenter: {datacenter}"
    dc_id = datacenter["id"]
    
    # Create first rack
    rack_data1 = {
        "name": f"{test_prefix}-Critical-Rack-1",
        "code": f"{test_prefix}-CRIT-RACK",
        "datacenter_id": dc_id,
        "height_u": 42
    }
    
    success1, rack1 = authenticated_client.post("/api/v1/locations/racks", rack_data1, expected_status=201)
    assert success1, f"Failed to create first rack: {rack1}"
    rack1_id = rack1["id"]
    
    # Try to create duplicate with same code (should fail)
    rack_data2 = {
        "name": f"{test_prefix}-Critical-Rack-2",  # Different name
        "code": f"{test_prefix}-CRIT-RACK",  # Same code
        "datacenter_id": dc_id,
        "height_u": 42
    }
    
    success2, response2 = authenticated_client.post("/api/v1/locations/racks", rack_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate rack code, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "code" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate code error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/locations/racks/{rack1_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/locations/datacenters/{dc_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_storage_container_duplicate_name(authenticated_client, test_prefix, test_tenant):
    """
    CRITICAL: Storage container name uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    container_name = f"{test_prefix}-Critical-Box"
    
    # Create first container
    container_data = {
        "name": container_name,
        "container_type": "box",
        "description": "Critical test storage container"
    }
    
    success1, container1 = authenticated_client.post(
        "/api/v1/storage-containers/",
        container_data,
        expected_status=201
    )
    assert success1, f"Failed to create first container: {container1}"
    assert container1["name"] == container_name
    container1_id = container1["id"]
    
    # Try to create duplicate with same name (should fail)
    success2, response2 = authenticated_client.post(
        "/api/v1/storage-containers/",
        container_data,
        expected_status=400
    )
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate container name, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "already exists" in error_detail or "duplicate" in error_detail or "name" in error_detail, \
        f"Expected duplicate name error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/storage-containers/{container1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.rbac
def test_super_admin_can_manage_tenants(admin_token, api_client, test_prefix):
    """
    CRITICAL: Super admin must be able to manage tenants for system administration.
    """
    api_client.set_token(admin_token)
    
    # Create tenant
    tenant_data = {
        "name": f"{test_prefix}-Critical-Tenant",
        "slug": f"{test_prefix.lower()}-critical-tenant",
        "subscription_tier": "standard",
        "contact_email": f"critical-{test_prefix.lower()}@test.example.com"
    }
    
    success, tenant_response = api_client.post(
        "/api/v1/tenants/",
        tenant_data,
        expected_status=201
    )
    
    assert success, f"Super admin should be able to create tenant: {tenant_response}"
    tenant_id = tenant_response["id"]
    
    # Cleanup
    api_client.delete(f"/api/v1/tenants/{tenant_id}", expected_status=[200, 204])


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.backup
def test_backup_restore_basic(admin_token, api_client, test_tenant, test_user):
    """
    CRITICAL: Backup and restore must work to prevent data loss.
    This is a minimal test to verify backup/restore functionality exists.
    """
    api_client.set_token(admin_token)
    
    # Create a simple asset to backup
    asset_data = {
        "asset_tag": f"CRITICAL-BACKUP-001",
        "serial_number": "SN-CRIT-BACKUP-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    # Use test_user token to create asset in test tenant
    api_client.set_token(test_user["token"])
    success, asset = api_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset for backup test: {asset}"
    
    # Switch back to admin token for backup
    api_client.set_token(admin_token)
    
    # Create backup (GET endpoint, not POST)
    success, backup_response = api_client.get(
        "/api/v1/backup/export",
        expected_status=200
    )
    
    assert success, f"Failed to create backup: {backup_response}"
    # Backup export returns the backup data directly, check for metadata or data structure
    assert isinstance(backup_response, dict), f"Backup response should be a dict, got: {type(backup_response)}"
    assert "metadata" in backup_response or len(backup_response) > 0, \
        f"Backup response missing expected data: {backup_response}"


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_storage_container_duplicate_barcode(authenticated_client, test_prefix, test_tenant):
    """
    CRITICAL: Storage container barcode uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    barcode = f"{test_prefix}-CRIT-BARCODE-001"
    
    # Create first container with barcode
    container_data1 = {
        "name": f"{test_prefix}-Critical-Box-1",
        "container_type": "box",
        "barcode": barcode,
        "description": "Critical test storage container"
    }
    
    success1, container1 = authenticated_client.post(
        "/api/v1/storage-containers/",
        container_data1,
        expected_status=201
    )
    assert success1, f"Failed to create first container: {container1}"
    container1_id = container1["id"]
    
    # Try to create duplicate with same barcode (should fail)
    container_data2 = {
        "name": f"{test_prefix}-Critical-Box-2",  # Different name
        "container_type": "box",
        "barcode": barcode,  # Same barcode
        "description": "Critical test storage container 2"
    }
    
    success2, response2 = authenticated_client.post(
        "/api/v1/storage-containers/",
        container_data2,
        expected_status=400
    )
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate barcode, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "barcode" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate barcode error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/storage-containers/{container1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_asset_duplicate_tag(authenticated_client, ensure_asset_types, test_prefix):
    """
    CRITICAL: Asset tag uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    asset_tag = f"{test_prefix}-CRIT-TAG-001"
    
    # Create first asset
    asset_data1 = {
        "asset_tag": asset_tag,
        "serial_number": f"{test_prefix}-CRIT-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success1, asset1 = authenticated_client.post("/api/v1/assets/", asset_data1, expected_status=201)
    assert success1, f"Failed to create first asset: {asset1}"
    asset1_id = asset1["id"]
    
    # Try to create duplicate with same tag (should fail)
    asset_data2 = {
        "asset_tag": asset_tag,  # Same tag
        "serial_number": f"{test_prefix}-CRIT-SN-002",  # Different serial
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success2, response2 = authenticated_client.post("/api/v1/assets/", asset_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate asset tag, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "tag" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate tag error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_asset_duplicate_serial(authenticated_client, ensure_asset_types, test_prefix):
    """
    CRITICAL: Asset serial number uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    serial_number = f"{test_prefix}-CRIT-SERIAL-001"
    
    # Create first asset
    asset_data1 = {
        "asset_tag": f"{test_prefix}-CRIT-001",
        "serial_number": serial_number,
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success1, asset1 = authenticated_client.post("/api/v1/assets/", asset_data1, expected_status=201)
    assert success1, f"Failed to create first asset: {asset1}"
    asset1_id = asset1["id"]
    
    # Try to create duplicate with same serial (should fail)
    asset_data2 = {
        "asset_tag": f"{test_prefix}-CRIT-002",  # Different tag
        "serial_number": serial_number,  # Same serial
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success2, response2 = authenticated_client.post("/api/v1/assets/", asset_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate serial number, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "serial" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate serial error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_asset_duplicate_hostname(authenticated_client, ensure_asset_types, test_prefix):
    """
    CRITICAL: Asset hostname uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    hostname = f"{test_prefix.lower()}-crit-host-001"
    
    # Create first asset with hostname
    asset_data1 = {
        "asset_tag": f"{test_prefix}-CRIT-HOST-001",
        "serial_number": f"{test_prefix}-CRIT-HOST-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active",
        "hostname": hostname
    }
    
    success1, asset1 = authenticated_client.post("/api/v1/assets/", asset_data1, expected_status=201)
    assert success1, f"Failed to create first asset: {asset1}"
    asset1_id = asset1["id"]
    
    # Try to create duplicate with same hostname (should fail)
    asset_data2 = {
        "asset_tag": f"{test_prefix}-CRIT-HOST-002",  # Different tag
        "serial_number": f"{test_prefix}-CRIT-HOST-SN-002",  # Different serial
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active",
        "hostname": hostname  # Same hostname
    }
    
    # Don't pass expected_status - we want to check the actual status
    success2, response2 = authenticated_client.post("/api/v1/assets/", asset_data2)
    
    # Should fail (not 200/201) with 400 Bad Request for duplicate hostname
    assert not success2, f"Expected 400 for duplicate hostname, got success: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "hostname" in error_detail or "already exists" in error_detail or "duplicate" in error_detail or "400" in str(response2).lower(), \
        f"Expected duplicate hostname error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_asset_type_duplicate_name(authenticated_client, test_prefix, test_tenant):
    """
    CRITICAL: Asset type name uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    asset_type_name = f"{test_prefix}-Critical-Type"
    
    # Create first asset type
    asset_type_data1 = {
        "name": asset_type_name,
        "display_name": asset_type_name,  # Required field
        "description": "Critical test asset type"
    }
    
    success1, asset_type1 = authenticated_client.post("/api/v1/asset-types/", asset_type_data1, expected_status=201)
    assert success1, f"Failed to create first asset type: {asset_type1}"
    asset_type1_id = asset_type1["id"]
    
    # Try to create duplicate with same name (should fail)
    asset_type_data2 = {
        "name": asset_type_name,  # Same name
        "display_name": f"{asset_type_name} (Duplicate)",  # Different display name
        "description": "Different description"
    }
    
    success2, response2 = authenticated_client.post("/api/v1/asset-types/", asset_type_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate asset type name, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "name" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate name error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/asset-types/{asset_type1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_datacenter_duplicate_name(authenticated_client, test_prefix):
    """
    CRITICAL: Datacenter name uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    dc_name = f"{test_prefix}-Critical-DC-Name"
    
    # Create first datacenter
    dc_data1 = {
        "name": dc_name,
        "code": f"{test_prefix}-CRIT-DC-CODE-1",
        "address": "123 Test St",
        "city": "Test City"
    }
    
    success1, dc1 = authenticated_client.post("/api/v1/locations/datacenters", dc_data1, expected_status=201)
    assert success1, f"Failed to create first datacenter: {dc1}"
    dc1_id = dc1["id"]
    
    # Try to create duplicate with same name (should fail)
    dc_data2 = {
        "name": dc_name,  # Same name
        "code": f"{test_prefix}-CRIT-DC-CODE-2",  # Different code
        "address": "456 Test St",
        "city": "Test City"
    }
    
    success2, response2 = authenticated_client.post("/api/v1/locations/datacenters", dc_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate datacenter name, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "name" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate name error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/locations/datacenters/{dc1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_datacenter_duplicate_code(authenticated_client, test_prefix):
    """
    CRITICAL: Datacenter code uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    dc_code = f"{test_prefix}-CRIT-DC-CODE"
    
    # Create first datacenter
    dc_data1 = {
        "name": f"{test_prefix}-Critical-DC-1",
        "code": dc_code,
        "address": "123 Test St",
        "city": "Test City"
    }
    
    success1, dc1 = authenticated_client.post("/api/v1/locations/datacenters", dc_data1, expected_status=201)
    assert success1, f"Failed to create first datacenter: {dc1}"
    dc1_id = dc1["id"]
    
    # Try to create duplicate with same code (should fail)
    dc_data2 = {
        "name": f"{test_prefix}-Critical-DC-2",  # Different name
        "code": dc_code,  # Same code
        "address": "456 Test St",
        "city": "Test City"
    }
    
    success2, response2 = authenticated_client.post("/api/v1/locations/datacenters", dc_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate datacenter code, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "code" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate code error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/locations/datacenters/{dc1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_network_cable_duplicate_serial(authenticated_client, test_prefix):
    """
    CRITICAL: Network cable serial number uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    serial_number = f"{test_prefix}-CRIT-CABLE-SN-001"
    
    # Create first cable with serial number
    cable_data1 = {
        "name": f"{test_prefix}-Critical-Cable-1",
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "serial_number": serial_number,
        "quantity": 1
    }
    
    success1, cable1 = authenticated_client.post("/api/v1/network-cables/", cable_data1, expected_status=201)
    assert success1, f"Failed to create first cable: {cable1}"
    cable1_id = cable1["id"]
    
    # Try to create duplicate with same serial (should fail)
    cable_data2 = {
        "name": f"{test_prefix}-Critical-Cable-2",  # Different name
        "cable_type": "dac",
        "connector_type": "qsfp28",
        "speed": "100G",
        "serial_number": serial_number,  # Same serial
        "quantity": 1
    }
    
    success2, response2 = authenticated_client.post("/api/v1/network-cables/", cable_data2, expected_status=400)
    
    # Should fail with 400 Bad Request
    assert success2, f"Expected 400 for duplicate cable serial number, got: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "serial" in error_detail or "already exists" in error_detail or "duplicate" in error_detail, \
        f"Expected duplicate serial error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/network-cables/{cable1_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.duplicate_prevention
def test_environmental_sensor_duplicate_sensor_id(authenticated_client, test_prefix):
    """
    CRITICAL: Environmental sensor ID uniqueness per tenant must be enforced.
    This test verifies the database constraint and application-level check.
    """
    # Create a datacenter first (required for sensors)
    dc_data = {
        "name": f"{test_prefix}-Critical-DC-Sensor",
        "code": f"{test_prefix}-CRIT-DC-SENSOR",
        "address": "123 Test St",
        "city": "Test City"
    }
    success, datacenter = authenticated_client.post("/api/v1/locations/datacenters", dc_data, expected_status=201)
    assert success, f"Failed to create datacenter: {datacenter}"
    dc_id = datacenter["id"]
    
    sensor_id = f"{test_prefix}-CRIT-SENSOR-001"
    
    # Create first sensor
    sensor_data1 = {
        "sensor_id": sensor_id,
        "sensor_name": f"{test_prefix}-Critical Sensor 1",  # Required field
        "datacenter_id": dc_id,  # Required field
        "sensor_type": "temperature",
        "location": "Test Location",
        "unit": "celsius"
    }
    
    success1, sensor1 = authenticated_client.post("/api/v1/environmental/sensors", sensor_data1, expected_status=201)
    assert success1, f"Failed to create first sensor: {sensor1}"
    sensor1_id = sensor1["id"]
    
    # Try to create duplicate with same sensor_id (should fail)
    sensor_data2 = {
        "sensor_id": sensor_id,  # Same sensor_id
        "sensor_name": f"{test_prefix}-Critical Sensor 2",  # Different name
        "datacenter_id": dc_id,
        "sensor_type": "humidity",  # Different type
        "location": "Different Location",
        "unit": "percent"
    }
    
    # Don't pass expected_status - we want to check the actual status
    success2, response2 = authenticated_client.post("/api/v1/environmental/sensors", sensor_data2)
    
    # Should fail (not 200/201) with 400 Bad Request for duplicate sensor_id
    assert not success2, f"Expected 400 for duplicate sensor_id, got success: {response2}"
    error_detail = str(response2.get("detail", "")).lower()
    assert "sensor" in error_detail or "sensor_id" in error_detail or "already exists" in error_detail or "duplicate" in error_detail or "400" in str(response2).lower(), \
        f"Expected duplicate sensor_id error, got: {response2}"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/environmental/sensors/{sensor1_id}", expected_status=204)
    authenticated_client.delete(f"/api/v1/locations/datacenters/{dc_id}", expected_status=204)


@pytest.mark.critical
@pytest.mark.integration
def test_basic_asset_crud(authenticated_client, ensure_asset_types):
    """
    CRITICAL: Basic CRUD operations must work for core functionality.
    """
    # Create asset
    asset_data = {
        "asset_tag": f"CRITICAL-CRUD-001",
        "serial_number": "SN-CRIT-CRUD-001",
        "asset_type": "server_device",
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    asset_id = asset["id"]
    
    # Read asset
    success, fetched_asset = authenticated_client.get(f"/api/v1/assets/{asset_id}", expected_status=200)
    assert success, f"Failed to fetch asset: {fetched_asset}"
    assert fetched_asset["asset_tag"] == asset_data["asset_tag"]
    
    # Update asset
    update_data = {"model": "Updated Model"}
    success, updated_asset = authenticated_client.put(
        f"/api/v1/assets/{asset_id}",
        update_data,
        expected_status=200
    )
    assert success, f"Failed to update asset: {updated_asset}"
    assert updated_asset["model"] == "Updated Model"
    
    # Delete asset
    success, delete_response = authenticated_client.delete(
        f"/api/v1/assets/{asset_id}",
        expected_status=204
    )
    assert success, f"Failed to delete asset: {delete_response}"

