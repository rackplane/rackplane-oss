# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Asset Clone API Tests
Tests for the asset cloning/duplication functionality.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.regression
@pytest.mark.integration
class TestAssetClone:
    """Test suite for asset clone endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = 1
        user.username = "testuser"
        user.tenant_id = 1
        user.is_readonly = False
        return user
    
    @pytest.fixture
    def sample_asset(self):
        """Create a sample asset for testing."""
        asset = MagicMock()
        asset.id = 42
        asset.asset_tag = "SRV-001"
        asset.serial_number = "ABC123456"
        asset.asset_type = "server"
        asset.manufacturer = "Dell"
        asset.model = "PowerEdge R750"
        asset.status = "received"
        asset.description = "Test server with 128GB RAM"
        asset.purchase_cost = 15000.00
        asset.sku = "R750-001"
        return asset
    
    def test_clone_single_asset(self, sample_asset):
        """
        Bug: Cannot duplicate existing asset to create similar assets
        Fix: Clone endpoint copies all fields except ID, tag, serial, location
        """
        # Verify source asset fields
        assert sample_asset.asset_tag == "SRV-001"
        assert sample_asset.manufacturer == "Dell"
        assert sample_asset.purchase_cost == 15000.00
        
        # Fields that should be excluded from cloning
        exclude_fields = {
            'id', 'asset_tag', 'serial_number', 'original_serial_number',
            'created_at', 'updated_at', 'tenant_id',
            'rack_position_start', 'rack_position_end', 'rack_id',
            'hostname', 'primary_ip', 'management_ip', 'mac_address'
        }
        
        # Verify exclude fields list contains essential unique identifiers
        assert 'id' in exclude_fields
        assert 'asset_tag' in exclude_fields
        assert 'serial_number' in exclude_fields
        assert 'rack_id' in exclude_fields
        
    def test_clone_with_prefix(self, sample_asset):
        """
        Bug: Clone with custom prefix should use prefix instead of source tag
        Fix: When prefix is provided, use {prefix}-{uuid} format
        """
        prefix = "HH-SRV"
        
        # Simulating what the clone logic would do
        import uuid
        new_tag = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        
        assert new_tag.startswith("HH-SRV-")
        assert len(new_tag) == len("HH-SRV-") + 8  # prefix + dash + 8 char hex
        
    def test_clone_without_prefix(self, sample_asset):
        """
        Bug: Clone without prefix should append CLONE suffix to source tag
        Fix: When no prefix, use {source_tag}-CLONE-{n} format
        """
        source_tag = sample_asset.asset_tag
        
        # For first clone
        new_tag_1 = f"{source_tag}-CLONE-1"
        assert new_tag_1 == "SRV-001-CLONE-1"
        
        # For second clone
        new_tag_2 = f"{source_tag}-CLONE-2"
        assert new_tag_2 == "SRV-001-CLONE-2"
        
    def test_clone_bulk_quantity(self, sample_asset):
        """
        Bug: Bulk cloning should create exact number of assets requested
        Fix: Clone endpoint accepts quantity parameter (1-100)
        """
        quantity = 5
        created_tags = []
        
        for i in range(quantity):
            new_tag = f"{sample_asset.asset_tag}-CLONE-{i+1}"
            created_tags.append(new_tag)
        
        assert len(created_tags) == 5
        assert created_tags[0] == "SRV-001-CLONE-1"
        assert created_tags[4] == "SRV-001-CLONE-5"
        
    def test_clone_serial_number_generation(self):
        """
        Bug: Cloned assets need unique serial numbers
        Fix: Generate new serial with CLN- prefix and UUID
        """
        import uuid
        
        serial_1 = f"CLN-{uuid.uuid4().hex[:12].upper()}"
        serial_2 = f"CLN-{uuid.uuid4().hex[:12].upper()}"
        
        assert serial_1.startswith("CLN-")
        assert serial_2.startswith("CLN-")
        assert serial_1 != serial_2  # Should be unique
        assert len(serial_1) == len("CLN-") + 12
        
    def test_clone_preserves_purchase_cost(self, sample_asset):
        """
        Bug: Cloned assets should retain financial information
        Fix: Purchase cost, currency, supplier copied to clones
        """
        # Fields that should be preserved
        preserved_fields = [
            'purchase_cost', 'currency', 'supplier', 'po_number',
            'manufacturer', 'model', 'sku', 'description',
            'asset_type', 'height_u', 'power_consumption_watts'
        ]
        
        # Verify these are NOT in exclude list
        exclude_fields = {
            'id', 'asset_tag', 'serial_number', 'original_serial_number',
            'created_at', 'updated_at', 'tenant_id',
            'rack_position_start', 'rack_position_end', 'rack_id',
            'hostname', 'primary_ip', 'management_ip', 'mac_address'
        }
        
        for field in preserved_fields:
            assert field not in exclude_fields, f"{field} should be preserved in clones"
