# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Serial Number Generation Service Test Suite
Tests for unique serial number and asset tag generation logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.serial_service import (
    get_type_prefix,
    get_tenant_code,
    generate_random_block,
    calculate_check_digit,
    TYPE_PREFIXES,
    SAFE_ALPHABET,
    DEFAULT_PREFIX
)
from app.models.tenant import Tenant


class TestTypePrefixMapping:
    """Test asset type to prefix mapping"""

    def test_get_prefix_for_server(self):
        assert get_type_prefix("server") == "SRV"

    def test_get_prefix_for_switch(self):
        assert get_type_prefix("switch") == "SW"

    def test_get_prefix_for_dac_cable(self):
        assert get_type_prefix("dac_cable") == "DAC"

    def test_get_prefix_for_storage_box(self):
        assert get_type_prefix("storage_box") == "BOX"

    def test_get_prefix_case_insensitive(self):
        assert get_type_prefix("SERVER") == "SRV"

    def test_get_prefix_partial_match(self):
        assert get_type_prefix("custom_server") == "SRV"

    def test_get_prefix_unknown_uses_first_3(self):
        assert get_type_prefix("foobar") == "FOO"

    def test_get_prefix_empty_uses_default(self):
        assert get_type_prefix("") == DEFAULT_PREFIX


class TestTenantCodeGeneration:
    """Test tenant code generation"""

    def test_get_tenant_code_from_slug(self, db_session):
        tenant = Mock(spec=Tenant)
        tenant.slug = "acme-corp"

        with patch.object(db_session, 'query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.return_value = tenant
            mock_query.return_value.filter.return_value = mock_filter

            result = get_tenant_code(db_session, tenant_id=1)

        assert result == "ACME"

    def test_get_tenant_code_pads_short_slug(self, db_session):
        tenant = Mock(spec=Tenant)
        tenant.slug = "ab"

        with patch.object(db_session, 'query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.return_value = tenant
            mock_query.return_value.filter.return_value = mock_filter

            result = get_tenant_code(db_session, tenant_id=1)

        assert result == "ABXX"


class TestRandomBlockGeneration:
    """Test random block generation"""

    def test_default_length_is_6(self):
        assert len(generate_random_block()) == 6

    def test_uses_safe_alphabet(self):
        result = generate_random_block(length=20)
        for char in result:
            assert char in SAFE_ALPHABET

    def test_no_ambiguous_chars(self):
        result = generate_random_block(length=50)
        assert '0' not in result
        assert 'O' not in result


class TestCheckDigitCalculation:
    """Test check digit"""

    def test_deterministic(self):
        assert calculate_check_digit("TEST") == calculate_check_digit("TEST")

    def test_single_character(self):
        assert len(calculate_check_digit("ABC123")) == 1

    def test_uses_safe_alphabet(self):
        assert calculate_check_digit("TEST") in SAFE_ALPHABET
