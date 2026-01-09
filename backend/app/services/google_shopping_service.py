"""
Google Shopping Price Search Service

Uses ZenRows to scrape Google Shopping for product pricing.
Aggregates prices from multiple retailers in a single search.

Usage:
    service = GoogleShoppingService()
    results = service.search_prices("NVIDIA MSN4700-WS2F")
    lowest = service.get_lowest_price("MCP4Y10-N001")
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
try:
    from app.services.zenrows_service import ZenRowsService
except ImportError:
    # Fallback/Mock for OSS
    class ZenRowsService:
        def __init__(self, *args, **kwargs):
            pass
        @property
        def is_configured(self):
            return False
        def scrape_google_shopping(self, *args, **kwargs):
            return []
import logging

logger = logging.getLogger(__name__)


class PriceResult(BaseModel):
    """A price result from a shopping search."""
    product_name: str
    price_usd: Optional[float]
    price_text: str
    vendor: Optional[str]
    url: Optional[str]
    source: str = "google_shopping"
    fetched_at: datetime = None
    
    def __init__(self, **data):
        if data.get('fetched_at') is None:
            data['fetched_at'] = datetime.utcnow()
        super().__init__(**data)


class PriceSearchResult(BaseModel):
    """Complete result from a price search."""
    query: str
    results: List[PriceResult]
    lowest_price: Optional[float]
    lowest_vendor: Optional[str]
    fetched_at: datetime = None
    
    def __init__(self, **data):
        if data.get('fetched_at') is None:
            data['fetched_at'] = datetime.utcnow()
        super().__init__(**data)


class GoogleShoppingService:
    """
    Service for searching product prices via Google Shopping.
    
    Uses ZenRows to bypass anti-bot measures on Google.
    
    Usage:
        service = GoogleShoppingService()
        
        # Search for prices
        result = service.search_prices("NVIDIA MSN4700-WS2F switch")
        for item in result.results:
            print(f"{item.vendor}: ${item.price_usd}")
        
        # Get lowest price
        lowest = service.get_lowest_price("MCP4Y10-N001")
        if lowest:
            print(f"Lowest: ${lowest.price_usd} from {lowest.vendor}")
    """
    
    def __init__(self, zenrows_service: Optional[ZenRowsService] = None):
        self.zenrows = zenrows_service or ZenRowsService()
    
    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self.zenrows.is_configured
    
    def search_prices(
        self,
        query: str,
        max_results: int = 10
    ) -> PriceSearchResult:
        """
        Search Google Shopping for product prices.
        
        Args:
            query: Product name or part number to search
            max_results: Maximum number of results
            
        Returns:
            PriceSearchResult with list of prices and lowest price
        """
        if not self.is_configured:
            logger.warning("GoogleShoppingService not configured (missing ZENROWS_API_KEY)")
            return PriceSearchResult(
                query=query,
                results=[],
                lowest_price=None,
                lowest_vendor=None
            )
        
        # Get results from ZenRows
        raw_results = self.zenrows.scrape_google_shopping(query, max_results)
        
        # Convert to PriceResult objects
        results = []
        for item in raw_results:
            results.append(PriceResult(
                product_name=item.get("name", "Unknown"),
                price_usd=item.get("price_usd"),
                price_text=item.get("price_text", ""),
                vendor=item.get("vendor"),
                url=item.get("url")
            ))
        
        # Find lowest price
        lowest_price = None
        lowest_vendor = None
        for r in results:
            if r.price_usd is not None:
                if lowest_price is None or r.price_usd < lowest_price:
                    lowest_price = r.price_usd
                    lowest_vendor = r.vendor
        
        return PriceSearchResult(
            query=query,
            results=results,
            lowest_price=lowest_price,
            lowest_vendor=lowest_vendor
        )
    
    def get_lowest_price(
        self,
        part_number: str,
        manufacturer: Optional[str] = None
    ) -> Optional[PriceResult]:
        """
        Get the lowest price for a specific part number.
        
        Args:
            part_number: Manufacturer part number (e.g., "MSN4700-WS2F")
            manufacturer: Optional manufacturer to append to search
            
        Returns:
            PriceResult with lowest price, or None if not found
        """
        # Build search query
        query = part_number
        if manufacturer:
            query = f"{manufacturer} {part_number}"
        
        result = self.search_prices(query, max_results=10)
        
        if not result.results:
            return None
        
        # Find result with lowest price
        lowest = None
        for r in result.results:
            if r.price_usd is not None:
                if lowest is None or r.price_usd < lowest.price_usd:
                    lowest = r
        
        return lowest
    
    def get_price_range(
        self,
        part_number: str
    ) -> Dict[str, Any]:
        """
        Get price range (min, max, avg) for a part number.
        
        Returns:
            Dict with min, max, avg prices and result count
        """
        result = self.search_prices(part_number, max_results=20)
        
        prices = [r.price_usd for r in result.results if r.price_usd is not None]
        
        if not prices:
            return {
                "part_number": part_number,
                "min_price": None,
                "max_price": None,
                "avg_price": None,
                "result_count": 0
            }
        
        return {
            "part_number": part_number,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "result_count": len(prices)
        }
