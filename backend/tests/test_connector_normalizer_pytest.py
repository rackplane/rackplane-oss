# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression tests for connector type normalization.

Tests the connector_normalizer utility that maps raw vendor connector
strings to standard enum values.
"""

import pytest
from app.services.connector_normalizer import normalize_connector_type, get_connector_family


@pytest.mark.regression
class TestConnectorNormalization:
    """Tests for connector type string normalization."""

    def test_osfp_flat_variations(self):
        """OSFP Flat variations should normalize to OSFP_FLT."""
        assert normalize_connector_type("OSFP Flat") == "OSFP_FLT"
        assert normalize_connector_type("osfp flat") == "OSFP_FLT"
        assert normalize_connector_type("osfp-flt") == "OSFP_FLT"
        assert normalize_connector_type("OSFP FLT") == "OSFP_FLT"

    def test_osfp_finned_variations(self):
        """OSFP Finned variations should normalize to OSFP_FIN."""
        assert normalize_connector_type("OSFP Finned") == "OSFP_FIN"
        assert normalize_connector_type("osfp finned") == "OSFP_FIN"
        assert normalize_connector_type("osfp-fin") == "OSFP_FIN"
        assert normalize_connector_type("OSFP FIN") == "OSFP_FIN"

    def test_plain_osfp_passthrough(self):
        """Plain OSFP should pass through unchanged for user clarification."""
        assert normalize_connector_type("OSFP") == "OSFP"

    def test_qsfp_dd_variations(self):
        """QSFP-DD variations should normalize to QSFP_DD."""
        assert normalize_connector_type("QSFP-DD") == "QSFP_DD"
        assert normalize_connector_type("qsfp-dd") == "QSFP_DD"
        assert normalize_connector_type("QSFPDD") == "QSFP_DD"
        assert normalize_connector_type("QSFP DD") == "QSFP_DD"

    def test_qsfp112_preserved(self):
        """QSFP112 should be preserved as distinct type (not mapped to QSFP-DD)."""
        assert normalize_connector_type("QSFP112") == "QSFP112"
        assert normalize_connector_type("qsfp112") == "QSFP112"

    def test_qsfp56_preserved(self):
        """QSFP56 should be preserved."""
        assert normalize_connector_type("QSFP56") == "QSFP56"
        assert normalize_connector_type("qsfp56") == "QSFP56"
    
    def test_qsfp28_preserved(self):
        """QSFP28 should be preserved."""
        assert normalize_connector_type("QSFP28") == "QSFP28"
        assert normalize_connector_type("qsfp28") == "QSFP28"
    
    def test_sfp_plus_variations(self):
        """SFP+ variations should normalize."""
        assert normalize_connector_type("SFP+") == "SFP_PLUS"
        assert normalize_connector_type("sfp+") == "SFP_PLUS"
        assert normalize_connector_type("sfp-plus") == "SFP_PLUS"

    def test_unknown_passthrough(self):
        """Unknown connector types should pass through unchanged."""
        assert normalize_connector_type("CUSTOM_TYPE") == "CUSTOM_TYPE"
        assert normalize_connector_type("RJ45") == "RJ45"

    def test_none_handling(self):
        """None input should return None."""
        assert normalize_connector_type(None) is None

    def test_empty_string_handling(self):
        """Empty string should return empty string."""
        assert normalize_connector_type("") == ""


@pytest.mark.regression
class TestConnectorFamily:
    """Tests for connector family detection."""

    def test_osfp_family(self):
        """OSFP variants should be in OSFP family."""
        assert get_connector_family("OSFP") == "OSFP"
        assert get_connector_family("OSFP_FIN") == "OSFP"
        assert get_connector_family("OSFP_FLT") == "OSFP"

    def test_qsfp_family(self):
        """QSFP variants should be in QSFP family."""
        assert get_connector_family("QSFP") == "QSFP"
        assert get_connector_family("QSFP28") == "QSFP"
        assert get_connector_family("QSFP56") == "QSFP"
        assert get_connector_family("QSFP112") == "QSFP"
        assert get_connector_family("QSFP_DD") == "QSFP"

    def test_sfp_family(self):
        """SFP variants should be in SFP family."""
        assert get_connector_family("SFP") == "SFP"
        assert get_connector_family("SFP28") == "SFP"
        assert get_connector_family("SFP_PLUS") == "SFP"

    def test_fiber_connectors(self):
        """Fiber connectors should be in FIBER family."""
        assert get_connector_family("LC") == "FIBER"
        assert get_connector_family("SC") == "FIBER"
        assert get_connector_family("MPO") == "FIBER"
        assert get_connector_family("MTP") == "FIBER"
