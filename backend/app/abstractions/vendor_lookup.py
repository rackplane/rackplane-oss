"""
Abstract Vendor Lookup Service Interface
Defines the contract for vendor data lookup services
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class VendorLookupInterface(ABC):
    """Abstract interface for vendor data lookup"""

    @abstractmethod
    async def lookup_sku(
        self,
        sku: str,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup SKU information from vendor APIs

        Args:
            sku: SKU/part number
            vendor: Vendor name (Mouser, FS.com, etc.) or None for auto-detect

        Returns:
            Dict containing vendor SKU information or None:
                - sku: The SKU
                - vendor: Vendor name
                - name: Product name
                - description: Description
                - price: Current price
                - stock: Stock availability
                - datasheet_url: URL to datasheet
        """
        pass

    @abstractmethod
    async def search_products(
        self,
        query: str,
        vendor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vendor catalogs for products

        Args:
            query: Search query
            vendor: Specific vendor to search or None for all

        Returns:
            List of matching products
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if vendor lookup service is available

        Returns:
            True if service is configured and ready
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of the vendor lookup service implementation

        Returns:
            Service name
        """
        return self.__class__.__name__
