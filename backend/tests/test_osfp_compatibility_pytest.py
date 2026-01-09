# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
"""Tests for OSFP Port Type Variants (OSFP_FIN and OSFP_FLT)

Regression tests to ensure:
1. OSFP_FIN to OSFP_FIN = perfect
2. OSFP_FLT to OSFP_FLT = perfect
3. OSFP_FIN to OSFP_FLT = compatible (form factor mismatch)
4. Legacy OSFP to new types = compatible
"""

import pytest
from app.services.cable_validation_service import CableValidationService, CompatibilityLevel


@pytest.mark.regression
class TestOSFPPortTypeVariants:
    """Tests for new OSFP port type variants"""

    def test_osfp_fin_to_osfp_fin_perfect(self):
        """TC-OSFP-001: OSFP Finned cable to OSFP Finned port = perfect match"""
        result = CableValidationService.validate_compatibility("osfp_fin", "osfp_fin")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value
        assert "switch" in result["message"].lower() or "finned" in result["message"].lower()
        assert result["allow_connection"] is True

    def test_osfp_flt_to_osfp_flt_perfect(self):
        """TC-OSFP-002: OSFP Flat cable to OSFP Flat port = perfect match"""
        result = CableValidationService.validate_compatibility("osfp_flt", "osfp_flt")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value
        assert "network card" in result["message"].lower() or "flat" in result["message"].lower()
        assert result["allow_connection"] is True

    def test_osfp_fin_to_osfp_flt_compatible(self):
        """TC-OSFP-003: OSFP Finned cable to OSFP Flat port = compatible with warning"""
        result = CableValidationService.validate_compatibility("osfp_fin", "osfp_flt")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert "form factor" in result["message"].lower() or "mismatch" in result["message"].lower()
        assert result["allow_connection"] is True

    def test_osfp_flt_to_osfp_fin_compatible(self):
        """TC-OSFP-004: OSFP Flat cable to OSFP Finned port = compatible with warning"""
        result = CableValidationService.validate_compatibility("osfp_flt", "osfp_fin")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert "form factor" in result["message"].lower() or "mismatch" in result["message"].lower()
        assert result["allow_connection"] is True

    def test_legacy_osfp_to_osfp_fin_compatible(self):
        """TC-OSFP-005: Legacy OSFP cable to OSFP Finned port = compatible"""
        result = CableValidationService.validate_compatibility("osfp", "osfp_fin")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert result["allow_connection"] is True

    def test_legacy_osfp_to_osfp_flt_compatible(self):
        """TC-OSFP-006: Legacy OSFP cable to OSFP Flat port = compatible"""
        result = CableValidationService.validate_compatibility("osfp", "osfp_flt")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert result["allow_connection"] is True

    def test_osfp_fin_to_legacy_osfp_compatible(self):
        """TC-OSFP-007: OSFP Finned cable to legacy OSFP port = compatible"""
        result = CableValidationService.validate_compatibility("osfp_fin", "osfp")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert result["allow_connection"] is True

    def test_osfp_flt_to_legacy_osfp_compatible(self):
        """TC-OSFP-008: OSFP Flat cable to legacy OSFP port = compatible"""
        result = CableValidationService.validate_compatibility("osfp_flt", "osfp")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.COMPATIBLE.value
        assert result["allow_connection"] is True

    def test_legacy_osfp_perfect_match(self):
        """TC-OSFP-009: Legacy OSFP to legacy OSFP still works"""
        result = CableValidationService.validate_compatibility("osfp", "osfp")

        assert result["compatible"] is True
        assert result["level"] == CompatibilityLevel.PERFECT.value
        assert result["allow_connection"] is True

    def test_osfp_to_qsfp_incompatible(self):
        """TC-OSFP-010: OSFP types incompatible with QSFP family"""
        # OSFP_FIN to QSFP28 should be incompatible
        result = CableValidationService.validate_compatibility("osfp_fin", "qsfp28")

        assert result["compatible"] is False
        assert result["level"] == CompatibilityLevel.INCOMPATIBLE.value
        assert result["allow_connection"] is True  # Still allow but warn

    def test_osfp_case_insensitive(self):
        """TC-OSFP-011: OSFP types are case-insensitive"""
        result_lower = CableValidationService.validate_compatibility("osfp_fin", "osfp_fin")
        result_upper = CableValidationService.validate_compatibility("OSFP_FIN", "OSFP_FIN")

        assert result_lower["level"] == result_upper["level"]
        assert result_lower["compatible"] == result_upper["compatible"]

    def test_get_compatible_port_types_osfp_fin(self):
        """TC-OSFP-012: Compatible ports list for OSFP_FIN includes expected types"""
        compatible = CableValidationService.get_compatible_port_types("osfp_fin")

        assert "osfp_fin" in compatible
        assert "osfp" in compatible
        assert "osfp_flt" in compatible
        assert len(compatible) == 3
