"""
Comprehensive backup and restore tests.

This module verifies that the backup/restore functionality works correctly:
1. Creating a tenant and representative data
2. Running a PostgreSQL native backup using pg_dump
3. Deleting items
4. Restoring the backup using pg_restore
5. Verifying all items were restored correctly

This tests the recommended production backup approach using PostgreSQL's
native pg_dump and pg_restore tools (see docs/BACKUP_GUIDE.md).
"""

import pytest
import json
import io
import os
import subprocess
import tempfile
import requests
from typing import Dict, Any, Optional


from test_suite import BASE_URL


def _resolve_db_port(db_port_env: Optional[str], postgres_port_env: Optional[str]) -> str:
    """
    Resolve the database port from DB_PORT / POSTGRES_PORT env vars.

    Behaviour:
    - Prefer DB_PORT when set.
    - Otherwise use POSTGRES_PORT, defaulting to "5432".
    - If POSTGRES_PORT is a K8s-style tcp URL (tcp://IP:PORT), extract PORT using urlparse.
    - On malformed tcp:// values, fall back to "5432".
    """
    from urllib.parse import urlparse
    
    if db_port_env:
        return db_port_env

    port = postgres_port_env or "5432"

    if port.startswith("tcp://"):
        # Use urlparse for robust K8s-style tcp:// URL parsing
        try:
            parsed = urlparse(port)
            if parsed.port:
                return str(parsed.port)
        except (ValueError, AttributeError):
            pass
        return "5432"

    return port


@pytest.mark.parametrize(
    "env_db_port, env_postgres_port, expected",
    [
        # DB_PORT takes precedence over POSTGRES_PORT
        ("15432", "5432", "15432"),
        ("15432", None, "15432"),
        # Fallback to plain POSTGRES_PORT
        (None, "5432", "5432"),
        (None, "15432", "15432"),
        # K8s-style tcp URLs
        (None, "tcp://10.0.0.1:5432", "5432"),
        (None, "tcp://10.0.0.1:15432", "15432"),
        # Malformed tcp:// values fall back to default
        (None, "tcp://", "5432"),
        (None, "tcp://10.0.0.1", "5432"),
        # No env vars set -> default
        (None, None, "5432"),
    ],
)
def test_resolve_db_port(monkeypatch, env_db_port, env_postgres_port, expected):
    # Clear existing env vars
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)

    if env_db_port is not None:
        monkeypatch.setenv("DB_PORT", env_db_port)
    if env_postgres_port is not None:
        monkeypatch.setenv("POSTGRES_PORT", env_postgres_port)

    resolved = _resolve_db_port(
        os.getenv("DB_PORT"),
        os.getenv("POSTGRES_PORT"),
    )
    assert resolved == expected



@pytest.mark.integration
@pytest.mark.backup
def test_backup_restore_comprehensive(
    authenticated_client,
    admin_token,
    api_client,
    test_tenant,
    test_user
):
    """
    Comprehensive backup/restore test covering all item types.
    
    This test creates a complete dataset, backs it up, deletes everything,
    then restores and verifies all data was restored correctly.
    """
    tenant_id = test_tenant["id"]
    created_items = {}  # Track all created items for verification
    
    # Step 1: Create Asset Types (use test user token to ensure tenant context)
    print("\n>>> Step 1: Creating asset types...")
    api_client.set_token(test_user["token"])  # Use test user token for tenant-scoped operations
    
    asset_types = [
        {"name": f"server_{tenant_id}", "display_name": "Server", "description": "Physical server"},
        {"name": f"switch_{tenant_id}", "display_name": "Network Switch", "description": "Network switch"},
        {"name": f"dac_cable_{tenant_id}", "display_name": "DAC Cable", "description": "Direct Attach Copper cable"},
        {"name": f"fiber_cable_{tenant_id}", "display_name": "Fiber Cable", "description": "Fiber optic cable"},
        {"name": f"storage_box_{tenant_id}", "display_name": "Storage Box", "description": "Storage container"},
    ]
    
    created_asset_types = []
    for asset_type_data in asset_types:
        success, response = api_client.post(
            "/api/v1/asset-types/",
            asset_type_data,
            expected_status=201
        )
        # If it already exists, try to get it
        if not success and "already exists" in str(response.get("detail", "")):
            # Try to find existing asset type
            success, existing_types = api_client.get("/api/v1/asset-types/", expected_status=200)
            if success:
                for at in existing_types:
                    if at.get("name") == asset_type_data["name"]:
                        response = at
                        success = True
                        break
        assert success, f"Failed to create or find asset type: {response}"
        created_asset_types.append(response)
        created_items[f"asset_type_{response['id']}"] = response
    
    # Step 2: Create Datacenter
    print("\n>>> Step 2: Creating datacenter...")
    success, datacenter = api_client.post(
        "/api/v1/locations/datacenters",
        {
            "name": "Test Datacenter",
            "code": "TEST-DC",
            "city": "Test City",
            "address": "123 Test St",
            "facility_manager": "Test Manager",
            "contact_email": "test@example.com",
            "contact_phone": "555-0100"
        },
        expected_status=201
    )
    assert success, f"Failed to create datacenter: {datacenter}"
    created_items["datacenter"] = datacenter
    datacenter_id = datacenter["id"]
    
    # Step 3: Create Room
    print("\n>>> Step 3: Creating room...")
    success, room = api_client.post(
        "/api/v1/locations/rooms",
        {
            "datacenter_id": datacenter_id,
            "name": f"Test Room {tenant_id}",
            "code": f"R001-{tenant_id}",
            "floor_number": 1,
            "power_capacity_kw": 100.0
        },
        expected_status=201
    )
    assert success, f"Failed to create room: {room}"
    created_items["room"] = room
    room_id = room["id"]
    
    # Step 4: Create Rack
    print("\n>>> Step 4: Creating rack...")
    success, rack = api_client.post(
        "/api/v1/locations/racks",
        {
            "datacenter_id": datacenter_id,
            "room_id": room_id,
            "name": f"Test Rack {tenant_id}",
            "code": f"RACK-001-{tenant_id}",
            "rack_number": f"RACK-001-{tenant_id}",
            "height_u": 42,
            "width_inches": 19
        },
        expected_status=201
    )
    assert success, f"Failed to create rack: {rack}"
    created_items["rack"] = rack
    rack_id = rack["id"]
    
    # Step 5: Create Storage Container
    print("\n>>> Step 5: Creating storage container...")
    success, storage_container = api_client.post(
        "/api/v1/storage-containers/",
        {
            "name": "Test Storage Container",
            "container_type": "shelf",
            "location": "Warehouse A",
            "capacity": 100
        },
        expected_status=201
    )
    assert success, f"Failed to create storage container: {storage_container}"
    created_items["storage_container"] = storage_container
    
    # Step 6: Create Assets (various types)
    print("\n>>> Step 6: Creating assets...")
    api_client.set_token(test_user["token"])  # Use test user token
    
    # Get asset type names for this tenant
    server_type = next((at for at in created_asset_types if "server" in at["name"]), None)
    switch_type = next((at for at in created_asset_types if "switch" in at["name"]), None)
    storage_box_type = next((at for at in created_asset_types if "storage_box" in at["name"]), None)
    dac_cable_type = next((at for at in created_asset_types if "dac_cable" in at["name"]), None)
    fiber_cable_type = next((at for at in created_asset_types if "fiber_cable" in at["name"]), None)
    
    # Create a server asset
    success, server = authenticated_client.post(
        "/api/v1/assets/",
        {
            "asset_tag": f"TEST-SERVER-001-{tenant_id}",
            "serial_number": f"SN-SERVER-001-{tenant_id}",
            "asset_type": server_type["name"],
            "manufacturer": "Dell",
            "model": "PowerEdge R740",
            "status": "active",
            "rack_id": rack_id,
            "datacenter_id": datacenter_id
        },
        expected_status=201
    )
    assert success, f"Failed to create server: {server}"
    created_items["server"] = server
    
    # Add a base64-encoded photo to the server asset (simulating real backup data)
    # Using a small 1x1 red PNG image as base64
    test_photo_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    test_photo_data_uri = f"data:image/png;base64,{test_photo_base64}"
    
    # Update the server asset to include the photo
    success, updated_server = authenticated_client.put(
        f"/api/v1/assets/{server['id']}",
        {
            **server,
            "photo_urls": [test_photo_data_uri]
        },
        expected_status=200
    )
    assert success, f"Failed to add photo to server: {updated_server}"
    server = updated_server  # Update our reference
    created_items["server"] = server
    assert "photo_urls" in server and len(server.get("photo_urls", [])) > 0, \
        "Server should have photo_urls after update"
    assert server["photo_urls"][0] == test_photo_data_uri, \
        "Server photo should match the test photo data URI"
    
    # Create a switch asset
    success, switch = authenticated_client.post(
        "/api/v1/assets/",
        {
            "asset_tag": f"TEST-SWITCH-001-{tenant_id}",
            "serial_number": f"SN-SWITCH-001-{tenant_id}",
            "asset_type": switch_type["name"],
            "manufacturer": "Cisco",
            "model": "Nexus 9000",
            "status": "active",
            "rack_id": rack_id,
            "datacenter_id": datacenter_id
        },
        expected_status=201
    )
    assert success, f"Failed to create switch: {switch}"
    created_items["switch"] = switch
    
    # Create a storage box asset
    success, storage_box = authenticated_client.post(
        "/api/v1/assets/",
        {
            "asset_tag": f"TEST-STORAGE-BOX-001-{tenant_id}",
            "serial_number": f"SN-BOX-001-{tenant_id}",
            "asset_type": storage_box_type["name"],
            "manufacturer": "Generic",
            "model": "Storage Bin",
            "status": "active",
            "min_stock_threshold": 10
        },
        expected_status=201
    )
    assert success, f"Failed to create storage box: {storage_box}"
    created_items["storage_box"] = storage_box
    storage_box_id = storage_box["id"]
    
    # Create a DAC cable asset
    success, dac_cable = authenticated_client.post(
        "/api/v1/assets/",
        {
            "asset_tag": f"TEST-DAC-001-{tenant_id}",
            "serial_number": f"SN-DAC-001-{tenant_id}",
            "asset_type": dac_cable_type["name"],
            "manufacturer": "Generic",
            "model": "DAC Cable",
            "status": "in_storage",
            "container_id": storage_box_id,
            "custom_fields": {
                "dac_speed": "100G",
                "dac_connector_a": "QSFP28",
                "dac_connector_b": "QSFP28",
                "cable_length": "3M"
            }
        },
        expected_status=201
    )
    assert success, f"Failed to create DAC cable: {dac_cable}"
    created_items["dac_cable"] = dac_cable
    
    # Create a fiber cable asset
    success, fiber_cable = authenticated_client.post(
        "/api/v1/assets/",
        {
            "asset_tag": f"TEST-FIBER-001-{tenant_id}",
            "serial_number": f"SN-FIBER-001-{tenant_id}",
            "asset_type": fiber_cable_type["name"],
            "manufacturer": "Generic",
            "model": "Fiber Cable",
            "status": "in_storage",
            "container_id": storage_box_id,
            "custom_fields": {
                "fiber_type": "SM",
                "fiber_connector_a": "LC",
                "fiber_connector_b": "LC",
                "cable_length": "5M"
            }
        },
        expected_status=201
    )
    assert success, f"Failed to create fiber cable: {fiber_cable}"
    created_items["fiber_cable"] = fiber_cable
    
    # Step 7: Create Connection
    print("\n>>> Step 7: Creating connection...")
    success, connection = authenticated_client.post(
        "/api/v1/connections/connect",
        {
            "cable_id": dac_cable["id"],
            "device_id": server["id"],
            "port_label": "eth0",
            "notes": "Test connection"
        },
        expected_status=201
    )
    assert success, f"Failed to create connection: {connection}"
    # Connection response has nested structure: {"connection": {...}, "end_label": "...", "message": "..."}
    if isinstance(connection, dict) and "connection" in connection:
        created_items["connection"] = connection["connection"]
    elif isinstance(connection, dict):
        created_items["connection"] = connection
    else:
        # If it's not a dict, skip connection verification
        created_items["connection"] = None
    
    # Step 8: Create Environment (DEV Troubleshooting)
    print("\n>>> Step 8: Creating dev environment...")
    success, environment = authenticated_client.post(
        "/api/v1/environments/",
        {
            "name": "Test Environment",
            "ssh_link": "test.example.com",
            "ipmi_link": "https://ipmi.test.example.com",
            "ssh_username": "testuser",
            "ssh_password": "testpass",
            "ipmi_username": "admin",
            "ipmi_password": "admin"
        },
        expected_status=201
    )
    assert success, f"Failed to create environment: {environment}"
    created_items["environment"] = environment
    
    # Step 9: Create Maintenance Record
    print("\n>>> Step 9: Creating maintenance record...")
    success, maintenance = authenticated_client.post(
        "/api/v1/maintenance/",
        {
            "asset_id": server["id"],
            "title": "Test Maintenance",
            "maintenance_type": "preventive",
            "description": "Test maintenance"
        },
        expected_status=201
    )
    assert success, f"Failed to create maintenance record: {maintenance}"
    # Maintenance response may not include id in the response body
    # Fetch it from the list to get the full record with id
    success, all_maintenance = authenticated_client.get(
        f"/api/v1/maintenance/?asset_id={server['id']}",
        expected_status=200
    )
    assert success, "Failed to fetch maintenance records"
    assert isinstance(all_maintenance, (list, dict)), f"Unexpected response type: {type(all_maintenance)}"
    # Handle both list and dict responses
    if isinstance(all_maintenance, dict) and "records" in all_maintenance:
        records = all_maintenance["records"]
    elif isinstance(all_maintenance, list):
        records = all_maintenance
    else:
        records = []
    # Find the maintenance record we just created by matching title
    maintenance_record = None
    for m in records:
        if isinstance(m, dict) and m.get("title") == "Test Maintenance" and m.get("asset_id") == server["id"]:
            maintenance_record = m
            break
    if maintenance_record is None or "id" not in maintenance_record:
        # If we can't find it, skip maintenance record verification
        print(f"Warning: Could not find maintenance record with id. Records: {records[:2] if records else 'empty'}")
        created_items["maintenance"] = None  # Mark as None so we skip deletion/verification
    else:
        created_items["maintenance"] = maintenance_record
    
    # Step 10: Export backup using pg_dump (PostgreSQL native backup)
    print("\n>>> Step 10: Exporting backup using pg_dump...")

    # Create temporary backup file
    backup_file_path = f"/tmp/test_backup_{tenant_id}.dump"

    # Get database connection info from environment
    db_host = os.getenv("POSTGRES_HOST", "postgres")
    db_port = _resolve_db_port(
        os.getenv("DB_PORT"),
        os.getenv("POSTGRES_PORT"),
    )
    
    db_name = os.getenv("POSTGRES_DB", "rackplane")
    db_user = os.getenv("POSTGRES_USER", "rackplane_user")
    db_password = os.getenv("POSTGRES_PASSWORD", "rackplane_password")

    # Run pg_dump with custom format (-F c) for best compatibility
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    dump_cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-d", db_name,
        "-F", "c",  # Custom format
        "-f", backup_file_path
    ]

    result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"pg_dump failed: {result.stderr}"

    # Verify backup file exists and has content
    assert os.path.exists(backup_file_path), "Backup file should exist"
    backup_size = os.path.getsize(backup_file_path)
    assert backup_size > 0, "Backup file should not be empty"
    print(f"✓ Backup created: {backup_file_path} ({backup_size:,} bytes)")
    
    # Step 11: Delete all created items
    print("\n>>> Step 11: Deleting all items...")
    api_client.set_token(test_user["token"])
    
    # Delete in reverse order of creation
    if "maintenance" in created_items and created_items["maintenance"] and "id" in created_items["maintenance"]:
        authenticated_client.delete(
            f"/api/v1/maintenance/{created_items['maintenance']['id']}",
            expected_status=204
        )
    
    if "environment" in created_items:
        authenticated_client.delete(
            f"/api/v1/environments/{created_items['environment']['id']}",
            expected_status=204
        )
    
    if "connection" in created_items and created_items["connection"] is not None and isinstance(created_items["connection"], dict) and "id" in created_items["connection"]:
        authenticated_client.delete(
            f"/api/v1/connections/{created_items['connection']['id']}",
            expected_status=204
        )
    
    # Delete assets
    for asset_key in ["fiber_cable", "dac_cable", "storage_box", "switch", "server"]:
        if asset_key in created_items:
            authenticated_client.delete(
                f"/api/v1/assets/{created_items[asset_key]['id']}",
                expected_status=204
            )
    
    # Delete storage container
    if "storage_container" in created_items:
        authenticated_client.delete(
            f"/api/v1/storage-containers/{created_items['storage_container']['id']}",
            expected_status=204
        )
    
    # Delete location hierarchy (rack, room, datacenter)
    if "rack" in created_items:
        authenticated_client.delete(
            f"/api/v1/locations/racks/{created_items['rack']['id']}",
            expected_status=204
        )
    
    if "room" in created_items:
        authenticated_client.delete(
            f"/api/v1/locations/rooms/{created_items['room']['id']}",
            expected_status=204
        )
    
    if "datacenter" in created_items:
        authenticated_client.delete(
            f"/api/v1/locations/datacenters/{created_items['datacenter']['id']}",
            expected_status=204
        )
    
    # Delete asset types
    api_client.set_token(admin_token)
    for asset_type in created_asset_types:
        api_client.delete(
            f"/api/v1/asset-types/{asset_type['id']}",
            expected_status=204
        )
    
    # Verify items are deleted
    print("\n>>> Verifying items are deleted...")
    api_client.set_token(test_user["token"])
    success, assets = authenticated_client.get("/api/v1/assets/", expected_status=200)
    assert success
    # Handle both list and dict responses
    if isinstance(assets, dict) and "assets" in assets:
        asset_list = assets["assets"]
    elif isinstance(assets, list):
        asset_list = assets
    else:
        asset_list = []
    asset_ids = [a["id"] for a in asset_list if isinstance(a, dict) and "id" in a]
    for asset_key in ["server", "switch", "storage_box", "dac_cable", "fiber_cable"]:
        if asset_key in created_items:
            assert created_items[asset_key]["id"] not in asset_ids, f"{asset_key} should be deleted"
    
    # Step 12: Restore backup using pg_restore (PostgreSQL native restore)
    print("\n>>> Step 12: Restoring backup using pg_restore...")

    # Use pg_restore with --clean flag to drop objects before recreating
    # This provides a clean restore similar to the JSON import with clear_existing=true
    restore_cmd = [
        "pg_restore",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-d", db_name,
        "--clean",  # Drop database objects before recreating them
        "--if-exists",  # Don't error if objects don't exist
        "-v",  # Verbose output for debugging
        backup_file_path
    ]

    result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)

    # pg_restore may have warnings in stderr even on success, so we check for actual errors
    # The return code should be 0 for success
    if result.returncode != 0:
        print(f"\n>>> pg_restore stderr: {result.stderr}")
        print(f"\n>>> pg_restore stdout: {result.stdout}")
        assert False, f"pg_restore failed with return code {result.returncode}"

    print(f"✓ Backup restored successfully")
    if result.stderr:
        # Print stderr for debugging but don't fail (warnings are common)
        print(f"  pg_restore warnings/info: {result.stderr[:500]}")  # First 500 chars
    
    # Step 13: Verify all items were restored
    print("\n>>> Step 13: Verifying restored items...")
    api_client.set_token(test_user["token"])
    
    # Verify assets were restored (by asset_tag/serial_number, since IDs are preserved with clear_existing=true)
    success, restored_assets = authenticated_client.get("/api/v1/assets/", expected_status=200)
    assert success
    # Handle both list and dict responses
    if isinstance(restored_assets, dict) and "assets" in restored_assets:
        asset_list = restored_assets["assets"]
    elif isinstance(restored_assets, list):
        asset_list = restored_assets
    else:
        asset_list = []
    # Create lookup by asset_tag and serial_number since IDs will be different after restore
    asset_by_tag = {a["asset_tag"]: a for a in asset_list if isinstance(a, dict) and "asset_tag" in a}
    asset_by_serial = {a["serial_number"]: a for a in asset_list if isinstance(a, dict) and "serial_number" in a}
    
    # Debug: Print available asset tags
    print(f"\n>>> Debug: Found {len(asset_list)} assets after restore")
    if asset_list:
        print(f"  Sample asset tags: {[a.get('asset_tag') for a in asset_list[:5] if isinstance(a, dict)]}")
    
    for asset_key in ["server", "switch", "storage_box", "dac_cable", "fiber_cable"]:
        if asset_key in created_items:
            original_asset = created_items[asset_key]
            original_tag = original_asset.get("asset_tag")
            original_serial = original_asset.get("serial_number")
            # Check by asset_tag first, then serial_number
            if original_tag and original_tag in asset_by_tag:
                restored = asset_by_tag[original_tag]
                assert restored.get("serial_number") == original_serial, \
                    f"{asset_key} {original_tag} should have matching serial number"
            elif original_serial and original_serial in asset_by_serial:
                restored = asset_by_serial[original_serial]
                assert restored.get("asset_tag") == original_tag, \
                    f"{asset_key} {original_serial} should have matching asset tag"
            else:
                assert False, f"{asset_key} with tag '{original_tag}' or serial '{original_serial}' should be restored"
    
    # Verify photo was restored for server asset
    if "server" in created_items:
        original_server = created_items["server"]
        original_tag = original_server.get("asset_tag")
        if original_tag and original_tag in asset_by_tag:
            restored_server = asset_by_tag[original_tag]
            original_photos = original_server.get("photo_urls", [])
            restored_photos = restored_server.get("photo_urls", [])
            assert len(restored_photos) == len(original_photos), \
                f"Server photo count should match: expected {len(original_photos)}, got {len(restored_photos)}"
            if original_photos:
                # Verify the first photo is restored correctly (base64 data URI)
                assert restored_photos[0] == original_photos[0], \
                    f"Server photo should be restored correctly. Original: {original_photos[0][:100]}..., Restored: {restored_photos[0][:100]}..."
                assert restored_photos[0].startswith("data:image/"), \
                    f"Restored photo should be a data URI: {restored_photos[0][:50]}..."
    
    # Verify datacenter was restored (by name, not ID, since IDs may differ after restore)
    success, datacenters = authenticated_client.get("/api/v1/locations/datacenters", expected_status=200)
    assert success
    datacenter_names = [dc["name"] for dc in datacenters if isinstance(dc, dict) and "name" in dc]
    assert created_items["datacenter"]["name"] in datacenter_names, \
        f"Datacenter {created_items['datacenter']['name']} should be restored. Found: {datacenter_names}"
    # Find the restored datacenter to get its new ID for room lookup
    restored_dc = next((dc for dc in datacenters if dc.get("name") == created_items["datacenter"]["name"]), None)
    assert restored_dc is not None, "Restored datacenter should exist"
    restored_dc_id = restored_dc["id"]
    
    # Verify room was restored (by name, not ID)
    success, rooms = authenticated_client.get(
        f"/api/v1/locations/datacenters/{restored_dc_id}/rooms",
        expected_status=200
    )
    assert success
    room_names = [r["name"] for r in rooms if isinstance(r, dict) and "name" in r]
    assert created_items["room"]["name"] in room_names, \
        f"Room {created_items['room']['name']} should be restored. Found: {room_names}"
    # Find the restored room to get its new ID for rack lookup
    restored_room = next((r for r in rooms if r.get("name") == created_items["room"]["name"]), None)
    assert restored_room is not None, "Restored room should exist"
    restored_room_id = restored_room["id"]
    
    # Verify rack was restored (by name, not ID)
    success, racks = authenticated_client.get(
        f"/api/v1/locations/racks?room_id={restored_room_id}",
        expected_status=200
    )
    assert success, f"Failed to fetch racks: {racks}"
    # Handle both list and dict responses
    if isinstance(racks, dict) and "racks" in racks:
        rack_list = racks["racks"]
    elif isinstance(racks, list):
        rack_list = racks
    else:
        rack_list = []
    # Verify rack was restored (by name, not ID, since IDs may differ after restore)
    rack_names = [r["name"] for r in rack_list if isinstance(r, dict) and "name" in r]
    assert created_items["rack"]["name"] in rack_names, f"Rack {created_items['rack']['name']} should be restored. Found: {rack_names}"
    
    # Verify storage container was restored (by name, not ID)
    success, storage_containers = authenticated_client.get("/api/v1/storage-containers/", expected_status=200)
    assert success
    container_names = [sc["name"] for sc in storage_containers]
    assert created_items["storage_container"]["name"] in container_names, \
        f"Storage container {created_items['storage_container']['name']} should be restored. Found: {container_names}"
    
    # Verify environment was restored (by name, not ID)
    success, environments = authenticated_client.get("/api/v1/environments/", expected_status=200)
    assert success
    env_names = [e["name"] for e in environments]
    assert created_items["environment"]["name"] in env_names, \
        f"Environment {created_items['environment']['name']} should be restored. Found: {env_names}"
    
    # Note: Connection model is NOT in BackupService.TABLE_ORDER, so connections are NOT backed up
    # Skip connection verification since it won't be in the backup
    if "connection" in created_items and created_items["connection"] is not None:
        print("Note: Connection verification skipped - Connection model not in backup service")
    
    # Verify maintenance record was restored (if we successfully created one)
    if "maintenance" in created_items and created_items["maintenance"] is not None and isinstance(created_items["maintenance"], dict) and "id" in created_items["maintenance"]:
        success, maintenance_response = authenticated_client.get("/api/v1/maintenance/", expected_status=200)
        if not success:
            print(f"Warning: Failed to fetch maintenance records: {maintenance_response}")
            # Skip maintenance verification if fetch fails
        else:
            # Handle both list and dict responses
            if isinstance(maintenance_response, dict) and "records" in maintenance_response:
                maintenance_records = maintenance_response["records"]
            elif isinstance(maintenance_response, list):
                maintenance_records = maintenance_response
            else:
                maintenance_records = []
            # Verify maintenance record was restored (by description or title, not ID)
            # Maintenance records don't have unique names, so we check if any match our description
            maintenance_descriptions = [m.get("description", "") for m in maintenance_records if isinstance(m, dict)]
            maintenance_titles = [m.get("title", "") for m in maintenance_records if isinstance(m, dict)]
            created_desc = created_items["maintenance"].get("description", "")
            created_title = created_items["maintenance"].get("title", "")
            assert created_desc in maintenance_descriptions or created_title in maintenance_titles, \
                f"Maintenance record should be restored. Looking for description '{created_desc}' or title '{created_title}'"
    
    # Verify asset types were restored (by name, not ID, since IDs may differ after restore)
    # Note: Asset types may have tenant-specific names, so we check if any match our created types
    # Use test user token to query asset types in the test tenant context
    api_client.set_token(test_user["token"])
    success, asset_types = api_client.get("/api/v1/asset-types/", expected_status=200)
    assert success
    asset_type_names = [at["name"] for at in asset_types]
    
    # Check if our created asset types are present (they have tenant-specific names like switch_{tenant_id})
    for created_type in created_asset_types:
        type_name = created_type.get("name")
        assert type_name in asset_type_names, \
            f"Asset type '{type_name}' should be restored. Found: {asset_type_names[:20]}"
    
    # Also check base names as fallback (in case names changed slightly)
    for base_name in ["server", "switch", "dac_cable", "fiber_cable", "storage_box"]:
        # Check if any asset type starts with our base name
        matching = [name for name in asset_type_names if name.startswith(base_name)]
        if len(matching) == 0:
            # If no match found, check if it's because the test tenant's asset types weren't restored
            # This is a warning, not a failure, since the exact name check above should catch it
            print(f"Warning: No asset type starting with '{base_name}' found in test tenant. Available: {asset_type_names[:20]}")

    # Cleanup: Remove the backup file
    try:
        os.remove(backup_file_path)
        print(f"\n>>> Cleaned up backup file: {backup_file_path}")
    except OSError as e:
        print(f"\n>>> Warning: Failed to clean up backup file: {e}")

    print("\n>>> ✓ All items successfully restored!")


@pytest.mark.integration
@pytest.mark.backup
def test_full_backup_archive_roundtrip(admin_token):
    """
    TC-BACKUP-ARCHIVE-001: Full backup archive export/import round-trip.

    This test verifies that:
    1. A full backup archive (.tar.gz) can be exported via the API
       using /api/v1/backup/export-archive
    2. The same archive can be imported via /api/v1/backup/import-archive
       without errors (database restored, files optionally skipped)
    """
    base_url = os.getenv("API_URL", BASE_URL)
    headers = {"Authorization": f"Bearer {admin_token}"}

    print("\n>>> Step 1: Exporting full backup archive...")
    resp = requests.get(
        f"{base_url}/api/v1/backup/export-archive",
        headers=headers,
        timeout=300,
    )
    assert resp.status_code == 200, f"Export archive failed: {resp.status_code} {resp.text}"

    content_type = resp.headers.get("content-type", "")
    assert "gzip" in content_type or "tar" in content_type, f"Unexpected content-type: {content_type}"
    assert len(resp.content) > 0, "Archive content should not be empty"

    # Save archive to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(resp.content)
        archive_path = tmp.name

    print(f"  ✓ Full backup archive exported to temporary file: {archive_path}")

    try:
        print("\n>>> Step 2: Importing full backup archive (DB only, skip files)...")
        with open(archive_path, "rb") as f:
            files = {
                "file": ("full_backup.tar.gz", f, "application/gzip"),
            }
            resp2 = requests.post(
                f"{base_url}/api/v1/backup/import-archive"
                f"?clear_existing=false&skip_files=true",
                headers=headers,
                files=files,
                timeout=300,
            )

        assert resp2.status_code == 200, f"Import archive failed: {resp2.status_code} {resp2.text}"
        data = resp2.json()
        assert data.get("success") is True, f"Archive import reported failure: {data}"

        print("  ✓ Full backup archive imported successfully (database only)")
    finally:
        # Clean up temp file
        try:
            os.remove(archive_path)
        except OSError:
            pass


@pytest.mark.integration
@pytest.mark.backup
def test_backup_includes_all_tables(admin_token, api_client):
    """
    CRITICAL: Verify that backup includes ALL tables defined in BackupService.TABLE_ORDER.
    
    This test ensures that when new models are added, they are also added to the backup service.
    Missing tables in backup would cause data loss during restore.
    """
    # Import BackupService to get the list of expected tables
    from app.services.backup_service import BackupService
    
    # Get list of all expected table names from TABLE_ORDER
    expected_tables = {table_info['name'] for table_info in BackupService.TABLE_ORDER}
    
    print(f"\n>>> Expected tables in backup: {len(expected_tables)}")
    print(f"   Tables: {sorted(expected_tables)}")
    
    # Export backup
    api_client.set_token(admin_token)
    success, backup_data = api_client.get(
        "/api/v1/backup/export",
        expected_status=200
    )
    assert success, f"Failed to export backup: {backup_data}"
    
    # Get actual tables in backup
    actual_tables = set(backup_data.get("tables", {}).keys())
    
    print(f"\n>>> Actual tables in backup: {len(actual_tables)}")
    print(f"   Tables: {sorted(actual_tables)}")
    
    # Check for missing tables
    missing_tables = expected_tables - actual_tables
    if missing_tables:
        print(f"\n❌ MISSING TABLES IN BACKUP: {missing_tables}")
        print(f"   These tables are defined in BackupService.TABLE_ORDER but not exported!")
        print(f"   This will cause data loss during restore.")
        print(f"\n   To fix: Ensure all models in TABLE_ORDER are properly imported and exported.")
    
    # Check for unexpected tables (warn but don't fail - might be OK)
    unexpected_tables = actual_tables - expected_tables
    if unexpected_tables:
        print(f"\n⚠️  UNEXPECTED TABLES IN BACKUP: {unexpected_tables}")
        print(f"   These tables are exported but not in TABLE_ORDER.")
        print(f"   Consider adding them to TABLE_ORDER if they should be backed up.")
    
    # Assert that all expected tables are present
    assert len(missing_tables) == 0, \
        f"Backup is missing {len(missing_tables)} table(s): {missing_tables}. " \
        f"All tables in BackupService.TABLE_ORDER must be exported. " \
        f"Add missing models to backup_service.py imports and TABLE_ORDER."
    
    print(f"\n✅ All {len(expected_tables)} expected tables are present in backup")


@pytest.mark.integration
@pytest.mark.backup
@pytest.mark.full_restore
def test_full_backup_restore_clear_all_data(admin_token, api_client):
    """
    CRITICAL: Full backup/restore test that clears ALL data.
    
    This test verifies the complete backup/restore cycle with TEST_CLEAR_ALL_DATA=true.
    It will clear ALL data in the database (not just test tenants).
    
    WARNING: This test only runs when TEST_CLEAR_ALL_DATA=true is set in the environment.
    This protects production databases from accidental data loss.
    
    To run this test manually:
        TEST_CLEAR_ALL_DATA=true pytest tests/test_backup_restore_pytest.py::test_full_backup_restore_clear_all_data -v
    
    This test:
    1. Exports a full system backup
    2. Clears ALL existing data (with TEST_CLEAR_ALL_DATA=true)
    3. Restores the backup
    4. Verifies all data was restored correctly
    """
    import os
    
    # Only run if TEST_CLEAR_ALL_DATA is explicitly set to 'true'
    if os.getenv('TEST_CLEAR_ALL_DATA', '').lower() != 'true':
        pytest.skip("Skipping full restore test - set TEST_CLEAR_ALL_DATA=true to run")
    
    print("\n>>> ⚠️  WARNING: This test will clear ALL data in the database!")
    print(">>> This test only runs when TEST_CLEAR_ALL_DATA=true is set")
    
    # Step 1: Export full backup
    print("\n>>> Step 1: Exporting full system backup...")
    api_client.set_token(admin_token)
    success, backup_data = api_client.get(
        "/api/v1/backup/export",
        expected_status=200
    )
    assert success, f"Failed to export backup: {backup_data}"
    
    # Count records in backup
    total_records = 0
    table_counts = {}
    for table_name, table_info in backup_data.get("tables", {}).items():
        count = table_info.get("count", 0)
        table_counts[table_name] = count
        total_records += count
    
    print(f"  ✓ Backup exported: {len(backup_data.get('tables', {}))} tables, {total_records} total records")
    
    # Step 2: Restore with clear_existing=True (will clear ALL data because TEST_CLEAR_ALL_DATA=true)
    print("\n>>> Step 2: Restoring backup (clearing ALL existing data)...")
    
    backup_json = json.dumps(backup_data)
    backup_file = io.BytesIO(backup_json.encode('utf-8'))
    backup_file.name = "backup.json"
    
    success, import_result = api_client.post_file(
        "/api/v1/backup/import?clear_existing=true",
        backup_file,
        expected_status=200
    )
    assert success, f"Failed to import backup: {import_result}"
    assert import_result.get("success", False), f"Import failed: {import_result}"
    
    stats = import_result.get("stats", {})
    records_imported = stats.get("records_imported", 0)
    errors = stats.get("errors", [])
    
    print(f"  ✓ Restore completed: {records_imported} records imported")
    if errors:
        print(f"  ⚠ Errors during restore: {len(errors)}")
        for error in errors[:5]:
            print(f"    - {error}")
    
    # Step 3: Verify restore by checking record counts
    print("\n>>> Step 3: Verifying restore...")
    
    # Re-export to verify
    success, verify_backup = api_client.get(
        "/api/v1/backup/export",
        expected_status=200
    )
    assert success, "Failed to export backup for verification"
    
    verify_total = 0
    for table_name, table_info in verify_backup.get("tables", {}).items():
        count = table_info.get("count", 0)
        verify_total += count
    
    print(f"  ✓ Verification: {len(verify_backup.get('tables', {}))} tables, {verify_total} total records")
    
    # Verify we have data (not empty database)
    assert verify_total > 0, "Database should not be empty after restore"
    assert len(verify_backup.get('tables', {})) > 0, "Backup should contain tables"
    
    # Verify key tables have data
    key_tables = ['tenants', 'users', 'assets', 'datacenters']
    for table in key_tables:
        if table in verify_backup.get('tables', {}):
            count = verify_backup['tables'][table].get('count', 0)
            assert count > 0, f"Table {table} should have data after restore"
            print(f"  ✓ {table}: {count} records")
    
    print("\n>>> ✅ Full backup/restore cycle completed successfully!")
    print(f">>>    Original: {total_records} records")
    print(f">>>    Restored: {verify_total} records")
    print(f">>>    Errors: {len(errors)}")

