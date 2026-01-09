"""
OSS Vendor Lookup Service Implementation
Stub implementation (vendor API lookups are premium features)
"""
import logging
from typing import Dict, Any, Optional, List

from app.abstractions.vendor_lookup import VendorLookupInterface

logger = logging.getLogger(__name__)


class StubVendorLookup(VendorLookupInterface):
    """Stub implementation for vendor lookup (premium feature)"""

    async def lookup_sku(
        self,
        sku: str,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Vendor API lookup not available in OSS

        Args:
            sku: SKU to look up
            vendor: Vendor name

        Returns:
            None (feature not available in OSS)
        """
        logger.info(
            f"Vendor API lookup requested for SKU '{sku}' but not available in OSS build. "
            "This feature requires RackPlane Premium."
        )
        return None

    async def search_products(
        self,
        query: str,
        vendor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Vendor API search not available in OSS

        Args:
            query: Search query
            vendor: Vendor to search

        Returns:
            Empty list (feature not available in OSS)
        """
        logger.info(
            f"Vendor API search requested for '{query}' but not available in OSS build. "
            "This feature requires RackPlane Premium."
        )
        return []

    def is_available(self) -> bool:
        """
        Check if vendor lookup is available

        Returns:
            False (not available in OSS)
        """
        return False

    def get_service_name(self) -> str:
        return "Vendor Lookup (Unavailable in OSS)"
