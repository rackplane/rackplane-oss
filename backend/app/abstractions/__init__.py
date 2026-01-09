"""
Service Abstractions for RackPlane
Provides abstract base classes for service implementations (OSS and Premium)
"""
from .ocr import OCRServiceInterface
from .catalog import CatalogServiceInterface
from .vendor_lookup import VendorLookupInterface
from .scraping import ScraperServiceInterface
from .netbox import NetBoxSyncInterface

__all__ = [
    'OCRServiceInterface',
    'CatalogServiceInterface',
    'VendorLookupInterface',
    'ScraperServiceInterface',
    'NetBoxSyncInterface',
]
