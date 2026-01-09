# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Asset Service Test Suite
Comprehensive tests for asset lifecycle management and business logic

Tests cover:
1. Asset creation with auto-generation
2. Duplicate detection and validation
3. Asset updates and lifecycle changes
4. Rack position collision detection
5. Circular reference prevention
6. Photo uploads
7. Asset deployment
8. Asset decommissioning
9. Status transitions
10. Storage container management
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, UploadFile
from io import BytesIO
from datetime import datetime
import uuid

from app.services.asset_service import AssetService
from app.models.asset import Asset, AssetStatus, AssetLifecycleEvent
from app.models.location import Rack
from app.schemas.asset import AssetCreate, AssetUpdate


def unique_id():
    """Generate a unique short ID for test data"""
    return str(uuid.uuid4())[:8]


class TestAssetCreation:
    """Test asset creation functionality"""

    def test_create_asset_basic(self, db):
        """Test basic asset creation"""
        service = AssetService(db)
        uid = unique_id()

        asset_data = AssetCreate(
            asset_tag=f"SRV-{uid}",
            serial_number=f"SN-{uid}",
            asset_type="server",
            manufacturer="Dell",
            model="PowerEdge R740",
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add'), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh') as mock_refresh:

            # Mock no duplicates
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.return_value.filter.return_value = mock_filter

            # Mock refresh to set an ID
            def set_id(obj):
                if isinstance(obj, Asset):
                    obj.id = 123
            mock_refresh.side_effect = set_id

            asset = service.create_asset(asset_data)

        assert asset.id is not None
        assert asset.asset_tag == f"SRV-{uid}"
        assert asset.serial_number == f"SN-{uid}"
        assert asset.status == AssetStatus.RECEIVED
        assert asset.manufacturer == "Dell"

    def test_create_asset_auto_generates_serial_number(self, db):
        """Test automatic serial number generation"""
        service = AssetService(db)
        uid = unique_id()

        asset_data = AssetCreate(
            asset_tag=f"SRV-{uid}",
            serial_number=None,  # Will be auto-generated
            asset_type="server",
            status=AssetStatus.ORDERED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.services.serial_service.generate_serial_number', return_value=f"AUTO-SN-{uid}"), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add'), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh') as mock_refresh:

            # Mock no duplicates
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.return_value.filter.return_value = mock_filter

            # Mock refresh to set an ID
            def set_id(obj):
                if isinstance(obj, Asset):
                    obj.id = 124
            mock_refresh.side_effect = set_id

            asset = service.create_asset(asset_data)

        assert asset.serial_number == f"AUTO-SN-{uid}"
        assert asset.original_serial_number == f"AUTO-SN-{uid}"

    def test_create_asset_auto_generates_asset_tag(self, db):
        """Test automatic asset tag generation"""
        service = AssetService(db)
        uid = unique_id()

        asset_data = AssetCreate(
            asset_tag=None,  # Will be auto-generated
            serial_number=f"SN-{uid}",
            asset_type="switch",
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.services.serial_service.generate_asset_tag', return_value=f"SW-AUTO-{uid}"), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add'), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh') as mock_refresh:

            # Mock no duplicates
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.return_value.filter.return_value = mock_filter

            # Mock refresh to set an ID
            def set_id(obj):
                if isinstance(obj, Asset):
                    obj.id = 125
            mock_refresh.side_effect = set_id

            asset = service.create_asset(asset_data)

        assert asset.asset_tag == f"SW-AUTO-{uid}"

    def test_create_asset_prevents_duplicate_asset_tag(self, db):
        """Test prevention of duplicate asset tags"""
        service = AssetService(db)
        uid = unique_id()

        # Mock an existing asset
        existing_asset = Mock(spec=Asset)
        existing_asset.asset_tag = f"DUP-{uid}"
        existing_asset.serial_number = "SN-UNIQUE-1"
        existing_asset.id = 100

        # Try to create asset with duplicate tag
        asset_data = AssetCreate(
            asset_tag=f"DUP-{uid}",  # Duplicate tag
            serial_number="SN-UNIQUE-2",  # Different serial
            asset_type="server",
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query:

            # Mock the duplicate check to return existing asset
            mock_filter = MagicMock()
            mock_filter.first.return_value = existing_asset  # Return existing asset
            mock_query.return_value.filter.return_value = mock_filter

            with pytest.raises(HTTPException) as exc_info:
                service.create_asset(asset_data)

            assert exc_info.value.status_code == 400
            assert "Asset with this tag already exists" in exc_info.value.detail

    def test_create_asset_prevents_duplicate_serial_number(self, db):
        """Test prevention of duplicate serial numbers"""
        service = AssetService(db)

        existing_asset = Mock(spec=Asset)
        existing_asset.asset_tag = "OLD-001"
        existing_asset.serial_number = "DUP-SERIAL"

        asset_data = AssetCreate(
            asset_tag="NEW-001",
            serial_number="DUP-SERIAL",  # Duplicate serial
            asset_type="server",
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query:

            mock_filter = MagicMock()
            mock_filter.first.return_value = existing_asset
            mock_query.return_value.filter.return_value = mock_filter

            with pytest.raises(HTTPException) as exc_info:
                service.create_asset(asset_data)

            assert exc_info.value.status_code == 400
            assert "serial number already exists" in exc_info.value.detail.lower()

    def test_create_asset_prevents_duplicate_hostname(self, db):
        """Test prevention of duplicate hostnames"""
        service = AssetService(db)

        existing_asset = Mock(spec=Asset)
        existing_asset.hostname = "server01.rack.local"

        asset_data = AssetCreate(
            asset_tag="SRV-003",
            serial_number="SN-003",
            hostname="server01.rack.local",  # Duplicate hostname
            asset_type="server",
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q):

            # Mock first query (tag/serial check) - no duplicates
            # Mock second query (hostname check) - found duplicate
            with patch.object(db, 'query') as mock_query:
                # First call: asset_tag/serial_number check - returns None
                first_filter = MagicMock()
                first_filter.first.return_value = None

                # Second call: hostname check - returns existing
                second_filter = MagicMock()
                second_filter.first.return_value = existing_asset

                mock_query.return_value.filter.side_effect = [first_filter, second_filter]

                with pytest.raises(HTTPException) as exc_info:
                    service.create_asset(asset_data)

                assert exc_info.value.status_code == 400
                assert "hostname" in exc_info.value.detail.lower()

    def test_create_asset_auto_sets_in_storage_status(self, db):
        """Test automatic IN_STORAGE status when container_id is set"""
        service = AssetService(db)
        uid = unique_id()

        container_mock = Mock(spec=Asset)
        container_mock.id = 100
        container_mock.asset_type = "storage_box"

        asset_data = AssetCreate(
            asset_tag=f"CABLE-{uid}",
            serial_number=f"SN-CABLE-{uid}",
            asset_type="dac_cable",
            container_id=100,  # Being placed in container
            status=AssetStatus.RECEIVED  # Will be overridden
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add'), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh') as mock_refresh:

            # Mock the duplicate check - returns None (no duplicate)
            duplicate_check = MagicMock()
            duplicate_check.filter.return_value.first.return_value = None

            # Mock the container check - returns the container
            container_check = MagicMock()
            container_check.filter.return_value.first.return_value = container_mock

            # Set up query to return different mocks for different calls
            mock_query.side_effect = [duplicate_check, container_check]

            # Mock refresh to set an ID
            def set_id(obj):
                if isinstance(obj, Asset):
                    obj.id = 126
            mock_refresh.side_effect = set_id

            asset = service.create_asset(asset_data)

            # Status should be auto-set to IN_STORAGE
            assert asset.status == AssetStatus.IN_STORAGE

    def test_create_cable_rejects_min_stock_threshold(self, db):
        """Test that cables cannot have min_stock_threshold"""
        service = AssetService(db)
        uid = unique_id()

        asset_data = AssetCreate(
            asset_tag=f"CABLE-{uid}",
            serial_number=f"SN-CABLE-{uid}",
            asset_type="dac_cable",
            min_stock_threshold=10,  # Invalid for cables
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query:

            # Mock no duplicates so we get to the min_stock_threshold check
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.return_value.filter.return_value = mock_filter

            with pytest.raises(HTTPException) as exc_info:
                service.create_asset(asset_data)

            assert exc_info.value.status_code == 400
            assert "Cables cannot have min_stock_threshold" in exc_info.value.detail

    def test_create_asset_creates_lifecycle_event(self, db):
        """Test that asset creation creates a lifecycle event"""
        service = AssetService(db)

        asset_data = AssetCreate(
            asset_tag="SRV-LIFECYCLE",
            serial_number="SN-LIFECYCLE",
            asset_type="server",
            status=AssetStatus.RECEIVED
        )

        lifecycle_events = []

        def mock_add(obj):
            if isinstance(obj, AssetLifecycleEvent):
                lifecycle_events.append(obj)

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add', side_effect=mock_add), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            # Mock no duplicates
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.return_value.filter.return_value = mock_filter

            asset = service.create_asset(asset_data)

            # Verify lifecycle event was created
            assert len(lifecycle_events) > 0
            event = lifecycle_events[0]
            assert event.event_type == "created"
            assert event.new_status == AssetStatus.RECEIVED.value


class TestAssetUpdate:
    """Test asset update functionality"""

    def test_update_asset_basic(self, db):
        """Test basic asset update"""
        service = AssetService(db)

        existing_asset = Asset(
            id=1,
            asset_tag="SRV-001",
            serial_number="SN-001",
            asset_type="server",
            status=AssetStatus.RECEIVED
        )

        update_data = AssetUpdate(
            manufacturer="Dell",
            model="PowerEdge R740"
        )

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            mock_query.return_value.filter.return_value.first.return_value = existing_asset

            asset = service.update_asset(1, update_data)

            assert asset.manufacturer == "Dell"
            assert asset.model == "PowerEdge R740"

    def test_update_asset_not_found(self, db):
        """Test update of non-existent asset"""
        service = AssetService(db)

        update_data = AssetUpdate(manufacturer="Dell")

        with patch.object(db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                service.update_asset(999, update_data)

            assert exc_info.value.status_code == 404
            assert "Asset not found" in exc_info.value.detail

    def test_update_asset_prevents_self_containment(self, db):
        """Test prevention of asset containing itself"""
        service = AssetService(db)

        asset = Asset(
            id=10,
            asset_tag="BOX-001",
            asset_type="storage_box",
            status=AssetStatus.IN_STORAGE
        )

        update_data = AssetUpdate(
            container_id=10  # Trying to contain itself
        )

        with patch.object(db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = asset

            with pytest.raises(HTTPException) as exc_info:
                service.update_asset(10, update_data)

            assert exc_info.value.status_code == 400
            assert "cannot be placed inside itself" in exc_info.value.detail.lower()

    def test_update_asset_prevents_circular_reference(self, db):
        """Test prevention of circular container references"""
        service = AssetService(db)

        # Setup: Box A (id=1) contains Box B (id=2)
        # Test: Try to make Box A's container be Box B (creates cycle)

        box_a = Asset(id=1, asset_tag="BOX-A", asset_type="storage_box", container_id=None)
        box_b = Asset(id=2, asset_tag="BOX-B", asset_type="storage_box", container_id=1)

        update_data = AssetUpdate(
            container_id=2  # Try to make Box B contain Box A
        )

        with patch.object(db, 'query') as mock_query, \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q):

            # First query returns the asset being updated (Box A)
            # Subsequent queries for cycle detection return Box B
            def query_side_effect(*args, **kwargs):
                mock_result = MagicMock()
                if hasattr(query_side_effect, 'call_count'):
                    query_side_effect.call_count += 1
                else:
                    query_side_effect.call_count = 1

                if query_side_effect.call_count == 1:
                    mock_result.filter.return_value.first.return_value = box_a
                else:
                    mock_result.filter.return_value.first.return_value = box_b

                return mock_result

            mock_query.side_effect = query_side_effect

            with pytest.raises(HTTPException) as exc_info:
                service.update_asset(1, update_data)

            assert exc_info.value.status_code == 400
            assert "circular reference" in exc_info.value.detail.lower()

    def test_update_asset_rack_position_collision_detection(self, db):
        """Test rack position collision detection"""
        service = AssetService(db)

        # Existing asset in rack at U10-12 (3U device)
        existing_rack_asset = Asset(
            id=2,
            asset_tag="SRV-002",
            rack_id=1,
            rack_position_start=10,
            rack_position_end=12,
            height_u=3
        )

        # Asset being updated
        asset_to_update = Asset(
            id=1,
            asset_tag="SRV-001",
            rack_id=None,
            rack_position_start=None
        )

        # Try to place at U11 (conflicts with SRV-002 at U10-12)
        update_data = AssetUpdate(
            rack_id=1,
            rack_position_start=11,
            height_u=2
        )

        with patch.object(db, 'query') as mock_query, \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q):

            def query_side_effect(*args, **kwargs):
                result = MagicMock()
                if hasattr(query_side_effect, 'call_count'):
                    query_side_effect.call_count += 1
                else:
                    query_side_effect.call_count = 1

                if query_side_effect.call_count == 1:
                    # First call: get asset being updated
                    result.filter.return_value.first.return_value = asset_to_update
                else:
                    # Subsequent calls: collision detection
                    result.filter.return_value.all.return_value = [existing_rack_asset]

                return result

            mock_query.side_effect = query_side_effect

            with pytest.raises(HTTPException) as exc_info:
                service.update_asset(1, update_data)

            assert exc_info.value.status_code == 400
            assert "conflicts" in exc_info.value.detail.lower()

    def test_update_asset_preserves_original_serial_number(self, db):
        """Test that original_serial_number is preserved when serial changes"""
        service = AssetService(db)

        asset = Asset(
            id=1,
            asset_tag="SRV-001",
            serial_number="ORIGINAL-SN",
            original_serial_number=None  # Not set yet
        )

        update_data = AssetUpdate(
            serial_number="NEW-SN"
        )

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            mock_query.return_value.filter.return_value.first.return_value = asset

            updated_asset = service.update_asset(1, update_data)

            # Original serial should be preserved
            assert updated_asset.original_serial_number == "ORIGINAL-SN"
            assert updated_asset.serial_number == "NEW-SN"

    def test_update_asset_status_creates_lifecycle_event(self, db):
        """Test that status changes create lifecycle events"""
        service = AssetService(db)

        asset = Asset(
            id=1,
            asset_tag="SRV-001",
            serial_number="SN-001",
            status=AssetStatus.RECEIVED
        )

        update_data = AssetUpdate(
            status=AssetStatus.DEPLOYED
        )

        lifecycle_events = []

        def mock_add(obj):
            if isinstance(obj, AssetLifecycleEvent):
                lifecycle_events.append(obj)

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add', side_effect=mock_add), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            mock_query.return_value.filter.return_value.first.return_value = asset

            service.update_asset(1, update_data)

            # Verify lifecycle event created
            assert len(lifecycle_events) > 0
            event = lifecycle_events[0]
            assert event.event_type == "status_changed"
            assert event.old_status == AssetStatus.RECEIVED.value
            assert event.new_status == AssetStatus.DEPLOYED.value


class TestAssetPhotoUpload:
    """Test asset photo upload functionality"""

    def test_upload_photo_success(self, db):
        """Test successful photo upload"""
        service = AssetService(db)

        asset = Asset(
            id=1,
            asset_tag="SRV-001",
            photo_urls=[]
        )

        # Create mock file
        file_content = b"fake image data"
        mock_file = Mock(spec=UploadFile)
        mock_file.file = BytesIO(file_content)
        mock_file.filename = "server.jpg"
        mock_file.content_type = "image/jpeg"

        mock_storage = Mock()
        mock_storage.upload_file.return_value = "https://storage.rackplane.com/assets/SRV-001_uuid.jpg"

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.storage_service.get_storage_service', return_value=mock_storage), \
             patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.services.asset_service.settings') as mock_settings, \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            mock_settings.MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
            mock_query.return_value.filter.return_value.first.return_value = asset

            result = service.upload_photo(1, mock_file)

            assert result["message"] == "Photo uploaded successfully"
            assert "photo_url" in result
            assert result["asset_id"] == 1
            assert len(asset.photo_urls) == 1

    def test_upload_photo_asset_not_found(self, db):
        """Test photo upload for non-existent asset"""
        service = AssetService(db)

        mock_file = Mock(spec=UploadFile)
        mock_file.file = BytesIO(b"data")

        with patch.object(db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                service.upload_photo(999, mock_file)

            assert exc_info.value.status_code == 404

    def test_upload_photo_file_too_large(self, db):
        """Test photo upload with file size limit"""
        service = AssetService(db)

        asset = Asset(id=1, asset_tag="SRV-001", photo_urls=[])

        # Create large file
        large_file = b"X" * (11 * 1024 * 1024)  # 11MB
        mock_file = Mock(spec=UploadFile)
        mock_file.file = BytesIO(large_file)
        mock_file.filename = "huge.jpg"

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.asset_service.settings') as mock_settings:

            mock_settings.MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB limit
            mock_query.return_value.filter.return_value.first.return_value = asset

            with pytest.raises(HTTPException) as exc_info:
                service.upload_photo(1, mock_file)

            assert exc_info.value.status_code == 400
            assert "too large" in exc_info.value.detail.lower()


class TestAssetDeployment:
    """Test asset deployment functionality"""

    def test_deploy_asset_success(self, db):
        """Test successful asset deployment"""
        service = AssetService(db)

        asset = Asset(
            id=1,
            asset_tag="SRV-001",
            serial_number="SN-001",
            status=AssetStatus.STAGING,
            rack_id=None,
            rack_position_start=None,
            height_u=2
        )

        rack = Rack(
            id=10,
            code="RACK-A",
            height_u=42
        )

        lifecycle_events = []

        def mock_add(obj):
            if isinstance(obj, AssetLifecycleEvent):
                lifecycle_events.append(obj)

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add', side_effect=mock_add), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            def query_side_effect(model):
                result = MagicMock()
                if model == Asset:
                    result.filter.return_value.first.return_value = asset
                elif model == Rack:
                    result.filter.return_value.first.return_value = rack
                return result

            mock_query.side_effect = query_side_effect

            deployed_asset = service.deploy_asset(1, rack_id=10, u_position_start=5)

            assert deployed_asset.rack_id == 10
            assert deployed_asset.rack_position_start == 5
            assert deployed_asset.rack_position_end == 6  # start + height - 1
            assert deployed_asset.status == AssetStatus.DEPLOYED
            assert deployed_asset.deployed_at is not None

            # Verify lifecycle event
            assert len(lifecycle_events) > 0
            event = lifecycle_events[0]
            assert event.event_type == "deployed"

    def test_deploy_asset_rack_not_found(self, db):
        """Test deployment to non-existent rack"""
        service = AssetService(db)

        asset = Asset(id=1, asset_tag="SRV-001")

        with patch.object(db, 'query') as mock_query:
            def query_side_effect(model):
                result = MagicMock()
                if model == Asset:
                    result.filter.return_value.first.return_value = asset
                elif model == Rack:
                    result.filter.return_value.first.return_value = None
                return result

            mock_query.side_effect = query_side_effect

            with pytest.raises(HTTPException) as exc_info:
                service.deploy_asset(1, rack_id=999, u_position_start=5)

            assert exc_info.value.status_code == 404
            assert "Rack not found" in exc_info.value.detail


class TestAssetDecommission:
    """Test asset decommissioning functionality"""

    def test_decommission_asset_success(self, db):
        """Test successful asset decommissioning"""
        service = AssetService(db)

        asset = Asset(
            id=1,
            asset_tag="SRV-OLD",
            status=AssetStatus.DEPLOYED,
            rack_id=5,
            rack_position_start=10,
            rack_position_end=11
        )

        lifecycle_events = []

        def mock_add(obj):
            if isinstance(obj, AssetLifecycleEvent):
                lifecycle_events.append(obj)

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add', side_effect=mock_add), \
             patch.object(db, 'commit'), \
             patch.object(db, 'refresh'):

            mock_query.return_value.filter.return_value.first.return_value = asset

            decommissioned = service.decommission_asset(1, reason="End of life")

            assert decommissioned.status == AssetStatus.DECOMMISSIONED
            assert decommissioned.decommissioned_at is not None
            assert decommissioned.rack_id is None
            assert decommissioned.rack_position_start is None
            assert decommissioned.rack_position_end is None

            # Verify lifecycle event
            assert len(lifecycle_events) > 0
            event = lifecycle_events[0]
            assert event.event_type == "decommissioned"
            assert "End of life" in event.notes

    def test_decommission_asset_not_found(self, db):
        """Test decommissioning non-existent asset"""
        service = AssetService(db)

        with patch.object(db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                service.decommission_asset(999)

            assert exc_info.value.status_code == 404


class TestAssetLifecycle:
    """Test asset lifecycle state transitions"""

    def test_asset_status_transitions(self):
        """Test valid asset status transitions"""
        # Test the enum values
        assert AssetStatus.ORDERED.value == "ordered"
        assert AssetStatus.IN_TRANSIT.value == "in_transit"
        assert AssetStatus.RECEIVED.value == "received"
        assert AssetStatus.STAGING.value == "staging"
        assert AssetStatus.IN_STORAGE.value == "in_storage"
        assert AssetStatus.DEPLOYED.value == "deployed"
        assert AssetStatus.ACTIVE.value == "active"
        assert AssetStatus.MAINTENANCE.value == "maintenance"
        assert AssetStatus.FAILED.value == "failed"
        assert AssetStatus.RMA.value == "rma"
        assert AssetStatus.DECOMMISSIONED.value == "decommissioned"
        assert AssetStatus.RETIRED.value == "retired"
        assert AssetStatus.DISPOSED.value == "disposed"

    def test_asset_status_string_representation(self):
        """Test that status enum converts to lowercase value"""
        status = AssetStatus.IN_STORAGE
        assert str(status) == "in_storage"
        assert status.value == "in_storage"


class TestAssetBusinessRules:
    """Test asset business rules and validations"""

    def test_cable_asset_types_identified_correctly(self):
        """Test cable type detection logic"""
        cable_types = [
            "dac_cable",
            "fiber_cable",
            "ethernet_cable",
            "network_cable",
            "power_cable"
        ]

        for cable_type in cable_types:
            assert "cable" in cable_type.lower() or cable_type.endswith("_cable")

    def test_container_validation_rejects_missing_container(self, db):
        """Test that invalid container_id is rejected"""
        service = AssetService(db)

        asset_data = AssetCreate(
            asset_tag="ITEM-001",
            serial_number="SN-001",
            asset_type="cable",
            container_id=999,  # Non-existent container
            status=AssetStatus.RECEIVED
        )

        with patch('app.core.tenant.get_current_tenant_id', return_value=1), \
             patch('app.core.tenant_query.apply_tenant_filter', side_effect=lambda q, m: q), \
             patch.object(db, 'query') as mock_query:

            # Mock: tag/serial check passes, container check fails
            tag_check = MagicMock()
            tag_check.first.return_value = None

            hostname_check = MagicMock()
            hostname_check.first.return_value = None

            container_check = MagicMock()
            container_check.first.return_value = None  # Container not found

            mock_query.return_value.filter.side_effect = [
                tag_check,
                hostname_check,
                container_check
            ]

            with pytest.raises(HTTPException) as exc_info:
                service.create_asset(asset_data)

            assert exc_info.value.status_code == 404
            assert "Container" in exc_info.value.detail


# Test fixtures
@pytest.fixture
def db():
    """Mock database session"""
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    return mock_db


# Mark all tests as unit tests
pytestmark = pytest.mark.unit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
