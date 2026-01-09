"""
Service Implementations for RackPlane - OSS Version
Contains OSS implementations only (no premium, no NetBox)
"""
# OSS implementations
from .oss import (
    LocalOCRService,
    LocalCatalogService,
    StubVendorLookup,
    StubScraperService,
)

# Premium implementations not available in OSS build
PREMIUM_AVAILABLE = False

__all__ = [
    # OSS
    'LocalOCRService',
    'LocalCatalogService',
    'StubVendorLookup',
    'StubScraperService',
    'PREMIUM_AVAILABLE',
]
