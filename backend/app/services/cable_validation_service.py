# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
"""Cable-to-Port Compatibility Validation Service

Validates cable connector types against port types and provides
compatibility warnings to help users avoid mismatched connections.
"""

from typing import Dict, List, Tuple, Any
from enum import Enum


class CompatibilityLevel(str, Enum):
    """Cable/port compatibility levels"""
    PERFECT = "perfect"
    COMPATIBLE = "compatible"
    DOWNGRADE = "downgrade"
    DEPENDS = "depends_on_transceiver"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CableValidationService:
    """
    Service for validating cable-to-port compatibility.

    Uses compatibility matrix to determine if a cable connector type
    is compatible with a port type, and returns appropriate warnings.
    """

    # Compatibility Matrix
    # Format: cable_connector_type -> [(port_type, compatibility_level, message)]
    COMPATIBILITY_MATRIX: Dict[str, List[Tuple[str, CompatibilityLevel, str]]] = {
        "rj45": [
            ("rj45", CompatibilityLevel.PERFECT, "Perfect match - Standard Ethernet"),
        ],

        "sfp": [
            ("sfp", CompatibilityLevel.PERFECT, "Perfect match - 1G SFP"),
            ("sfp_plus", CompatibilityLevel.COMPATIBLE, "SFP works in SFP+ port at 1G speed"),
        ],

        "sfp_plus": [
            ("sfp_plus", CompatibilityLevel.PERFECT, "Perfect match - 10G SFP+"),
            ("sfp", CompatibilityLevel.DOWNGRADE, "10G transceiver in 1G port - will run at 1G"),
            ("sfp28", CompatibilityLevel.COMPATIBLE, "SFP+ works in SFP28 port at 10G speed"),
        ],

        "sfp28": [
            ("sfp28", CompatibilityLevel.PERFECT, "Perfect match - 25G SFP28"),
            ("sfp_plus", CompatibilityLevel.DOWNGRADE, "25G in 10G port - will run at 10G"),
        ],

        "qsfp": [
            ("qsfp", CompatibilityLevel.PERFECT, "Perfect match - 40G QSFP"),
        ],

        "qsfp28": [
            ("qsfp28", CompatibilityLevel.PERFECT, "Perfect match - 100G QSFP28"),
            ("qsfp", CompatibilityLevel.COMPATIBLE, "100G transceiver in 40G port - check device support"),
            ("qsfp_dd", CompatibilityLevel.COMPATIBLE, "100G QSFP28 in 400G QSFP-DD port"),
        ],

        "qsfp_dd": [
            ("qsfp_dd", CompatibilityLevel.PERFECT, "Perfect match - 400G QSFP-DD"),
        ],

        "osfp": [
            ("osfp", CompatibilityLevel.PERFECT, "Perfect match - 400G/800G OSFP"),
            ("osfp_fin", CompatibilityLevel.COMPATIBLE, "OSFP to OSFP Finned - verify form factor"),
            ("osfp_flt", CompatibilityLevel.COMPATIBLE, "OSFP to OSFP Flat - verify form factor"),
        ],

        "osfp_fin": [
            ("osfp_fin", CompatibilityLevel.PERFECT, "Perfect match - OSFP Finned (switch ports)"),
            ("osfp", CompatibilityLevel.COMPATIBLE, "OSFP-FIN to legacy OSFP port"),
            ("osfp_flt", CompatibilityLevel.COMPATIBLE, "OSFP-FIN to OSFP-FLT - form factor mismatch, verify compatibility"),
        ],

        "osfp_flt": [
            ("osfp_flt", CompatibilityLevel.PERFECT, "Perfect match - OSFP Flat (network cards)"),
            ("osfp", CompatibilityLevel.COMPATIBLE, "OSFP-FLT to legacy OSFP port"),
            ("osfp_fin", CompatibilityLevel.COMPATIBLE, "OSFP-FLT to OSFP-FIN - form factor mismatch, verify compatibility"),
        ],

        "lc": [  # Fiber connector
            ("sfp", CompatibilityLevel.DEPENDS, "LC fiber - depends on installed transceiver"),
            ("sfp_plus", CompatibilityLevel.DEPENDS, "LC fiber - depends on installed transceiver"),
            ("sfp28", CompatibilityLevel.DEPENDS, "LC fiber - depends on installed transceiver"),
        ],

        "sc": [  # Fiber connector
            ("sfp", CompatibilityLevel.DEPENDS, "SC fiber - depends on installed transceiver"),
            ("sfp_plus", CompatibilityLevel.DEPENDS, "SC fiber - depends on installed transceiver"),
        ],

        "mpo": [  # Multi-fiber connector
            ("qsfp", CompatibilityLevel.PERFECT, "MPO to QSFP - parallel optics"),
            ("qsfp28", CompatibilityLevel.PERFECT, "MPO to QSFP28 - parallel optics"),
            ("qsfp_dd", CompatibilityLevel.PERFECT, "MPO to QSFP-DD - parallel optics"),
        ],

        "dac": [  # Direct Attach Copper
            ("sfp_plus", CompatibilityLevel.PERFECT, "SFP+ DAC - passive copper"),
            ("sfp28", CompatibilityLevel.PERFECT, "SFP28 DAC - passive copper"),
            ("qsfp", CompatibilityLevel.PERFECT, "QSFP DAC - passive copper"),
            ("qsfp28", CompatibilityLevel.PERFECT, "QSFP28 DAC - passive copper"),
            ("qsfp_dd", CompatibilityLevel.PERFECT, "QSFP-DD DAC - passive copper"),
        ],

        "aoc": [  # Active Optical Cable
            ("sfp_plus", CompatibilityLevel.PERFECT, "SFP+ AOC - active optical"),
            ("sfp28", CompatibilityLevel.PERFECT, "SFP28 AOC - active optical"),
            ("qsfp", CompatibilityLevel.PERFECT, "QSFP AOC - active optical"),
            ("qsfp28", CompatibilityLevel.PERFECT, "QSFP28 AOC - active optical"),
            ("qsfp_dd", CompatibilityLevel.PERFECT, "QSFP-DD AOC - active optical"),
        ],

        # Ethernet categories (for structured cabling)
        "cat5e": [
            ("rj45", CompatibilityLevel.PERFECT, "Cat5e to RJ45 - up to 1Gbps"),
        ],
        "cat6": [
            ("rj45", CompatibilityLevel.PERFECT, "Cat6 to RJ45 - up to 10Gbps @ 55m"),
        ],
        "cat6a": [
            ("rj45", CompatibilityLevel.PERFECT, "Cat6a to RJ45 - 10Gbps @ 100m"),
        ],

        # Other common types
        "console": [
            ("console", CompatibilityLevel.PERFECT, "Console cable match"),
            ("rj45", CompatibilityLevel.COMPATIBLE, "Console cable to RJ45 - for management"),
        ],
        "usb": [
            ("usb", CompatibilityLevel.PERFECT, "USB cable match"),
        ],
    }

    @classmethod
    def validate_compatibility(
        cls,
        cable_connector_type: str,
        port_type: str,
        cable_end: str = None,
        cable: "NetworkCable" = None
    ) -> Dict[str, Any]:
        """
        Validate cable/port compatibility.

        Args:
            cable_connector_type: Cable connector type (case-insensitive)
            port_type: Port type (case-insensitive)
            cable_end: Which end of the cable ('A' or 'B') - used with cable param
            cable: Optional NetworkCable object to get end-specific connector type

        Returns:
            {
                "compatible": bool,
                "level": CompatibilityLevel value,
                "message": str,
                "allow_connection": bool
            }
        """
        # If cable object provided with end, use end-specific connector type
        if cable and cable_end:
            if cable_end.upper() == "A" and hasattr(cable, 'connector_type_end_a') and cable.connector_type_end_a:
                cable_connector_type = cable.connector_type_end_a.value if hasattr(cable.connector_type_end_a, 'value') else str(cable.connector_type_end_a)
            elif cable_end.upper() == "B" and hasattr(cable, 'connector_type_end_b') and cable.connector_type_end_b:
                cable_connector_type = cable.connector_type_end_b.value if hasattr(cable.connector_type_end_b, 'value') else str(cable.connector_type_end_b)
            elif hasattr(cable, 'connector_type') and cable.connector_type:
                # Fallback to main connector_type if end-specific not set
                cable_connector_type = cable.connector_type.value if hasattr(cable.connector_type, 'value') else str(cable.connector_type)
        
        if not cable_connector_type or not port_type:
            return {
                "compatible": True,
                "level": CompatibilityLevel.UNKNOWN.value,
                "message": "Cable or port type not specified - compatibility cannot be verified",
                "allow_connection": True
            }

        cable_type = cable_connector_type.lower().strip()
        port_t = port_type.lower().strip()
        
        # Normalize both to underscores (matrix uses underscores for keys like osfp_fin)
        cable_type = cable_type.replace('-', '_')
        port_t = port_t.replace('-', '_')

        # Check if cable type is in matrix
        if cable_type not in cls.COMPATIBILITY_MATRIX:
            return {
                "compatible": True,  # Allow unknown types
                "level": CompatibilityLevel.UNKNOWN.value,
                "message": f"Unknown cable connector type '{cable_connector_type}'. Compatibility cannot be verified.",
                "allow_connection": True
            }

        # Check port type compatibility
        compatible_ports = cls.COMPATIBILITY_MATRIX[cable_type]

        for compatible_port, level, message in compatible_ports:
            # Both port_t and compatible_port already use underscores
            if compatible_port == port_t:
                return {
                    "compatible": True,
                    "level": level.value,
                    "message": message,
                    "allow_connection": True
                }

        # No match found - incompatible
        return {
            "compatible": False,
            "level": CompatibilityLevel.INCOMPATIBLE.value,
            "message": f"{cable_connector_type.upper()} cable is not compatible with {port_type.upper()} port. Connection may not work.",
            "allow_connection": True  # Still allow, but warn
        }

    @classmethod
    def get_compatible_port_types(cls, cable_connector_type: str) -> List[str]:
        """
        Get list of compatible port types for a cable.

        Args:
            cable_connector_type: Cable connector type

        Returns:
            List of compatible port types
        """
        if not cable_connector_type:
            return []

        cable_type = cable_connector_type.lower().strip()

        if cable_type not in cls.COMPATIBILITY_MATRIX:
            return []

        return [
            port_type
            for port_type, level, _ in cls.COMPATIBILITY_MATRIX[cable_type]
        ]

    @classmethod
    def get_compatibility_summary(cls, cable_connector_type: str) -> Dict[str, List[str]]:
        """
        Get summary of port compatibility for a cable type.

        Returns dict with port types grouped by compatibility level.
        """
        if not cable_connector_type:
            return {}

        cable_type = cable_connector_type.lower().strip()

        if cable_type not in cls.COMPATIBILITY_MATRIX:
            return {}

        summary: Dict[str, List[str]] = {}

        for port_type, level, _ in cls.COMPATIBILITY_MATRIX[cable_type]:
            level_name = level.value
            if level_name not in summary:
                summary[level_name] = []
            summary[level_name].append(port_type)

        return summary
