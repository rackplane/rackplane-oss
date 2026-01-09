"""
Pytest-based tests for rack visualization and storage container filtering.

Tests the integration between racks and storage containers, including:
- Rack visualization only shows mounted devices
- Storage container filtering by rack number
- Bulk assign to rack functionality
"""

import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.tenant import set_current_tenant_id, clear_tenant_id
from app.models.asset import Asset
from app.models.storage_container import StorageContainer
from app.models.location import Rack, Room, Datacenter
from app.models.asset_type import AssetTypeModel


@pytest.mark.integration
@pytest.mark.rack
@pytest.mark.storage
def test_rack_visualization_only_shows_mounted_devices(authenticated_client, test_prefix, test_tenant):
    """
    TC-RACK-001: Rack visualization should only show assets with rack_position_start
    
    This test verifies that assets assigned to a rack but not mounted (no rack_position_start)
    do not appear in the rack visualization.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create asset type
        asset_type = AssetTypeModel(
            name='server',
            display_name='Server',
            description='Test server',
            tenant_id=test_tenant["id"]
        )
        db.add(asset_type)
        db.commit()
        
        # Create datacenter and room
        datacenter = Datacenter(
            name=f"{test_prefix} DC",
            code=f"{test_prefix}-DC",
            tenant_id=test_tenant["id"]
        )
        db.add(datacenter)
        db.commit()
        db.refresh(datacenter)
        
        room = Room(
            name=f"{test_prefix} Room",
            code=f"{test_prefix}-ROOM",
            datacenter_id=datacenter.id,
            tenant_id=test_tenant["id"]
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create rack
        rack = Rack(
            name=f"{test_prefix} Rack",
            code=f"{test_prefix}-RACK-8-31",
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack)
        db.commit()
        db.refresh(rack)
        
        # Create mounted asset (should appear in visualization)
        mounted_asset_data = {
            "asset_tag": f"{test_prefix}-Mounted-001",
            "serial_number": f"{test_prefix}-MNT-SN-001",
            "asset_type": "server",
            "manufacturer": "Test",
            "model": "Server Model",
            "status": "deployed",
            "rack_id": rack.id,
            "rack_position_start": 10,
            "rack_position_end": 11,
            "height_u": 2
        }
        success, mounted_asset = authenticated_client.post("/api/v1/assets/", mounted_asset_data, expected_status=201)
        assert success, f"Failed to create mounted asset: {mounted_asset}"
        
        # Create unmounted asset (assigned to rack but no position - should NOT appear)
        unmounted_asset_data = {
            "asset_tag": f"{test_prefix}-Unmounted-001",
            "serial_number": f"{test_prefix}-UNM-SN-001",
            "asset_type": "server",
            "manufacturer": "Test",
            "model": "Server Model",
            "status": "staging",
            "rack_id": rack.id
            # No rack_position_start - this is the key difference
        }
        success, unmounted_asset = authenticated_client.post("/api/v1/assets/", unmounted_asset_data, expected_status=201)
        assert success, f"Failed to create unmounted asset: {unmounted_asset}"
        
        # Fetch assets for the rack
        success, response = authenticated_client.get("/api/v1/assets/", params={"rack_id": rack.id})
        assert success, f"Failed to fetch rack assets: {response}"
        
        assets = response.get("assets", [])
        
        # Filter to only mounted assets (what visualization should show)
        mounted_assets = [a for a in assets if a.get("rack_position_start") and a["rack_position_start"] >= 1]
        
        # Should only have 1 mounted asset
        assert len(mounted_assets) == 1, f"Expected 1 mounted asset, got {len(mounted_assets)}"
        assert mounted_assets[0]["asset_tag"] == f"{test_prefix}-Mounted-001", \
            f"Expected mounted asset, got {mounted_assets[0]['asset_tag']}"
        
        # Total assets should be 2 (both assigned to rack)
        assert len(assets) == 2, f"Expected 2 total assets, got {len(assets)}"
        
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.rack
@pytest.mark.storage
def test_storage_container_filtering_by_rack_number(authenticated_client, test_prefix, test_tenant):
    """
    TC-RACK-002: Storage containers should be filtered by rack number in name/location
    
    This test verifies that storage containers are correctly associated with specific racks
    based on rack number in their name or location, handling both dots and dashes.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create datacenter and room
        datacenter = Datacenter(
            name=f"{test_prefix} DC",
            code=f"{test_prefix}-DC",
            tenant_id=test_tenant["id"]
        )
        db.add(datacenter)
        db.commit()
        db.refresh(datacenter)
        
        room = Room(
            name=f"{test_prefix} Room",
            code=f"{test_prefix}-ROOM",
            datacenter_id=datacenter.id,
            tenant_id=test_tenant["id"]
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create two racks in the same room
        rack1 = Rack(
            name=f"{test_prefix} Rack 8.31",
            code=f"{test_prefix}-RACK-8-31",  # Dash format
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack1)
        
        rack2 = Rack(
            name=f"{test_prefix} Rack 8.32",
            code=f"{test_prefix}-RACK-8-32",  # Dash format
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack2)
        db.commit()
        db.refresh(rack1)
        db.refresh(rack2)
        
        # Create storage container for rack 8.31 (dot format in name)
        container1_data = {
            "name": f"Bottom of Rack 8.31",  # Dot format
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id
        }
        success, container1 = authenticated_client.post("/api/v1/storage-containers/", container1_data, expected_status=201)
        assert success, f"Failed to create container 1: {container1}"
        
        # Create storage container for rack 8.32 (dash format in location)
        container2_data = {
            "name": f"Bottom of Rack 8-32",  # Dash format
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id,
            "location": f"Rack 8-32 bottom"
        }
        success, container2 = authenticated_client.post("/api/v1/storage-containers/", container2_data, expected_status=201)
        assert success, f"Failed to create container 2: {container2}"
        
        # Create general container (no rack mentioned)
        container3_data = {
            "name": f"General Storage Box",
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id
        }
        success, container3 = authenticated_client.post("/api/v1/storage-containers/", container3_data, expected_status=201)
        assert success, f"Failed to create container 3: {container3}"
        
        # Fetch all containers in the room
        success, containers = authenticated_client.get("/api/v1/storage-containers/")
        assert success, f"Failed to fetch containers: {containers}"
        
        # Filter containers for rack1 (should get container1 and container3)
        containers_in_room = [c for c in containers if c.get("room_id") == room.id]
        
        # Container1 mentions "8.31" - should match rack1 (RACK-8-31)
        # Container2 mentions "8-32" - should NOT match rack1
        # Container3 doesn't mention a rack - should match all racks in room
        
        # Test the filtering logic (simulating frontend logic)
        def extract_rack_number(code: str) -> str:
            # Remove "RACK-" prefix if present, then normalize dots/dashes
            # Handle both "RACK-8-31" and "PYTEST-RACK-8-31" formats
            normalized = code.lower()
            # Remove everything up to and including "rack-"
            if "rack-" in normalized:
                normalized = normalized.split("rack-")[-1]
            elif "rack" in normalized:
                normalized = normalized.split("rack")[-1].lstrip("-")
            # Replace dots with dashes for consistent matching
            return normalized.replace(".", "-")
        
        rack1_number = extract_rack_number(rack1.code)
        # rack1.code is like "PYTEST-RACK-8-31", so rack1_number should be "8-31"
        
        def matches_rack(container: dict, rack_number: str) -> bool:
            location_text = (container.get("location") or "").lower().replace(".", "-")
            name_text = (container.get("name") or "").lower().replace(".", "-")
            
            # Check if location or name mentions a rack
            mentions_rack = "rack" in location_text or "rack" in name_text
            
            if mentions_rack:
                # If it mentions a rack, check if it's this specific rack
                # Look for the rack number pattern in the location or name
                return rack_number in location_text or rack_number in name_text
            # If it doesn't mention a specific rack, include it (it's a general container in the room)
            return True
        
        matching_containers = [c for c in containers_in_room if matches_rack(c, rack1_number)]
        
        # Should match container1 (mentions 8.31) and container3 (general)
        assert len(matching_containers) == 2, \
            f"Expected 2 containers for rack1, got {len(matching_containers)}: {[c['name'] for c in matching_containers]}"
        
        matching_names = [c["name"] for c in matching_containers]
        assert "Bottom of Rack 8.31" in matching_names, "Container1 should match rack1"
        assert "General Storage Box" in matching_names, "Container3 should match all racks"
        assert "Bottom of Rack 8-32" not in matching_names, "Container2 should NOT match rack1"
        
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.rack
@pytest.mark.storage
def test_bulk_assign_to_rack_sets_container_location(authenticated_client, test_prefix, test_tenant):
    """
    TC-RACK-003: Bulk assign to rack should set room_id on storage container, not rack_id on items
    
    This test verifies that when bulk assigning a storage container to a rack,
    the container's location is updated, not individual items.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])

        # Get or create asset type
        asset_type = db.query(AssetTypeModel).filter(
            AssetTypeModel.name == 'dac_cable',
            AssetTypeModel.tenant_id == test_tenant["id"]
        ).first()

        if not asset_type:
            asset_type = AssetTypeModel(
                name='dac_cable',
                display_name='DAC Cable',
                description='Test cable',
                tenant_id=test_tenant["id"]
            )
            db.add(asset_type)
            db.commit()
        
        # Create datacenter and room
        datacenter = Datacenter(
            name=f"{test_prefix} DC",
            code=f"{test_prefix}-DC",
            tenant_id=test_tenant["id"]
        )
        db.add(datacenter)
        db.commit()
        db.refresh(datacenter)
        
        room = Room(
            name=f"{test_prefix} Room",
            code=f"{test_prefix}-ROOM",
            datacenter_id=datacenter.id,
            tenant_id=test_tenant["id"]
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create rack
        rack = Rack(
            name=f"{test_prefix} Rack",
            code=f"{test_prefix}-RACK-8-31",
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack)
        db.commit()
        db.refresh(rack)
        
        # Create storage container
        container_data = {
            "name": f"{test_prefix} Test Box",
            "container_type": "box",
            "datacenter_id": datacenter.id
            # No room_id initially
        }
        success, container = authenticated_client.post("/api/v1/storage-containers/", container_data, expected_status=201)
        assert success, f"Failed to create container: {container}"
        container_id = container["id"]
        
        # Create items in the container
        items = []
        for i in range(3):
            item_data = {
                "asset_tag": f"{test_prefix}-Cable-{i+1}",
                "serial_number": f"{test_prefix}-CABLE-SN-{i+1}",
                "asset_type": "dac_cable",
                "manufacturer": "Test",
                "model": "1m",
                "status": "in_storage",
                "storage_container_id": container_id
            }
            success, item = authenticated_client.post("/api/v1/assets/", item_data, expected_status=201)
            assert success, f"Failed to create item {i+1}: {item}"
            items.append(item)
        
        # Verify items don't have rack_id
        for item in items:
            assert item.get("rack_id") is None, f"Item should not have rack_id initially: {item}"
        
        # Bulk assign container to rack (simulate the API call)
        # This should update the container's room_id and location
        success, updated_container = authenticated_client.put(
            f"/api/v1/storage-containers/{container_id}",
            {
                "room_id": room.id,
                "datacenter_id": datacenter.id,
                "location": f"Bottom of rack {rack.code}"
            },
            expected_status=200
        )
        assert success, f"Failed to update container: {updated_container}"
        assert updated_container["room_id"] == room.id, \
            f"Container room_id should be {room.id}, got {updated_container.get('room_id')}"
        assert "rack" in updated_container.get("location", "").lower(), \
            f"Container location should mention rack, got {updated_container.get('location')}"
        
        # Verify items still don't have rack_id (they should remain unchanged)
        for item in items:
            success, updated_item = authenticated_client.get(f"/api/v1/assets/{item['id']}")
            assert success, f"Failed to fetch item: {updated_item}"
            assert updated_item.get("rack_id") is None, \
                f"Item should not have rack_id after bulk assign: {updated_item}"
            assert updated_item.get("storage_container_id") == container_id, \
                f"Item should still be in container: {updated_item}"
        
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.rack
@pytest.mark.storage
def test_storage_containers_appear_in_rack_detail(authenticated_client, test_prefix, test_tenant):
    """
    TC-RACK-004: Storage containers in the same room should appear in rack detail view
    
    This test verifies that storage containers in the same room as a rack
    are correctly associated and can be retrieved.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create datacenter and room
        datacenter = Datacenter(
            name=f"{test_prefix} DC",
            code=f"{test_prefix}-DC",
            tenant_id=test_tenant["id"]
        )
        db.add(datacenter)
        db.commit()
        db.refresh(datacenter)
        
        room = Room(
            name=f"{test_prefix} Room",
            code=f"{test_prefix}-ROOM",
            datacenter_id=datacenter.id,
            tenant_id=test_tenant["id"]
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create rack
        rack = Rack(
            name=f"{test_prefix} Rack",
            code=f"{test_prefix}-RACK-8-31",
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack)
        db.commit()
        db.refresh(rack)
        
        # Create storage container in the same room
        container_data = {
            "name": f"Bottom of Rack 8.31",
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id
        }
        success, container = authenticated_client.post("/api/v1/storage-containers/", container_data, expected_status=201)
        assert success, f"Failed to create container: {container}"
        
        # Fetch all containers
        success, containers = authenticated_client.get("/api/v1/storage-containers/")
        assert success, f"Failed to fetch containers: {containers}"
        
        # Filter containers in the same room as the rack
        containers_in_room = [c for c in containers if c.get("room_id") == room.id]
        
        assert len(containers_in_room) >= 1, \
            f"Expected at least 1 container in room, got {len(containers_in_room)}"
        
        # Verify the container is in the list
        container_names = [c["name"] for c in containers_in_room]
        assert "Bottom of Rack 8.31" in container_names, \
            f"Container should be in room, got containers: {container_names}"
        
    finally:
        clear_tenant_id()
        db.close()


@pytest.mark.integration
@pytest.mark.rack
@pytest.mark.storage
def test_storage_containers_filtered_by_rack_in_same_room(authenticated_client, test_prefix, test_tenant):
    """
    TC-RACK-005: Storage containers should only show for their specific rack, not other racks in same room
    
    This test verifies that when multiple racks are in the same room, each rack
    only shows containers that mention its specific rack number.
    """
    db = SessionLocal()
    try:
        set_current_tenant_id(test_tenant["id"])
        
        # Create datacenter and room
        datacenter = Datacenter(
            name=f"{test_prefix} DC",
            code=f"{test_prefix}-DC",
            tenant_id=test_tenant["id"]
        )
        db.add(datacenter)
        db.commit()
        db.refresh(datacenter)
        
        room = Room(
            name=f"{test_prefix} Room",
            code=f"{test_prefix}-ROOM",
            datacenter_id=datacenter.id,
            tenant_id=test_tenant["id"]
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        
        # Create two racks in the same room
        rack1 = Rack(
            name=f"{test_prefix} Rack 8.31",
            code=f"{test_prefix}-RACK-8-31",
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack1)
        
        rack2 = Rack(
            name=f"{test_prefix} Rack 8.30",
            code=f"{test_prefix}-RACK-8-30",
            datacenter_id=datacenter.id,
            room_id=room.id,
            height_u=42,
            tenant_id=test_tenant["id"]
        )
        db.add(rack2)
        db.commit()
        db.refresh(rack1)
        db.refresh(rack2)
        
        # Create storage container for rack 8.31
        container1_data = {
            "name": f"Bottom of Rack 8.31",
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id
        }
        success, container1 = authenticated_client.post("/api/v1/storage-containers/", container1_data, expected_status=201)
        assert success, f"Failed to create container 1: {container1}"
        
        # Create storage container for rack 8.30
        container2_data = {
            "name": f"Bottom of Rack 8.30 (front side next to Ixia)",
            "container_type": "box",
            "room_id": room.id,
            "datacenter_id": datacenter.id,
            "location": f"Bottom of rack {rack2.code}"
        }
        success, container2 = authenticated_client.post("/api/v1/storage-containers/", container2_data, expected_status=201)
        assert success, f"Failed to create container 2: {container2}"
        
        # Fetch all containers
        success, containers = authenticated_client.get("/api/v1/storage-containers/")
        assert success, f"Failed to fetch containers: {containers}"
        
        # Simulate the frontend filtering logic
        def extract_rack_number(code: str) -> str:
            normalized = code.lower()
            if "rack-" in normalized:
                normalized = normalized.split("rack-")[1]
            elif "rack" in normalized:
                normalized = normalized.split("rack")[1].lstrip("-")
            return normalized.replace(".", "-")
        
        def matches_rack(container: dict, rack_number: str) -> bool:
            if container.get("room_id") != room.id:
                return False
            
            location_text = (container.get("location") or "").lower().replace(".", "-")
            name_text = (container.get("name") or "").lower().replace(".", "-")
            
            mentions_rack = "rack" in location_text or "rack" in name_text
            
            if mentions_rack:
                return rack_number in location_text or rack_number in name_text
            return False  # Only show containers that mention a rack
        
        rack1_number = extract_rack_number(rack1.code)
        rack2_number = extract_rack_number(rack2.code)
        
        # Filter containers for rack1
        containers_for_rack1 = [c for c in containers if matches_rack(c, rack1_number)]
        
        # Filter containers for rack2
        containers_for_rack2 = [c for c in containers if matches_rack(c, rack2_number)]
        
        # Rack1 should only show container1
        assert len(containers_for_rack1) == 1, \
            f"Rack1 should show 1 container, got {len(containers_for_rack1)}: {[c['name'] for c in containers_for_rack1]}"
        assert containers_for_rack1[0]["name"] == "Bottom of Rack 8.31", \
            f"Rack1 should show container1, got {containers_for_rack1[0]['name']}"
        
        # Rack2 should only show container2
        assert len(containers_for_rack2) == 1, \
            f"Rack2 should show 1 container, got {len(containers_for_rack2)}: {[c['name'] for c in containers_for_rack2]}"
        assert containers_for_rack2[0]["name"] == "Bottom of Rack 8.30 (front side next to Ixia)", \
            f"Rack2 should show container2, got {containers_for_rack2[0]['name']}"
        
        # Verify containers don't cross over
        container1_names_rack1 = [c["name"] for c in containers_for_rack1]
        assert "Bottom of Rack 8.30" not in container1_names_rack1[0], \
            "Rack1 should not show container2"
        
        container2_names_rack2 = [c["name"] for c in containers_for_rack2]
        assert "Bottom of Rack 8.31" not in container2_names_rack2[0], \
            "Rack2 should not show container1"
        
    finally:
        clear_tenant_id()
        db.close()

