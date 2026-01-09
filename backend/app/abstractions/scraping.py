"""
Abstract Web Scraping Service Interface
Defines the contract for web scraping services
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class ScraperServiceInterface(ABC):
    """Abstract interface for web scraping services"""

    @abstractmethod
    async def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Scrape product data from a URL

        Args:
            url: Product page URL

        Returns:
            Dict containing scraped data:
                - title: Product title
                - description: Product description
                - price: Price (if found)
                - images: List of image URLs
                - specifications: Dict of product specs
                - raw_html: Raw HTML (optional)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if scraping service is available

        Returns:
            True if service is configured and ready
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of the scraping service implementation

        Returns:
            Service name
        """
        return self.__class__.__name__
