# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
"""Tests for Cable Validation Service"""

import pytest
from app.services.cable_validation_service import CableValidationService, CompatibilityLevel


@pytest.mark.regression
class TestCableValidationService:
    """Tests for cable/port compatibility validation"""

    def test_perfect_match_rj45(self):
        """TC-VALIDATION-001: RJ45 cable to RJ45 port = perfect"""
        result = CableValidationService.validate_compatibility("rj45", "rj45")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value
        assert result["allow_connection"] is True

    def test_perfect_match_sfp_plus(self):
        """TC-VALIDATION-002: SFP+ cable to SFP+ port = perfect"""
        result = CableValidationService.validate_compatibility("sfp_plus", "sfp_plus")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_sfp_in_sfp_plus_compatible(self):
        """TC-VALIDATION-003: SFP cable in SFP+ port = compatible (1G in 10G)"""
        result = CableValidationService.validate_compatibility("sfp", "sfp_plus")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert "1G" in result["message"]

    def test_sfp_plus_in_sfp_downgrade(self):
        """TC-VALIDATION-004: SFP+ cable in SFP port = downgrade"""
        result = CableValidationService.validate_compatibility("sfp_plus", "sfp")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.DOWNGRADE.value
        assert "1G" in result["message"]

    def test_qsfp_dd_in_sfp_plus_incompatible(self):
        """TC-VALIDATION-005: QSFP-DD cable in SFP+ port = incompatible"""
        result = CableValidationService.validate_compatibility("qsfp_dd", "sfp_plus")

        assert result["compatible"] is False
        assert result["level"] == CompatibilityLevel.INCOMPATIBLE.value
        assert result["allow_connection"] is True  # Still allow with warning

    def test_unknown_cable_type(self):
        """TC-VALIDATION-006: Unknown cable type returns unknown level"""
        result = CableValidationService.validate_compatibility("future_connector_9000", "sfp")

        assert result["compatible"] is True  # Allow unknown
        assert result["level"] == CompatibilityLevel.UNKNOWN.value
        assert "unknown" in result["message"].lower()
        assert result["allow_connection"] is True

    def test_fiber_connector_depends(self):
        """TC-VALIDATION-007: LC fiber connector depends on transceiver"""
        result = CableValidationService.validate_compatibility("lc", "sfp_plus")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.DEPENDS.value
        assert "transceiver" in result["message"].lower()

    def test_dac_perfect_match(self):
        """TC-VALIDATION-008: DAC cable to QSFP28 = perfect"""
        result = CableValidationService.validate_compatibility("dac", "qsfp28")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_aoc_perfect_match(self):
        """TC-VALIDATION-009: AOC cable to SFP+ = perfect"""
        result = CableValidationService.validate_compatibility("aoc", "sfp_plus")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_case_insensitive(self):
        """TC-VALIDATION-010: Cable and port types are case-insensitive"""
        result = CableValidationService.validate_compatibility("RJ45", "RJ45")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value

    def test_null_cable_type(self):
        """TC-VALIDATION-011: Null cable type returns unknown"""
        result = CableValidationService.validate_compatibility(None, "rj45")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.UNKNOWN.value

    def test_null_port_type(self):
        """TC-VALIDATION-012: Null port type returns unknown"""
        result = CableValidationService.validate_compatibility("rj45", None)

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.UNKNOWN.value

    def test_get_compatible_port_types(self):
        """TC-VALIDATION-013: Get list of compatible port types for SFP+"""
        compatible = CableValidationService.get_compatible_port_types("sfp_plus")

        assert "sfp_plus" in compatible
        assert "sfp" in compatible
        assert "sfp28" in compatible

    def test_get_compatible_port_types_unknown(self):
        """TC-VALIDATION-014: Unknown cable returns empty list"""
        compatible = CableValidationService.get_compatible_port_types("unknown_type")

        assert compatible == []

    def test_get_compatibility_summary(self):
        """TC-VALIDATION-015: Get compatibility summary for SFP+"""
        summary = CableValidationService.get_compatibility_summary("sfp_plus")

        assert "perfect" in summary
        assert "sfp_plus" in summary["perfect"]
        assert "downgrade" in summary
        assert "sfp" in summary["downgrade"]
