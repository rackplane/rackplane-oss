# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Global Search Test Suite
Tests for global search across all entity types
"""

import pytest


@pytest.mark.integration
@pytest.mark.search
def test_global_search_assets(authenticated_client, test_prefix, test_tenant):
    """
    TC-SEARCH-001: Verify global search finds assets by various fields.
    """
    from app.core.database import SessionLocal
    from app.models.asset_type import AssetTypeModel
    from app.core.tenant_query import apply_tenant_filter
    
    # Ensure network_device asset type exists
    from app.core.tenant import set_current_tenant_id
    set_current_tenant_id(test_tenant["id"])
    
    db = SessionLocal()
    try:
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
    
    # Create test assets
    asset_data_1 = {
        "asset_tag": f"{test_prefix}-SEARCH-SRV-001",
        "serial_number": f"{test_prefix}-SRV-SN-001",
        "asset_type": "server_device",
        "manufacturer": "Dell",
        "model": "PowerEdge R740",
        "status": "active",
        "hostname": "search-server-01"
    }
    
    asset_data_2 = {
        "asset_tag": f"{test_prefix}-SEARCH-SW-001",
        "serial_number": f"{test_prefix}-SW-SN-001",
        "asset_type": "network_device",
        "manufacturer": "Cisco",
        "model": "Nexus 9000",
        "status": "active"
    }
    
    success, asset1 = authenticated_client.post("/api/v1/assets/", asset_data_1, expected_status=201)
    assert success, f"Failed to create asset 1: {asset1}"
    
    success, asset2 = authenticated_client.post("/api/v1/assets/", asset_data_2, expected_status=201)
    assert success, f"Failed to create asset 2: {asset2}"
    
    # Search by asset tag
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": f"{test_prefix}-SEARCH-SRV-001"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert "assets" in results, "Results should include assets"
    assert len(results["assets"]) >= 1, "Should find at least one asset"
    assert results["assets"][0]["asset_tag"] == f"{test_prefix}-SEARCH-SRV-001"
    
    # Search by manufacturer
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "Dell"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert len(results["assets"]) >= 1, "Should find Dell assets"
    assert any(a["manufacturer"] == "Dell" for a in results["assets"]), "Should find Dell manufacturer"
    
    # Search by hostname
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "search-server"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert len(results["assets"]) >= 1, "Should find assets by hostname"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset1['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/assets/{asset2['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.search
def test_global_search_locations(authenticated_client, test_prefix):
    """
    TC-SEARCH-002: Verify global search finds datacenters, rooms, and racks.
    """
    # Create datacenter
    dc_data = {
        "name": f"{test_prefix} Search Datacenter",
        "code": f"{test_prefix}-SEARCH-DC",
        "address": "123 Search Street"
    }
    
    success, datacenter = authenticated_client.post("/api/v1/locations/datacenters", dc_data, expected_status=201)
    assert success, f"Failed to create datacenter: {datacenter}"
    dc_id = datacenter["id"]
    
    # Create room
    room_data = {
        "name": f"{test_prefix} Search Room",
        "code": f"{test_prefix}-SEARCH-ROOM",
        "datacenter_id": dc_id
    }
    
    success, room = authenticated_client.post("/api/v1/locations/rooms", room_data, expected_status=201)
    assert success, f"Failed to create room: {room}"
    room_id = room["id"]
    
    # Create rack
    rack_data = {
        "name": f"{test_prefix} Search Rack",
        "code": f"{test_prefix}-SEARCH-RACK",
        "datacenter_id": dc_id,
        "room_id": room_id,
        "height_u": 42
    }
    
    success, rack = authenticated_client.post("/api/v1/locations/racks", rack_data, expected_status=201)
    assert success, f"Failed to create rack: {rack}"
    
    # Search for datacenter
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": f"{test_prefix} Search Datacenter"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert "datacenters" in results, "Results should include datacenters"
    assert len(results["datacenters"]) >= 1, "Should find datacenter"
    assert results["datacenters"][0]["id"] == dc_id
    
    # Search for room
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "Search Room"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert "rooms" in results, "Results should include rooms"
    assert len(results["rooms"]) >= 1, "Should find room"
    
    # Search for rack
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "Search Rack"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert "racks" in results, "Results should include racks"
    assert len(results["racks"]) >= 1, "Should find rack"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/locations/racks/{rack['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/locations/rooms/{room_id}", expected_status=200)
    authenticated_client.delete(f"/api/v1/locations/datacenters/{dc_id}", expected_status=200)


@pytest.mark.integration
@pytest.mark.search
def test_global_search_multiple_entity_types(authenticated_client, test_prefix):
    """
    TC-SEARCH-003: Verify global search returns results from multiple entity types.
    """
    # Create asset
    asset_data = {
        "asset_tag": f"{test_prefix}-MULTI-SEARCH-001",
        "serial_number": f"{test_prefix}-MS-SN-001",
        "asset_type": "server_device",
        "manufacturer": "MultiSearch",
        "model": "Test Model",
        "status": "active"
    }
    
    success, asset = authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    assert success, f"Failed to create asset: {asset}"
    
    # Create datacenter with similar name
    dc_data = {
        "name": f"{test_prefix} MultiSearch Datacenter",
        "code": f"{test_prefix}-MULTI-DC",
        "address": "MultiSearch Address"
    }
    
    success, datacenter = authenticated_client.post("/api/v1/locations/datacenters", dc_data, expected_status=201)
    assert success, f"Failed to create datacenter: {datacenter}"
    
    # Search for common term
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "MultiSearch"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    
    # Should find both asset and datacenter
    assert results["total_results"] >= 2, f"Should find multiple results, got {results['total_results']}"
    assert len(results["assets"]) >= 1, "Should find asset"
    assert len(results["datacenters"]) >= 1, "Should find datacenter"
    
    # Cleanup
    authenticated_client.delete(f"/api/v1/assets/{asset['id']}", expected_status=200)
    authenticated_client.delete(f"/api/v1/locations/datacenters/{datacenter['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.search
def test_global_search_limit(authenticated_client, test_prefix):
    """
    TC-SEARCH-004: Verify global search respects limit parameter.
    """
    # Create multiple assets
    for i in range(10):
        asset_data = {
            "asset_tag": f"{test_prefix}-LIMIT-{i+1:03d}",
            "serial_number": f"{test_prefix}-LIM-SN-{i+1:03d}",
            "asset_type": "server_device",
            "manufacturer": "LimitTest",
            "model": f"Model {i+1}",
            "status": "active"
        }
        authenticated_client.post("/api/v1/assets/", asset_data, expected_status=201)
    
    # Search with limit
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "LimitTest", "limit": 5},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert len(results["assets"]) <= 5, f"Should respect limit, got {len(results['assets'])} results"
    
    # Cleanup - get all assets and delete them
    success, assets = authenticated_client.get("/api/v1/assets/", params={"asset_type": "server_device"}, expected_status=200)
    if success:
        for asset in assets.get("items", []):
            if asset.get("asset_tag", "").startswith(f"{test_prefix}-LIMIT-"):
                authenticated_client.delete(f"/api/v1/assets/{asset['id']}", expected_status=200)


@pytest.mark.integration
@pytest.mark.search
def test_global_search_no_results(authenticated_client):
    """
    TC-SEARCH-005: Verify global search returns empty results for non-matching queries.
    """
    success, results = authenticated_client.get(
        "/api/v1/search/",
        params={"q": "NONEXISTENTQUERY12345"},
        expected_status=200
    )
    assert success, f"Failed to search: {results}"
    assert results["total_results"] == 0, "Should return 0 results for non-matching query"
    assert len(results["assets"]) == 0, "Should have no assets"
    assert len(results["datacenters"]) == 0, "Should have no datacenters"

