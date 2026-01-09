# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Version Constants - Single Source of Truth

This module contains all version-related constants for the API.
Import from here to ensure consistency across the application.
"""

# API Version Components
API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0
API_VERSION_PATCH = 0

# Formatted version strings
API_VERSION = f"{API_VERSION_MAJOR}.{API_VERSION_MINOR}.{API_VERSION_PATCH}"
API_VERSION_PREFIX = f"v{API_VERSION_MAJOR}"

# Supported API versions (for backward compatibility)
SUPPORTED_API_VERSIONS = ["v1"]
MINIMUM_SUPPORTED_VERSION = 1
MAXIMUM_SUPPORTED_VERSION = 1

# Documentation URLs - centralized for easy maintenance
DOCS_BASE_URL = "https://docs.rackplane.com"
CHANGELOG_URL = f"{DOCS_BASE_URL}/changelog"
API_DOCS_URL = f"{DOCS_BASE_URL}/api"

def get_migration_guide_url(from_version: int, to_version: int) -> str:
    """Generate migration guide URL for version upgrades."""
    return f"{DOCS_BASE_URL}/migration/v{from_version}-to-v{to_version}"
