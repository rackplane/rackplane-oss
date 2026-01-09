# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Base Vendor Order Parser

Abstract base class defining the interface for vendor-specific order parsers.
Each vendor parser extracts order metadata and line items from PDFs/documents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ClarificationQuestion(BaseModel):
    """A question that needs user input before import."""
    field: str  # Field name, e.g., "connector_type_end_a"
    question: str  # Human-readable question
    options: List[str] = []  # Available options (empty = free text)
    default: Optional[str] = None  # Default value if user doesn't answer


class ParsedOrderItem(BaseModel):
    """A single line item from an order/invoice."""
    description: str
    quantity: int = 1
    unit_price: Optional[float] = None
    extended_price: Optional[float] = None
    
    # Optional product identifiers
    part_number: Optional[str] = None
    sku: Optional[str] = None
    manufacturer: Optional[str] = None
    
    # Category hints for asset type mapping
    category: Optional[str] = None  # e.g., "server", "switch", "cable", "transceiver"
    
    # Clarification support - for items needing user input before import
    needs_clarification: bool = False
    clarification_questions: List[ClarificationQuestion] = []
    clarification_answers: Dict[str, str] = {}  # User-provided answers
    
    # Raw metadata for vendor-specific fields
    raw_data: Dict[str, Any] = {}


class ParsedOrder(BaseModel):
    """Parsed order/invoice from a vendor."""
    vendor: str  # e.g., "Penguin Computing", "FS.com", "Dell"
    order_number: Optional[str] = None
    order_date: Optional[str] = None
    
    # Customer/shipping info
    customer_name: Optional[str] = None
    shipping_address: Optional[str] = None
    
    # Line items
    items: List[ParsedOrderItem] = []
    
    # Totals
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    freight: Optional[float] = None
    total: Optional[float] = None
    
    # Raw metadata
    raw_text: Optional[str] = None
    raw_data: Dict[str, Any] = {}


class VendorOrderParser(ABC):
    """Abstract base class for vendor order parsers."""
    
    # Subclasses must define these
    vendor_name: str = "Unknown"
    vendor_patterns: List[str] = []  # Patterns to detect this vendor in text
    
    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """
        Check if this parser can handle the given document text.
        
        Args:
            text: Extracted text from the document
            
        Returns:
            True if this parser can handle the document
        """
        pass
    
    @abstractmethod
    def parse(self, text: str) -> ParsedOrder:
        """
        Parse document text and extract order information.
        
        Args:
            text: Extracted text from the document
            
        Returns:
            ParsedOrder with extracted information
        """
        pass
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """
        Helper to parse price strings like "$1,234.56" or "US$100.00".
        
        Args:
            price_str: Price string to parse
            
        Returns:
            Float value or None if parsing fails
        """
        if not price_str:
            return None
        try:
            # Remove currency symbols and commas
            cleaned = price_str.replace("$", "").replace(",", "").replace("US", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def detect_category(self, description: str) -> Optional[str]:
        """
        Detect asset category from item description.
        
        Args:
            description: Item description text
            
        Returns:
            Category string or None
        """
        desc_lower = description.lower()
        
        # SERVICES FIRST - must check before "server" keyword catches "server-level"
        # Look for service-specific patterns
        service_indicators = [
            "professional service",
            "integration",
            "installation",
            "deployment service",
            "per node",
            "per rack",
            "per gpu",
            "extended warranty",
            "warranty service",
            "support service",
            "support plan",
            "maintenance contract",
            "service level",
            "server-level",  # This is a support tier, not a server!
            "travel expense",
            "consulting",
            "training",
        ]
        if any(kw in desc_lower for kw in service_indicators):
            return "service"
        
        # Servers - more specific patterns
        if any(kw in desc_lower for kw in ["server", "hgx", "dgx", "supermicro", "poweredge"]):
            # Double-check it's not a service with "server" in the name
            if not any(kw in desc_lower for kw in ["service", "support", "warranty", "integration"]):
                return "server"
        
        # Switches
        if any(kw in desc_lower for kw in ["switch", "sn5", "sn2", "nexus"]):
            return "network_switch"
        
        # Racks
        if any(kw in desc_lower for kw in ["rack", "42u", "eia"]):
            return "rack"
        
        # PDUs
        if any(kw in desc_lower for kw in ["pdu", "power distribution"]):
            return "pdu"
        
        # Transceivers (return the actual asset type name)
        if any(kw in desc_lower for kw in ["transceiver", "sfp", "qsfp", "osfp"]):
            return "optical_transceiver"
        
        # Cables - order matters! More specific matches first
        # Check for Ethernet cables (CAT5, CAT6, RJ45, etc.)
        if any(kw in desc_lower for kw in ["cat5", "cat6", "cat7", "cat8", "rj45", "ethernet", "utp", "patch cable"]):
            return "ethernet_cable"
        
        # Check for DAC cables (Direct Attach Copper)
        if any(kw in desc_lower for kw in ["dac", "direct attach", "copper cable", "twinax", "passive copper"]):
            return "dac_cable"
        
        # Check for InfiniBand cables
        if any(kw in desc_lower for kw in ["infiniband", "ib cable", "mellanox cable", "nvidia cable", "hdr", "edr", "qdr", "fdr"]):
            return "infiniband_cable"
        
        # Check for fiber cables (AOC, fiber optic, SMF, MMF)
        if any(kw in desc_lower for kw in ["fiber", "aoc", "active optical", "smf", "mmf", "lc-lc", "sc-sc", "mtp", "mpo"]):
            return "fiber_cable"
        
        # Generic cable fallback (still catches "cable" keyword)
        if "cable" in desc_lower:
            # Default to ethernet if no specific type detected
            return "ethernet_cable"
        
        # Fallback service check for remaining patterns
        if any(kw in desc_lower for kw in ["service", "support", "professional", "warranty", "travel"]):
            return "service"
        
        return None

    def detect_clarifications(self, description: str, category: Optional[str]) -> List[ClarificationQuestion]:
        """
        Detect if an item needs clarification before import.
        
        Returns a list of questions the user should answer.
        
        Args:
            description: Item description text
            category: Already-detected category (from detect_category)
            
        Returns:
            List of ClarificationQuestion objects
        """
        questions = []
        desc_lower = description.lower()
        
        # OSFP cables - need to know which end type (Finned vs Flat)
        if category in ["dac_cable", "infiniband_cable", "fiber_cable"]:
            # Check for OSFP with unclear end types
            has_osfp = "osfp" in desc_lower
            
            # Patterns indicating both ends are OSFP (but type unclear)
            ambiguous_patterns = [
                "osfp/osfp",
                "osfp-osfp",
                "osfp to osfp",
                "osfp - osfp",
            ]
            is_ambiguous = any(p in desc_lower for p in ambiguous_patterns)
            
            # Specific patterns that indicate the end type IS specified
            # Use more specific patterns to avoid false positives (e.g., 'Infiniband' contains 'fin')
            specified_patterns = [
                "osfp-fin",     # Common format: OSFP-FIN  
                "osfp_fin",     # Underscore variant
                "osfp fin",     # Space variant
                "osfp-flt",     # Common format: OSFP-FLT
                "osfp_flt",     # Underscore variant
                "osfp flt",     # Space variant
                "osfp finned",  # Full word
                "osfp flat",    # Full word
                "finned osfp",  # Reversed order
                "flat osfp",    # Reversed order
            ]
            end_type_specified = any(p in desc_lower for p in specified_patterns)
            
            # If OSFP is mentioned but end type is not specified, ask for clarification
            if has_osfp and not end_type_specified:
                questions.append(ClarificationQuestion(
                    field="connector_type_end_a",
                    question="What is the connector type on End A?",
                    options=["osfp-fin", "osfp-flt", "osfp"],
                    default=None  # No default - user must choose
                ))
                questions.append(ClarificationQuestion(
                    field="connector_type_end_b",
                    question="What is the connector type on End B?",
                    options=["osfp-fin", "osfp-flt", "osfp"],
                    default=None
                ))
        
        # QSFP-DD cables - similar situation (DD vs regular QSFP)
        if category in ["dac_cable", "fiber_cable"] and "qsfp" in desc_lower:
            if "qsfp-dd" in desc_lower or "qsfp dd" in desc_lower:
                # QSFP-DD to QSFP28 breakout is common, ask if unclear
                if any(p in desc_lower for p in ["qsfp-dd/qsfp28", "qsfp-dd to qsfp28"]):
                    # Already clear - no need to ask
                    pass
                elif "dd" in desc_lower and "qsfp28" not in desc_lower:
                    # Might be homogeneous QSFP-DD
                    pass
        
        return questions
