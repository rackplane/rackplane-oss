# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Serial Number Generation Service

Generates unique, human-readable serial numbers and asset tags with:
- Type prefix (e.g., DAC, SRV, SW)
- Tenant identifier (4-char abbreviation)
- Random alphanumeric block (no ambiguous characters)
- Check digit for typo detection

Format: {TYPE}-{TENANT}-{RANDOM}-{CHECK}
Example: DAC-ACME-K7X9M2-4
"""

import secrets
import string
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.asset import Asset
from app.models.tenant import Tenant
from app.core.tenant import get_current_tenant_id, set_current_tenant_id


# Alphabet without ambiguous characters (0/O, 1/I/L)
# 32 characters: A-H, J-N, P-Z, 2-9
SAFE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

# Asset type to prefix mapping
# 2-4 character codes that are meaningful and unique
TYPE_PREFIXES = {
    # Servers and compute
    "server": "SRV",
    "blade_server": "BLD",
    "virtual_machine": "VM",
    
    # Network equipment
    "switch": "SW",
    "router": "RTR",
    "firewall": "FW",
    "load_balancer": "LB",
    "access_point": "AP",
    
    # Storage
    "storage": "STO",
    "nas": "NAS",
    "san": "SAN",
    "storage_box": "BOX",
    "storage_device": "BOX",
    
    # Cables
    "dac_cable": "DAC",
    "fiber_cable": "FBR",
    "ethernet_cable": "ETH",
    "network_cable": "NET",
    "power_cable": "PWR",
    "electrical_cable": "ELC",
    
    # Transceivers
    "copper_transceiver": "CXC",
    "optical_transceiver": "OXC",
    "transceiver": "XCV",
    
    # Power
    "pdu": "PDU",
    "ups": "UPS",
    "power_strip": "PST",
    
    # Other
    "patch_panel": "PNL",
    "kvm": "KVM",
    "console_server": "CON",
    "monitor": "MON",
    "keyboard": "KBD",
    "other": "OTH",
}

# Default prefix for unknown types
DEFAULT_PREFIX = "AST"


def get_type_prefix(asset_type: str) -> str:
    """
    Get the 2-4 character prefix for an asset type.
    
    Args:
        asset_type: The asset type string (e.g., "dac_cable", "server")
        
    Returns:
        The prefix code (e.g., "DAC", "SRV")
    """
    if not asset_type:
        return DEFAULT_PREFIX
    
    normalized = asset_type.lower().strip()
    
    # Direct lookup
    if normalized in TYPE_PREFIXES:
        return TYPE_PREFIXES[normalized]
    
    # Try partial matches (e.g., "my_custom_server" -> "SRV")
    for type_name, prefix in TYPE_PREFIXES.items():
        if type_name in normalized or normalized in type_name:
            return prefix
    
    # Generate a prefix from the first 3 characters
    if len(normalized) >= 3:
        return normalized[:3].upper()
    
    return DEFAULT_PREFIX


def get_tenant_code(db: Session, tenant_id: Optional[int] = None) -> str:
    """
    Get a 4-character tenant code from the tenant slug.
    
    Args:
        db: Database session
        tenant_id: Tenant ID (uses current tenant if not provided)
        
    Returns:
        4-character tenant code (e.g., "ACME")
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    
    if not tenant_id:
        return "DFLT"  # Default tenant code
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return "DFLT"
    
    # Use slug, sanitize and uppercase
    slug = tenant.slug.upper().replace("-", "").replace("_", "")
    
    # Take first 4 characters, pad if necessary
    if len(slug) >= 4:
        return slug[:4]
    else:
        return slug.ljust(4, "X")


def generate_random_block(length: int = 6) -> str:
    """
    Generate a random alphanumeric block using safe characters.
    
    Args:
        length: Number of characters (default 6)
        
    Returns:
        Random string like "K7X9M2"
    """
    return ''.join(secrets.choice(SAFE_ALPHABET) for _ in range(length))


def calculate_check_digit(data: str) -> str:
    """
    Calculate a Luhn mod N check digit for the given string.
    
    This uses a modified Luhn algorithm that works with alphanumeric characters.
    The check digit helps catch typos when manually entering serial numbers.
    
    Args:
        data: The string to calculate check digit for
        
    Returns:
        Single character check digit
    """
    # Convert to numeric values using SAFE_ALPHABET positions
    values = []
    for char in data.upper():
        if char in SAFE_ALPHABET:
            values.append(SAFE_ALPHABET.index(char))
        elif char.isdigit():
            values.append(int(char))
        # Skip other characters (like hyphens)
    
    if not values:
        return "0"
    
    # Luhn algorithm
    total = 0
    for i, val in enumerate(reversed(values)):
        if i % 2 == 0:
            doubled = val * 2
            if doubled >= len(SAFE_ALPHABET):
                doubled = doubled - len(SAFE_ALPHABET) + 1
            total += doubled
        else:
            total += val
    
    check = (len(SAFE_ALPHABET) - (total % len(SAFE_ALPHABET))) % len(SAFE_ALPHABET)
    return SAFE_ALPHABET[check]


def validate_check_digit(serial: str) -> bool:
    """
    Validate that a serial number has a correct check digit.
    
    Args:
        serial: Full serial number including check digit
        
    Returns:
        True if valid, False if invalid
    """
    if not serial or len(serial) < 2:
        return False
    
    # Split off the check digit (last character after final hyphen)
    parts = serial.rsplit("-", 1)
    if len(parts) != 2:
        return False
    
    data, check = parts
    expected = calculate_check_digit(data)
    return check.upper() == expected


def generate_serial_number(
    db: Session,
    asset_type: str,
    tenant_id: Optional[int] = None,
    random_length: int = 6
) -> str:
    """
    Generate a unique serial number for an asset.
    
    Format: {TYPE}-{TENANT}-{RANDOM}-{CHECK}
    Example: DAC-ACME-K7X9M2-4
    
    Args:
        db: Database session
        asset_type: The asset type (e.g., "dac_cable")
        tenant_id: Tenant ID (uses current tenant if not provided)
        random_length: Length of random block (default 6)
        
    Returns:
        Unique serial number string
    """
    prefix = get_type_prefix(asset_type)
    tenant_code = get_tenant_code(db, tenant_id)
    
    # Set tenant context for queries
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    
    # Temporarily set tenant context if provided
    original_tenant_id = None
    if tenant_id:
        original_tenant_id = get_current_tenant_id()
        set_current_tenant_id(tenant_id)
    
    try:
        # Keep generating until we get a unique one (collision is extremely unlikely)
        max_attempts = 100
        for _ in range(max_attempts):
            random_block = generate_random_block(random_length)
            
            # Build serial without check digit
            serial_base = f"{prefix}-{tenant_code}-{random_block}"
            check_digit = calculate_check_digit(serial_base)
            serial = f"{serial_base}-{check_digit}"
            
            # Check uniqueness within tenant
            from app.core.tenant_query import apply_tenant_filter
            query = db.query(Asset).filter(Asset.serial_number == serial)
            query = apply_tenant_filter(query, Asset)
            
            if not query.first():
                return serial
    finally:
        # Restore original tenant context
        if original_tenant_id is not None:
            set_current_tenant_id(original_tenant_id)
        elif tenant_id and original_tenant_id is None:
            # Clear tenant context if we set it and there wasn't one before
            from app.core.tenant import clear_tenant_id
            clear_tenant_id()
    
    # Fallback: add timestamp if we somehow can't find unique (should never happen)
    import time
    return f"{prefix}-{tenant_code}-{int(time.time())}"


def generate_asset_tag(
    db: Session,
    asset_type: str,
    tenant_id: Optional[int] = None
) -> str:
    """
    Generate a unique asset tag.
    
    Format: {TYPE}-{RANDOM4}
    Example: DAC-K7X9
    
    Asset tags are shorter than serial numbers for easier labeling.
    
    Args:
        db: Database session
        asset_type: The asset type (e.g., "dac_cable")
        tenant_id: Tenant ID (uses current tenant if not provided)
        
    Returns:
        Unique asset tag string
    """
    prefix = get_type_prefix(asset_type)
    
    # Set tenant context for queries
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    
    # Temporarily set tenant context if provided
    original_tenant_id = None
    if tenant_id:
        original_tenant_id = get_current_tenant_id()
        set_current_tenant_id(tenant_id)
    
    try:
        # Keep generating until we get a unique one
        max_attempts = 100
        for _ in range(max_attempts):
            random_block = generate_random_block(4)
            tag = f"{prefix}-{random_block}"
            
            # Check uniqueness within tenant
            from app.core.tenant_query import apply_tenant_filter
            query = db.query(Asset).filter(Asset.asset_tag == tag)
            query = apply_tenant_filter(query, Asset)
            
            if not query.first():
                return tag
    finally:
        # Restore original tenant context
        if original_tenant_id is not None:
            set_current_tenant_id(original_tenant_id)
        elif tenant_id and original_tenant_id is None:
            # Clear tenant context if we set it and there wasn't one before
            from app.core.tenant import clear_tenant_id
            clear_tenant_id()
    
    # Fallback: use longer random block
    return f"{prefix}-{generate_random_block(8)}"


def generate_bulk_serials(
    db: Session,
    asset_type: str,
    quantity: int,
    tenant_id: Optional[int] = None
) -> List[Tuple[str, str]]:
    """
    Generate multiple unique serial numbers and asset tags for bulk creation.
    
    Args:
        db: Database session
        asset_type: The asset type (e.g., "dac_cable")
        quantity: Number of serial/tag pairs to generate
        tenant_id: Tenant ID (uses current tenant if not provided)
        
    Returns:
        List of (serial_number, asset_tag) tuples
    """
    results = []
    generated_serials = set()
    generated_tags = set()
    
    for _ in range(quantity):
        # Generate unique serial
        serial = generate_serial_number(db, asset_type, tenant_id)
        while serial in generated_serials:
            serial = generate_serial_number(db, asset_type, tenant_id)
        generated_serials.add(serial)
        
        # Generate unique tag
        tag = generate_asset_tag(db, asset_type, tenant_id)
        while tag in generated_tags:
            tag = generate_asset_tag(db, asset_type, tenant_id)
        generated_tags.add(tag)
        
        results.append((serial, tag))
    
    return results


# Utility function to add custom type prefixes at runtime
def register_type_prefix(asset_type: str, prefix: str) -> None:
    """
    Register a custom asset type prefix.
    
    Args:
        asset_type: The asset type name
        prefix: The 2-4 character prefix
    """
    TYPE_PREFIXES[asset_type.lower()] = prefix.upper()[:4]

