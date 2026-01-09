# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression tests for cable end type matching and transceiver tracking.

Tests added for:
- OSFP_FIN and OSFP_FLT connector types
- Dual-end cable connector type support
- Transceiver installation in ports
"""

import pytest
from app.models.network_cable import ConnectorType, CableType
from app.models.network import PortType
from app.services.cable_validation_service import CableValidationService, CompatibilityLevel


@pytest.mark.regression
class TestOSFPConnectorTypes:
    """Test OSFP Finned and Flat connector type support."""

    def test_connector_type_enum_has_osfp_fin(self):
        """
        Bug: ConnectorType enum was missing OSFP_FIN
        Fix: Added OSFP_FIN = "osfp-fin" to ConnectorType enum
        """
        assert hasattr(ConnectorType, 'OSFP_FIN')
        assert ConnectorType.OSFP_FIN.value == "osfp-fin"

    def test_connector_type_enum_has_osfp_flt(self):
        """
        Bug: ConnectorType enum was missing OSFP_FLT
        Fix: Added OSFP_FLT = "osfp-flt" to ConnectorType enum
        """
        assert hasattr(ConnectorType, 'OSFP_FLT')
        assert ConnectorType.OSFP_FLT.value == "osfp-flt"

    def test_connector_type_enum_has_sfp28(self):
        """
        Bug: ConnectorType enum was missing SFP28 (25G)
        Fix: Added SFP28 = "sfp28" to ConnectorType enum
        """
        assert hasattr(ConnectorType, 'SFP28')
        assert ConnectorType.SFP28.value == "sfp28"


@pytest.mark.regression
class TestCableValidationOSFP:
    """Test cable-to-port compatibility validation for OSFP variants."""

    def test_osfp_fin_to_osfp_fin_port_is_perfect(self):
        """OSFP-FIN cable to OSFP_FIN port should be a perfect match."""
        result = CableValidationService.validate_compatibility("osfp-fin", "osfp_fin")
        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_osfp_flt_to_osfp_flt_port_is_perfect(self):
        """OSFP-FLT cable to OSFP_FLT port should be a perfect match."""
        result = CableValidationService.validate_compatibility("osfp-flt", "osfp_flt")
        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_osfp_fin_to_osfp_flt_port_shows_warning(self):
        """OSFP-FIN cable to OSFP_FLT port should show compatibility warning."""
        result = CableValidationService.validate_compatibility("osfp-fin", "osfp_flt")
        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert "form factor" in result["message"].lower()

    def test_osfp_flt_to_osfp_fin_port_shows_warning(self):
        """OSFP-FLT cable to OSFP_FIN port should show compatibility warning."""
        result = CableValidationService.validate_compatibility("osfp-flt", "osfp_fin")
        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value

    def test_osfp_legacy_to_osfp_fin_is_compatible(self):
        """Legacy OSFP cable to OSFP_FIN port should be compatible."""
        result = CableValidationService.validate_compatibility("osfp", "osfp_fin")
        assert result["compatible"] is True
        # Should be compatible (not perfect) since form factor may differ
        assert result["level"] in [CompatibilityLevel.COMPATIBLE.value, CompatibilityLevel.PERFECT.value]

    def test_osfp_legacy_to_osfp_flt_is_compatible(self):
        """Legacy OSFP cable to OSFP_FLT port should be compatible."""
        result = CableValidationService.validate_compatibility("osfp", "osfp_flt")
        assert result["compatible"] is True


@pytest.mark.regression
class TestCableEndTypes:
    """Test that cables can have different connector types on each end."""

    def test_network_cable_model_has_end_a_type(self):
        """
        Bug: NetworkCable only had one connector_type field
        Fix: Added connector_type_end_a for asymmetric cables
        """
        from app.models.network_cable import NetworkCable
        from sqlalchemy import inspect
        
        # Check the model has the column
        mapper = inspect(NetworkCable)
        column_names = [c.key for c in mapper.columns]
        assert 'connector_type_end_a' in column_names

    def test_network_cable_model_has_end_b_type(self):
        """
        Bug: NetworkCable only had one connector_type field
        Fix: Added connector_type_end_b for asymmetric cables
        """
        from app.models.network_cable import NetworkCable
        from sqlalchemy import inspect
        
        mapper = inspect(NetworkCable)
        column_names = [c.key for c in mapper.columns]
        assert 'connector_type_end_b' in column_names

    def test_validation_uses_end_specific_type_when_provided(self):
        """Validation should use end-specific connector type when cable and end are provided."""
        # Create a mock cable object with end-specific types
        class MockCable:
            connector_type = ConnectorType.OSFP
            connector_type_end_a = ConnectorType.OSFP_FIN
            connector_type_end_b = ConnectorType.OSFP_FLT
        
        cable = MockCable()
        
        # End A should use OSFP-FIN
        result_a = CableValidationService.validate_compatibility(
            cable_connector_type="",  # Will be overridden by cable
            port_type="osfp_fin",
            cable_end="A",
            cable=cable
        )
        assert result_a["compatible"] is True
        assert result_a["level"] == CompatibilityLevel.PERFECT.value
        
        # End B should use OSFP-FLT
        result_b = CableValidationService.validate_compatibility(
            cable_connector_type="",
            port_type="osfp_flt",
            cable_end="B",
            cable=cable
        )
        assert result_b["compatible"] is True
        assert result_b["level"] == CompatibilityLevel.PERFECT.value


@pytest.mark.regression
class TestTransceiverTracking:
    """Test transceiver installation tracking in ports."""

    def test_network_port_model_has_installed_transceiver_id(self):
        """
        Bug: Fiber connections need 3-part tracking (port+transceiver+cable)
        Fix: Added installed_transceiver_id to NetworkPort model
        """
        from app.models.network import NetworkPort
        from sqlalchemy import inspect
        
        mapper = inspect(NetworkPort)
        column_names = [c.key for c in mapper.columns]
        assert 'installed_transceiver_id' in column_names

    def test_network_port_schema_includes_installed_transceiver_id(self):
        """NetworkPort response schema should include installed_transceiver_id."""
        from app.schemas.network_port import NetworkPortResponse
        
        # Check the schema has the field
        assert 'installed_transceiver_id' in NetworkPortResponse.model_fields

    def test_network_port_update_schema_allows_transceiver_assignment(self):
        """NetworkPort update schema should allow setting installed_transceiver_id."""
        from app.schemas.network_port import NetworkPortUpdate
        
        assert 'installed_transceiver_id' in NetworkPortUpdate.model_fields


@pytest.mark.regression
class TestPortTypeCompatibility:
    """Test that PortType enum has the OSFP variants."""

    def test_port_type_has_osfp_fin(self):
        """PortType enum should include OSFP_FIN for switch ports."""
        assert hasattr(PortType, 'OSFP_FIN')
        assert PortType.OSFP_FIN.value == "OSFP_FIN"

    def test_port_type_has_osfp_flt(self):
        """PortType enum should include OSFP_FLT for NIC ports."""
        assert hasattr(PortType, 'OSFP_FLT')
        assert PortType.OSFP_FLT.value == "OSFP_FLT"
