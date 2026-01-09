# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog Service
Central service for managing the Global Product Catalog.
Handles fetching, caching, and searching products across all vendors (FS.com, etc.).
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from datetime import datetime, timedelta

from app.models.catalog_sku import CatalogSKU
try:
    from app.models.fs_api_usage import FSApiUsage
except ImportError:
    FSApiUsage = None
from app.services.product_parser import ProductParserService
import logging

logger = logging.getLogger(__name__)

class CatalogService:
    """
    Service for interacting with the Global Product Catalog.
    """
    
    @staticmethod
    def get_product(db: Session, vendor: str, vendor_product_id: str) -> Optional[CatalogSKU]:
        """
        Retrieve a product from the global catalog.
        
        Args:
            db: Database session
            vendor: Vendor name (e.g., "FS.com", "DigiKey")
            vendor_product_id: Vendor's unique product ID/SKU
            
        Returns:
            CatalogSKU object or None
        """
        return db.query(CatalogSKU).filter(
            CatalogSKU.vendor == vendor,
            CatalogSKU.sku == vendor_product_id
        ).first()

    @staticmethod
    def upsert_product(
        db: Session, 
        vendor: str, 
        vendor_product_id: str, 
        name: str, 
        raw_data: Dict[str, Any],
        manufacturer: str = None,
        part_number: str = None,
        price_usd: float = None,
        currency: str = "USD",
        url: str = None,
        vertical: str = None
    ) -> CatalogSKU:
        """
        Create or update a product in the global catalog (CatalogSKU).
        
        Args:
            db: Database session
            vendor: Vendor name
            vendor_product_id: Vendor SKU
            name: Product name
            raw_data: Full JSON response from vendor API
            manufacturer: Manufacturer name (optional)
            part_number: MPN (optional)
            price_usd: Price (optional)
            currency: Currency code (default USD)
            url: Product URL (optional)
            vertical: Industry vertical (optional)
            
        Returns:
            Updated CatalogSKU object
        """
        # Parse attributes for asset classification
        attributes = ProductParserService.parse_product_name(name)
        
        # Check for existing
        product = CatalogService.get_product(db, vendor, vendor_product_id)
        
        if not product:
            product = CatalogSKU(
                vendor=vendor,
                sku=vendor_product_id,
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.add(product)
        
        # Update fields
        product.name = name
        product.manufacturer = manufacturer or vendor
        product.part_number = part_number
        
        # Extracted attributes mapping
        product.asset_type = attributes.get('category')
        
        # Store full specs in specifications JSON
        # Include parsed attributes and any other useful info
        specs = attributes.copy()
        specs['raw_category'] = attributes.get('category')
        specs['url'] = url
        product.specifications = specs
        
        # Pricing
        product.price_usd = price_usd
        product.currency = currency
        
        # URLs
        product.vendor_url = url
        
        # Vertical: None = no change, empty string = clear, truthy = set
        # Note: We use `is not None` to allow explicitly clearing the vertical
        if vertical is not None:
            product.vertical = vertical if vertical else None
        
        product.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(product)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to upsert product {vendor}:{vendor_product_id}: {e}")
            raise
        
        # Push to services.rackplane.com (bi-directional sync)
        # Do this in background to not block the main operation
        try:
            CatalogService._push_sku_to_services(db, product)
        except Exception as e:
            # Don't fail the upsert if push fails - just log it
            logger.warning(f"Failed to push SKU to services.rackplane.com: {e}")
            
        return product
    
    @staticmethod
    def _push_sku_to_services(db: Session, sku: CatalogSKU) -> bool:
        """
        Push a catalog SKU to services.rackplane.com (bi-directional sync).
        
        This is called automatically after upsert_product to sync local changes
        to the central services database.
        
        Args:
            db: Database session (needed for tenant lookup)
            sku: CatalogSKU object to push
            
        Returns:
            True if push succeeded, False otherwise
        """
        try:
            try:
                from app.bridges.rackplane_services import RackPlaneServicesClient
            except ImportError:
                logger.debug("RackPlaneServicesClient not available (OSS build)")
                return False
            
            # Create client (needs db for tenant lookup)
            client = RackPlaneServicesClient(db)
            
            # Convert SKU to dict for API
            sku_data = {
                "vendor": sku.vendor,
                "sku": sku.sku,
                "part_number": sku.part_number,
                "name": sku.name,
                "manufacturer": sku.manufacturer,
                "asset_type": sku.asset_type,
                "specifications": sku.specifications,
                "price_usd": sku.price_usd,
                "currency": sku.currency or "USD",
                "compatibility": sku.compatibility,
                "description": sku.description,
                "datasheet_url": sku.datasheet_url,
                "vendor_url": sku.vendor_url,
                "image_url": sku.image_url,
                "vertical": sku.vertical or "datacenter",
                "is_active": sku.is_active
            }
            
            # Push to services (synchronous call)
            return client.push_catalog_sku(sku_data)
        except Exception as e:
            logger.warning(f"Error pushing SKU to services: {e}")
            return False

    @staticmethod
    def search_catalog(db: Session, query: str, vendor: str = None, vertical: str = None, limit: int = 50, offset: int = 0) -> List[CatalogSKU]:
        """
        Search the global catalog.
        
        Args:
            db: Database session
            query: Search string
            vendor: Optional filter by vendor
            vertical: Optional filter by vertical (datacenter, healthcare, warehouse)
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of matching CatalogSKU products
        """
        from sqlalchemy import cast, String
        q = db.query(CatalogSKU)
        
        if vertical:
            q = q.filter(CatalogSKU.vertical == vertical)
        
        if vendor:
            q = q.filter(CatalogSKU.vendor == vendor)
            
        if query:
            search = f"%{query}%"
            # Cast specs to string for text search
            specs_as_text = cast(CatalogSKU.specifications, String)
            
            q = q.filter(or_(
                CatalogSKU.name.ilike(search),
                CatalogSKU.part_number.ilike(search),
                CatalogSKU.sku.ilike(search),
                CatalogSKU.manufacturer.ilike(search),
                CatalogSKU.description.ilike(search),
                CatalogSKU.asset_type.ilike(search),
                specs_as_text.ilike(search)
            ))
            
        return q.offset(offset).limit(limit).all()

    @staticmethod
    def prune_api_usage(db: Session, days: int = 30):
        """
        Cleanup old API usage logs.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        try:
            deleted = db.query(FSApiUsage).filter(FSApiUsage.created_at < cutoff).delete()
            db.commit()
            logger.info(f"Pruned {deleted} old API usage records.")
        except Exception as e:
            logger.error(f"Failed to prune API usage: {e}")
            db.rollback()
