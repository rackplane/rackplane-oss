# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Cached SKU Model

Stores SKU data fetched from the Global Catalog for offline access.
Data is cached locally to enable bunker/offline operation.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class CachedSKU(Base):
    """
    Locally cached SKU data from the Global Catalog.
    
    Enables offline operation by storing remote SKU data locally.
    Cache expires after 30 days by default.
    """
    __tablename__ = "cached_skus"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # SKU identifiers (indexed for fast lookup)
    sku = Column(String(100), index=True)
    part_number = Column(String(100), index=True)
    vendor = Column(String(50))
    
    # Product information
    name = Column(String(255))
    manufacturer = Column(String(100))
    asset_type = Column(String(50))
    specifications = Column(JSON)
    description = Column(Text)
    
    # URLs
    image_url = Column(String(500))
    datasheet_url = Column(String(500))
    vendor_url = Column(String(500))
    
    # Pricing (if available)
    price_usd = Column(String(20))  # Stored as string to preserve precision
    currency = Column(String(10), default="USD")
    
    # Cache metadata
    fetched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    source = Column(String(50))  # "rackplane_global", "fs.com", etc.
    
    # Composite index for common queries
    __table_args__ = (
        Index('ix_cached_skus_tenant_sku', 'tenant_id', 'sku'),
        Index('ix_cached_skus_tenant_part', 'tenant_id', 'part_number'),
    )
    
    # Default cache duration
    CACHE_DURATION_DAYS = 30
    
    @property
    def is_stale(self) -> bool:
        """Check if cached data has expired."""
        if not self.expires_at:
            return True
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def from_remote_sku(cls, tenant_id: int, remote_data: dict, source: str = "rackplane_global") -> "CachedSKU":
        """
        Create a CachedSKU from remote API response data.
        
        Args:
            tenant_id: The tenant ID to associate with this cache entry
            remote_data: Dictionary containing SKU data from remote API
            source: The source service (e.g., "rackplane_global")
            
        Returns:
            New CachedSKU instance (not yet persisted)
        """
        now = datetime.utcnow()
        return cls(
            tenant_id=tenant_id,
            sku=remote_data.get("sku"),
            part_number=remote_data.get("part_number"),
            vendor=remote_data.get("vendor"),
            name=remote_data.get("name"),
            manufacturer=remote_data.get("manufacturer"),
            asset_type=remote_data.get("asset_type"),
            specifications=remote_data.get("specifications"),
            description=remote_data.get("description"),
            image_url=remote_data.get("image_url"),
            datasheet_url=remote_data.get("datasheet_url"),
            vendor_url=remote_data.get("vendor_url"),
            price_usd=str(remote_data.get("price_usd")) if remote_data.get("price_usd") else None,
            currency=remote_data.get("currency", "USD"),
            fetched_at=now,
            expires_at=now + timedelta(days=cls.CACHE_DURATION_DAYS),
            source=source
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "sku": self.sku,
            "part_number": self.part_number,
            "vendor": self.vendor,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "asset_type": self.asset_type,
            "specifications": self.specifications,
            "description": self.description,
            "image_url": self.image_url,
            "datasheet_url": self.datasheet_url,
            "vendor_url": self.vendor_url,
            "price_usd": float(self.price_usd) if self.price_usd else None,
            "currency": self.currency,
            "source": self.source,
            "is_cached": True,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_stale": self.is_stale
        }
