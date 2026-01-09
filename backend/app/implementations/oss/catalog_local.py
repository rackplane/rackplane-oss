"""
OSS Catalog Service Implementation
Uses local database catalog only (no global RackPlane Services catalog)
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.abstractions.catalog import CatalogServiceInterface
from app.models.catalog_sku import CatalogSKU

logger = logging.getLogger(__name__)


class LocalCatalogService(CatalogServiceInterface):
    """OSS implementation using local database catalog only"""

    def __init__(self, db: Session):
        self.db = db

    async def lookup_sku(
        self,
        sku: str,
        vendor: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Lookup SKU in local database only"""
        try:
            query = self.db.query(CatalogSKU).filter(
                (CatalogSKU.sku == sku) | (CatalogSKU.part_number == sku)
            )

            if vendor:
                query = query.filter(CatalogSKU.vendor.ilike(f"%{vendor}%"))

            result = query.first()

            if result:
                return {
                    "sku": result.sku,
                    "part_number": result.part_number,
                    "vendor": result.vendor,
                    "manufacturer": result.manufacturer,
                    "name": result.name,
                    "description": result.description,
                    "price": result.price_usd,
                    "currency": result.currency,
                    "asset_type": result.asset_type,
                    "specifications": result.specifications,
                    "datasheet_url": result.datasheet_url,
                    "vendor_url": result.vendor_url,
                    "source": "local",  # Indicate local database
                }

            return None

        except Exception as e:
            logger.error(f"Local catalog lookup failed: {e}")
            return None

    async def search_catalog(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search local catalog"""
        try:
            q = self.db.query(CatalogSKU).filter(
                (CatalogSKU.sku.ilike(f"%{query}%")) |
                (CatalogSKU.part_number.ilike(f"%{query}%")) |
                (CatalogSKU.name.ilike(f"%{query}%")) |
                (CatalogSKU.description.ilike(f"%{query}%"))
            )

            if filters:
                if "vendor" in filters:
                    q = q.filter(CatalogSKU.vendor.ilike(f"%{filters['vendor']}%"))

                if "asset_type" in filters:
                    q = q.filter(CatalogSKU.asset_type == filters["asset_type"])

                if "min_price" in filters:
                    q = q.filter(CatalogSKU.price_usd >= filters["min_price"])

                if "max_price" in filters:
                    q = q.filter(CatalogSKU.price_usd <= filters["max_price"])

            results = q.limit(50).all()

            return [
                {
                    "sku": r.sku,
                    "part_number": r.part_number,
                    "vendor": r.vendor,
                    "manufacturer": r.manufacturer,
                    "name": r.name,
                    "description": r.description,
                    "price": r.price_usd,
                    "currency": r.currency,
                    "asset_type": r.asset_type,
                    "source": "local",
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Local catalog search failed: {e}")
            return []

    def is_available(self) -> bool:
        """Local catalog is always available"""
        return True

    def get_service_name(self) -> str:
        return "Local Database Catalog (OSS)"
