# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Connector Type Normalization

Normalizes raw connector type strings from vendor data to valid enum values.
Handles variations in naming conventions across different vendors and sources.
"""

from typing import Optional


# Mapping of raw connector strings to normalized enum values
# Key: raw value (case-insensitive), Value: normalized connector type
CONNECTOR_NORMALIZATION_MAP = {
    # OSFP variants - normalize to enum values
    "osfp flat": "OSFP_FLT",
    "osfp-flat": "OSFP_FLT",
    "osfp_flat": "OSFP_FLT",
    "osfp flt": "OSFP_FLT",
    "osfp-flt": "OSFP_FLT",
    "osfp finned": "OSFP_FIN",
    "osfp-finned": "OSFP_FIN",
    "osfp_finned": "OSFP_FIN",
    "osfp fin": "OSFP_FIN",
    "osfp-fin": "OSFP_FIN",
    
    # QSFP family - keep distinct form factors
    # QSFP-DD has double-deep physical form factor
    "qsfp-dd": "QSFP_DD",
    "qsfpdd": "QSFP_DD",
    "qsfp dd": "QSFP_DD",
    
    # QSFP112 is separate - 200/400G with 112G/lane in regular QSFP form factor
    "qsfp112": "QSFP112",
    
    # QSFP56 - 200G with 56G/lane
    "qsfp56": "QSFP56",
    
    # Standard QSFP types
    "qsfp28": "QSFP28",
    "qsfp+": "QSFP_PLUS",
    "qsfp-plus": "QSFP_PLUS",
    
    # SFP family
    "sfp+": "SFP_PLUS",
    "sfp-plus": "SFP_PLUS",
    "sfp28": "SFP28",
    "sfp56": "SFP56",
}


def normalize_connector_type(raw: Optional[str]) -> Optional[str]:
    """
    Normalize a raw connector type string to a standard enum value.
    
    Args:
        raw: Raw connector type string from vendor data
        
    Returns:
        Normalized connector type string, or the original if no mapping exists
        
    Examples:
        >>> normalize_connector_type("OSFP Flat")
        'OSFP_FLT'
        >>> normalize_connector_type("qsfp-dd")
        'QSFP_DD'
        >>> normalize_connector_type("QSFP112")
        'QSFP112'
    """
    if not raw:
        return raw
    
    # Check for exact match first (case-insensitive)
    normalized = CONNECTOR_NORMALIZATION_MAP.get(raw.lower())
    if normalized:
        return normalized
    
    # If no mapping found, return the original value
    # This allows new connector types to pass through
    return raw


def get_connector_family(connector_type: str) -> str:
    """
    Get the connector family from a connector type.
    
    Useful for compatibility checking - connectors in the same family
    may have varying physical compatibility.
    
    Args:
        connector_type: Normalized connector type
        
    Returns:
        Connector family (e.g., "OSFP", "QSFP", "SFP")
    """
    if not connector_type:
        return "UNKNOWN"
    
    upper = connector_type.upper()
    
    if upper.startswith("OSFP"):
        return "OSFP"
    elif upper.startswith("QSFP"):
        return "QSFP"
    elif upper.startswith("SFP"):
        return "SFP"
    elif upper == "RJ45":
        return "RJ45"
    elif upper in ("LC", "SC", "MPO", "MTP"):
        return "FIBER"
    else:
        return "OTHER"
