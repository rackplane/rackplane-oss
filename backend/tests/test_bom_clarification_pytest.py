# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Regression tests for BOM import clarification feature.

Tests that items requiring user input (like OSFP cable end types) are detected
and clarification questions are included in the preview response.
"""

import pytest
from app.services.vendor_parsers.base_parser import (
    VendorOrderParser,
    ParsedOrderItem,
    ClarificationQuestion
)


class TestableParser(VendorOrderParser):
    """Concrete parser for testing inherited methods."""
    vendor_name = "test"
    
    def can_parse(self, text):
        return False
    
    def parse(self, text):
        return None


@pytest.mark.regression
class TestClarificationDetection:
    """Test that parser detects items needing clarification."""

    def test_osfp_osfp_cable_needs_clarification(self):
        """
        Bug: OSFP/OSFP cables don't specify end types (Finned vs Flat)
        Fix: Detect ambiguous OSFP cables and request clarification
        """
        parser = TestableParser()
        description = "Cable, Infiniband NDR 800G, OSFP/OSFP, Passive Copper, 1.5m, Nvidia"
        
        questions = parser.detect_clarifications(description, "dac_cable")
        
        assert len(questions) == 2
        assert questions[0].field == "connector_type_end_a"
        assert questions[1].field == "connector_type_end_b"
        assert "osfp-fin" in questions[0].options
        assert "osfp-flt" in questions[0].options

    def test_osfp_dac_cable_needs_clarification(self):
        """OSFP DAC cables without finned/flat specified need clarification."""
        parser = TestableParser()
        description = "MCA7J40-N003 800G OSFP DAC Cable 3m"
        
        questions = parser.detect_clarifications(description, "dac_cable")
        
        assert len(questions) == 2
        assert questions[0].field == "connector_type_end_a"
        assert questions[1].field == "connector_type_end_b"

    def test_osfp_finned_cable_no_clarification_needed(self):
        """OSFP cables with 'finned' or 'flat' specified don't need clarification."""
        parser = TestableParser()
        description = "800G OSFP Finned DAC Cable 1.5m"
        
        questions = parser.detect_clarifications(description, "dac_cable")
        
        assert len(questions) == 0

    def test_osfp_flt_cable_no_clarification_needed(self):
        """OSFP cables with 'flt' specified don't need clarification."""
        parser = TestableParser()
        description = "800G OSFP-FLT to OSFP-FIN DAC Cable"
        
        questions = parser.detect_clarifications(description, "dac_cable")
        
        assert len(questions) == 0

    def test_qsfp28_cable_no_clarification_needed(self):
        """QSFP28 cables don't need end type clarification."""
        parser = TestableParser()
        description = "100G QSFP28 DAC Cable 3m"
        
        questions = parser.detect_clarifications(description, "dac_cable")
        
        assert len(questions) == 0

    def test_ethernet_cable_no_clarification_needed(self):
        """Ethernet cables don't need clarification."""
        parser = TestableParser()
        description = "CAT6A Patch Cable 10ft Blue"
        
        questions = parser.detect_clarifications(description, "ethernet_cable")
        
        assert len(questions) == 0


@pytest.mark.regression
class TestClarificationQuestionModel:
    """Test the ClarificationQuestion model."""

    def test_clarification_question_has_required_fields(self):
        """ClarificationQuestion must have field, question, options, default."""
        question = ClarificationQuestion(
            field="connector_type_end_a",
            question="What connector type on End A?",
            options=["osfp-fin", "osfp-flt"],
            default="osfp-fin"
        )
        
        assert question.field == "connector_type_end_a"
        assert question.question == "What connector type on End A?"
        assert question.options == ["osfp-fin", "osfp-flt"]
        assert question.default == "osfp-fin"

    def test_clarification_question_default_is_optional(self):
        """Default value should be optional (None allowed)."""
        question = ClarificationQuestion(
            field="test_field",
            question="Test question?",
            options=["a", "b"]
        )
        
        assert question.default is None


@pytest.mark.regression
class TestParsedOrderItemClarification:
    """Test clarification fields on ParsedOrderItem."""

    def test_parsed_item_has_clarification_fields(self):
        """ParsedOrderItem should have clarification support."""
        item = ParsedOrderItem(
            description="Test cable",
            needs_clarification=True,
            clarification_questions=[
                ClarificationQuestion(
                    field="test",
                    question="Test?",
                    options=["a", "b"]
                )
            ]
        )
        
        assert item.needs_clarification is True
        assert len(item.clarification_questions) == 1

    def test_parsed_item_clarification_defaults(self):
        """Clarification fields should default to not needing clarification."""
        item = ParsedOrderItem(description="Test item")
        
        assert item.needs_clarification is False
        assert item.clarification_questions == []
        assert item.clarification_answers == {}
