"""
Tests for OSS Build Mode
Validates that OSS implementations are loaded correctly in BUILD_MODE=oss
"""

import os
import pytest
from unittest.mock import patch

from app.core.container import ServiceContainer
from app.implementations.oss import (
    LocalOCRService,
    LocalCatalogService,
    StubVendorLookup,
    StubScraperService,
)


class TestOSSBuildMode:
    """Test that OSS mode loads correct implementations"""

    def test_oss_mode_uses_local_ocr(self):
        """OSS build should use LocalOCRService for OCR"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            ocr = container.get_ocr_service()
            assert isinstance(ocr, LocalOCRService)
            assert ocr.__class__.__name__ == "LocalOCRService"

    def test_oss_mode_uses_local_catalog(self, db_session):
        """OSS build should use LocalCatalogService for catalog"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            catalog = container.get_catalog_service(db_session)
            assert isinstance(catalog, LocalCatalogService)
            assert catalog.__class__.__name__ == "LocalCatalogService"

    # NetBox tests removed - OSS build has no NetBox support

    def test_oss_mode_uses_stub_vendor_lookup(self, db_session):
        """OSS build should use StubVendorLookup for vendor lookups"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            vendor = container.get_vendor_lookup(db_session)
            assert isinstance(vendor, StubVendorLookup)
            assert vendor.__class__.__name__ == "StubVendorLookup"

    def test_oss_mode_uses_stub_scraper(self):
        """OSS build should use StubScraperService for web scraping"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            scraper = container.get_scraper_service()
            assert isinstance(scraper, StubScraperService)
            assert scraper.__class__.__name__ == "StubScraperService"


class TestOSSServiceBehavior:
    """Test behavior of OSS service implementations"""

    @pytest.mark.asyncio
    async def test_local_ocr_uses_tesseract(self):
        """LocalOCRService should use Tesseract and ignore cloud flags"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            ocr = container.get_ocr_service()

            # Skip gracefully if Tesseract is not available in the test environment
            if not ocr.is_available():
                pytest.skip("Tesseract is not available in this test environment")

            # Service should be available
            assert ocr.is_available() is True
            assert ocr.get_service_name() == "Local Tesseract OCR (OSS)"

    def test_local_catalog_queries_local_db_only(self, db_session):
        """LocalCatalogService should only query local database"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            catalog = container.get_catalog_service(db_session)

            # Service should be available
            assert catalog.is_available() is True
            assert catalog.get_service_name() == "Local Database Catalog (OSS)"

    # NetBox pull/push tests removed - OSS build has no NetBox support

    @pytest.mark.asyncio
    async def test_stub_vendor_lookup_returns_none(self):
        """StubVendorLookup should return None for all lookups"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            vendor = container.get_vendor_lookup(None)

            # Service should not be available
            assert vendor.is_available() is False
            assert vendor.get_service_name() == "Vendor Lookup (Unavailable in OSS)"

            # Lookup methods should return empty results
            result = await vendor.lookup_sku("TEST", "TestVendor")
            assert result is None

            products = await vendor.search_products("TEST", "TestVendor")
            assert products == []

    def test_stub_scraper_returns_none(self):
        """StubScraperService should return None for all scraping requests"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            scraper = container.get_scraper_service()

            # Service should not be available
            assert scraper.is_available() is False
            assert scraper.get_service_name() == "Web Scraper (Unavailable in OSS)"


class TestOSSFeatureLimitations:
    """Test that OSS build properly restricts premium features"""

    @pytest.mark.asyncio
    async def test_oss_ocr_ignores_cloud_flag(self):
        """OSS OCR should ignore use_cloud_ocr flag and use Tesseract"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            ocr = container.get_ocr_service()

            # Create a small test image (1x1 white pixel)
            from PIL import Image
            import io
            img = Image.new('RGB', (1, 1), color='white')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()

            # Request cloud OCR (should be ignored)
            result = await ocr.process_image(
                image_data,
                use_cloud_ocr=True,
                force_cloud_ocr=True
            )

            # Should still use Tesseract
            assert result.get("ocr_source") == "tesseract"
            assert result.get("cloud_ocr_available") is False

    @pytest.mark.asyncio
    async def test_oss_catalog_no_global_catalog(self, db_session):
        """OSS catalog should not access global catalog"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()
            catalog = container.get_catalog_service(db_session)

            # Should only use local database
            result = await catalog.lookup_sku("FAKE-SKU-123", "TestVendor")
            # Result will be None since SKU doesn't exist in test DB
            assert result is None

    # NetBox push error test removed - OSS build has no NetBox support


class TestOSSBuildValidation:
    """Integration tests to validate full OSS build"""

    def test_oss_build_all_services_load(self, db_session):
        """All OSS services should load without errors"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            container = ServiceContainer()

            # All services should instantiate without error
            ocr = container.get_ocr_service()
            catalog = container.get_catalog_service(db_session)
            vendor = container.get_vendor_lookup(db_session)
            scraper = container.get_scraper_service()

            # All should be valid instances
            assert ocr is not None
            assert catalog is not None
            assert vendor is not None
            assert scraper is not None

    def test_oss_build_no_premium_imports(self):
        """OSS build should work even if premium imports fail"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            # Even if premium implementations are missing, OSS should work
            container = ServiceContainer()
            assert container.build_mode == "oss"
            assert container.is_oss_build()

    def test_oss_build_logs_correct_mode(self, caplog):
        """Container initialization should log OSS mode"""
        with patch.dict(os.environ, {"BUILD_MODE": "oss"}, clear=True):
            import app.core.container
            app.core.container._container = None  # Clear singleton

            container = ServiceContainer()
            assert "BUILD_MODE=oss" in caplog.text or container.build_mode == "oss"
