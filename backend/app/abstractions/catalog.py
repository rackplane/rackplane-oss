"""
Abstract Catalog Service Interface
Defines the contract for catalog/SKU lookup services (local DB or global catalog)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class CatalogServiceInterface(ABC):
    """Abstract interface for catalog/SKU services"""

    @abstractmethod
    async def lookup_sku(
        self,
        sku: str,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup a SKU in the catalog

        Args:
            sku: SKU/part number to look up
            vendor: Optional vendor name to filter by

        Returns:
            Dict containing SKU information or None if not found:
                - sku: The SKU/part number
                - vendor: Vendor name
                - name: Product name
                - description: Product description
                - price: Price (if available)
                - source: Source of data (local/global)
        """
        pass

    @abstractmethod
    async def search_catalog(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the catalog by query string

        Args:
            query: Search query (SKU, name, description)
            filters: Optional filters:
                - vendor: Filter by vendor
                - asset_type: Filter by asset type
                - min_price, max_price: Price range

        Returns:
            List of matching SKU dictionaries
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the catalog service is available

        Returns:
            True if service is ready to use, False otherwise
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of the catalog service implementation

        Returns:
            Service name (e.g., "Local Catalog", "Global Catalog")
        """
        return self.__class__.__name__
