"""
SerpApi Google Shopping Service

Uses SerpApi to search Google Shopping and get structured JSON results.
This is more reliable than scraping because SerpApi maintains the parser.

Pricing: ~$0.015 per search (varies by plan)

Usage:
    service = SerpApiService()
    results = service.search_google_shopping("NVIDIA MSN4700-WS2F")
"""

import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ShoppingResult(BaseModel):
    """A product result from Google Shopping via SerpApi."""
    title: str
    price: Optional[float] = None
    price_raw: Optional[str] = None
    source: Optional[str] = None  # Vendor/retailer name
    link: Optional[str] = None
    product_id: Optional[str] = None
    thumbnail: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    extensions: Optional[List[str]] = None  # e.g., ["Free shipping"]


class ShoppingSearchResult(BaseModel):
    """Complete result from a SerpApi Google Shopping search."""
    query: str
    results: List[ShoppingResult]
    total_results: Optional[int] = None
    lowest_price: Optional[float] = None
    lowest_source: Optional[str] = None
    fetched_at: datetime = None
    
    def __init__(self, **data):
        if data.get('fetched_at') is None:
            data['fetched_at'] = datetime.utcnow()
        super().__init__(**data)


class SerpApiService:
    """
    Service for searching Google Shopping via SerpApi.
    
    SerpApi returns structured JSON, so no HTML parsing needed.
    They maintain the parser as Google changes their site.
    
    Usage:
        service = SerpApiService()
        
        # Search Google Shopping
        result = service.search_google_shopping("NVIDIA MSN4700-WS2F")
        for item in result.results:
            print(f"{item.source}: ${item.price}")
        
        # Get lowest price
        print(f"Lowest: ${result.lowest_price} from {result.lowest_source}")
    """
    
    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        self.base_url = settings.SERPAPI_BASE_URL
        self.session = requests.Session()
    
    @property
    def is_configured(self) -> bool:
        """Check if SerpApi is configured."""
        return bool(self.api_key)
    
    def search_google_shopping(
        self,
        query: str,
        location: str = "United States",
        num_results: int = 20
    ) -> ShoppingSearchResult:
        """
        Search Google Shopping via SerpApi.
        
        Args:
            query: Product name or part number to search
            location: Geographic location for pricing
            num_results: Max results to return
            
        Returns:
            ShoppingSearchResult with structured product data
        """
        if not self.is_configured:
            logger.warning("SerpApiService not configured (missing SERPAPI_API_KEY)")
            return ShoppingSearchResult(
                query=query,
                results=[],
                lowest_price=None,
                lowest_source=None
            )
        
        params = {
            "engine": "google_shopping",
            "q": query,
            "location": location,
            "api_key": self.api_key,
            "num": num_results
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Parse shopping results
            results = []
            shopping_results = data.get("shopping_results", [])
            
            for item in shopping_results:
                # Parse price - SerpApi returns "extracted_price" as float
                price = item.get("extracted_price")
                
                result = ShoppingResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    price_raw=item.get("price"),
                    source=item.get("source"),
                    link=item.get("link"),
                    product_id=item.get("product_id"),
                    thumbnail=item.get("thumbnail"),
                    rating=item.get("rating"),
                    reviews=item.get("reviews"),
                    extensions=item.get("extensions")
                )
                results.append(result)
            
            # Find lowest price
            lowest_price = None
            lowest_source = None
            for r in results:
                if r.price is not None:
                    if lowest_price is None or r.price < lowest_price:
                        lowest_price = r.price
                        lowest_source = r.source
            
            return ShoppingSearchResult(
                query=query,
                results=results,
                total_results=data.get("search_information", {}).get("total_results"),
                lowest_price=lowest_price,
                lowest_source=lowest_source
            )
            
        except requests.RequestException as e:
            logger.error(f"SerpApi request failed: {e}")
            return ShoppingSearchResult(
                query=query,
                results=[],
                lowest_price=None,
                lowest_source=None
            )
    
    def get_lowest_price(
        self,
        part_number: str,
        manufacturer: Optional[str] = None
    ) -> Optional[ShoppingResult]:
        """
        Get the lowest price for a specific part number.
        
        Args:
            part_number: Manufacturer part number
            manufacturer: Optional manufacturer name to add to query
            
        Returns:
            ShoppingResult with lowest price, or None
        """
        query = part_number
        if manufacturer:
            query = f"{manufacturer} {part_number}"
        
        result = self.search_google_shopping(query, num_results=10)
        
        if not result.results:
            return None
        
        # Find result with lowest price
        lowest = None
        for r in result.results:
            if r.price is not None:
                if lowest is None or r.price < lowest.price:
                    lowest = r
        
        return lowest
    
    def get_price_range(
        self,
        part_number: str,
        manufacturer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get price range (min, max, avg) for a part number.
        
        Returns:
            Dict with min, max, avg prices and result count
        """
        query = part_number
        if manufacturer:
            query = f"{manufacturer} {part_number}"
        
        result = self.search_google_shopping(query, num_results=20)
        
        prices = [r.price for r in result.results if r.price is not None]
        
        if not prices:
            return {
                "part_number": part_number,
                "min_price": None,
                "max_price": None,
                "avg_price": None,
                "result_count": 0,
                "sources": []
            }
        
        sources = list(set(r.source for r in result.results if r.source))
        
        return {
            "part_number": part_number,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "result_count": len(prices),
            "sources": sources
        }
