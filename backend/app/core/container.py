"""
Dependency Injection Container - OSS Version
Provides service instances for OSS build (no NetBox, no premium services)
"""

import os
from typing import Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

# Import abstractions
from app.abstractions import (
    OCRServiceInterface,
    VendorLookupInterface,
    CatalogServiceInterface,
    ScraperServiceInterface,
)

# Import OSS implementations (always available)
from app.implementations.oss import (
    LocalOCRService,
    LocalCatalogService,
    StubVendorLookup,
    StubScraperService
)

# NetBox is excluded from OSS build


class ServiceContainer:
    """
    Service container for dependency injection - OSS Version
    Only OSS implementations are available
    """

    def __init__(self):
        self.build_mode = "oss"  # OSS build always uses OSS mode

        # Cache for stateless service instances
        self._ocr_service: Optional[OCRServiceInterface] = None
        self._scraper_service: Optional[ScraperServiceInterface] = None

        logger.info(f"ServiceContainer initialized with BUILD_MODE={self.build_mode} (OSS)")

    def get_ocr_service(self) -> OCRServiceInterface:
        """
        Get OCR service implementation (cached singleton)

        Returns:
            LocalOCRService (OSS - Tesseract-based)
        """
        if self._ocr_service is not None:
            return self._ocr_service

        logger.debug("Creating LocalOCRService (OSS)")
        self._ocr_service = LocalOCRService()
        return self._ocr_service

    def get_catalog_service(self, db: Session) -> CatalogServiceInterface:
        """
        Get catalog service implementation

        Args:
            db: Database session

        Returns:
            LocalCatalogService (OSS)
        """
        logger.debug("Using LocalCatalogService (OSS)")
        return LocalCatalogService(db)

    def get_vendor_lookup(self, db: Session) -> VendorLookupInterface:
        """
        Get vendor lookup implementation

        Args:
            db: Database session

        Returns:
            StubVendorLookup (OSS)
        """
        logger.debug("Using StubVendorLookup (OSS)")
        return StubVendorLookup()

    # NetBox service is NOT available in OSS build

    def get_scraper_service(self) -> ScraperServiceInterface:
        """
        Get web scraper implementation (cached singleton)

        Returns:
            StubScraperService (OSS)
        """
        if self._scraper_service is not None:
            return self._scraper_service

        logger.debug("Creating StubScraperService (OSS)")
        self._scraper_service = StubScraperService()
        return self._scraper_service

    def is_oss_build(self) -> bool:
        """Check if running OSS build"""
        return True

    def is_premium_build(self) -> bool:
        """Check if running premium build"""
        return False


# Global container instance (singleton pattern)
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get or create the global service container

    Returns:
        ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


# FastAPI dependency injection helpers
def get_ocr_service() -> OCRServiceInterface:
    """FastAPI dependency for OCR service"""
    return get_container().get_ocr_service()


def get_catalog_service(db: Session) -> CatalogServiceInterface:
    """FastAPI dependency for catalog service"""
    return get_container().get_catalog_service(db)


def get_vendor_lookup(db: Session) -> VendorLookupInterface:
    """FastAPI dependency for vendor lookup"""
    return get_container().get_vendor_lookup(db)


# NetBox service is NOT available in OSS build


def get_scraper_service() -> ScraperServiceInterface:
    """FastAPI dependency for scraper service"""
    return get_container().get_scraper_service()
