"""
OSS Web Scraping Service Implementation
Stub implementation (web scraping is a premium feature)
"""
import logging
from typing import Dict, Any

from app.abstractions.scraping import ScraperServiceInterface

logger = logging.getLogger(__name__)


class StubScraperService(ScraperServiceInterface):
    """Stub implementation for web scraping (premium feature)"""

    async def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Web scraping not available in OSS

        Args:
            url: URL to scrape

        Raises:
            NotImplementedError: Always raised in OSS builds
        """
        logger.info(
            f"Web scraping requested for '{url}' but not available in OSS build. "
            "This feature requires RackPlane Premium."
        )
        raise NotImplementedError(
            "Web scraping requires RackPlane Premium subscription. "
            "OSS version does not include web scraping capabilities. "
            "Upgrade to Premium at https://rackplane.com/pricing to enable this feature."
        )

    def is_available(self) -> bool:
        """
        Check if scraping service is available

        Returns:
            False (not available in OSS)
        """
        return False

    def get_service_name(self) -> str:
        return "Web Scraper (Unavailable in OSS)"
