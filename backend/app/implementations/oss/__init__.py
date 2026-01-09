"""
OSS Service Implementations
Provides open-source implementations of service interfaces
NetBox integration is excluded in OSS build
"""
from .ocr_local import LocalOCRService
from .catalog_local import LocalCatalogService
from .vendor_stub import StubVendorLookup
from .scraper_stub import StubScraperService

# NetBox is excluded from OSS build
# ReadOnlyNetBoxService requires premium netbox_service.py

__all__ = [
    'LocalOCRService',
    'LocalCatalogService',
    'StubVendorLookup',
    'StubScraperService',
]
