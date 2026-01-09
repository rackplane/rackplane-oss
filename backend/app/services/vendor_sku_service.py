# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Vendor SKU Service
Handles lookup and matching of vendor SKUs for auto-populating asset fields
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.vendor_sku import VendorSKU

logger = logging.getLogger(__name__)


class VendorSKUService:
    """Service for vendor SKU catalog lookups and management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def lookup_by_sku(
        self,
        sku: str,
        vendor: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> Optional[VendorSKU]:
        """
        Look up a vendor SKU by SKU number.
        
        Args:
            sku: SKU/part number to lookup
            vendor: Optional vendor name to narrow search
            tenant_id: Tenant ID (for multi-tenant isolation)
            
        Returns:
            VendorSKU if found, None otherwise
        """
        if not sku:
            return None
        
        query = self.db.query(VendorSKU).filter(
            VendorSKU.sku.ilike(f"%{sku}%"),
            VendorSKU.is_active == True
        )
        
        if vendor:
            query = query.filter(VendorSKU.vendor.ilike(f"%{vendor}%"))
        
        if tenant_id:
            query = query.filter(VendorSKU.tenant_id == tenant_id)
        
        return query.first()
    
    def lookup_by_vendor_and_sku(
        self,
        vendor: str,
        sku: str,
        tenant_id: Optional[int] = None
    ) -> Optional[VendorSKU]:
        """
        Look up a vendor SKU by exact vendor and SKU match.
        
        Args:
            vendor: Vendor name
            sku: SKU/part number
            tenant_id: Tenant ID
            
        Returns:
            VendorSKU if found, None otherwise
        """
        if not vendor or not sku:
            return None
        
        query = self.db.query(VendorSKU).filter(
            VendorSKU.vendor.ilike(vendor),
            VendorSKU.sku.ilike(sku),
            VendorSKU.is_active == True
        )
        
        if tenant_id:
            query = query.filter(VendorSKU.tenant_id == tenant_id)
        
        return query.first()
    
    def search_skus(
        self,
        search_term: Optional[str] = None,
        vendor: Optional[str] = None,
        asset_type: Optional[str] = None,
        tenant_id: Optional[int] = None,
        limit: int = 50
    ) -> List[VendorSKU]:
        """
        Search vendor SKUs by various criteria.
        
        Args:
            search_term: Search in SKU, name, or description
            vendor: Filter by vendor
            asset_type: Filter by asset type
            tenant_id: Tenant ID
            limit: Maximum results to return
            
        Returns:
            List of matching VendorSKU objects
        """
        query = self.db.query(VendorSKU).filter(
            VendorSKU.is_active == True
        )
        
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    VendorSKU.sku.ilike(search_pattern),
                    VendorSKU.name.ilike(search_pattern),
                    VendorSKU.description.ilike(search_pattern)
                )
            )
        
        if vendor:
            query = query.filter(VendorSKU.vendor.ilike(f"%{vendor}%"))
        
        if asset_type:
            query = query.filter(VendorSKU.asset_type == asset_type)
        
        if tenant_id:
            query = query.filter(VendorSKU.tenant_id == tenant_id)
        
        return query.limit(limit).all()
    
    def match_sku_from_text(
        self,
        text: str,
        tenant_id: Optional[int] = None
    ) -> Optional[VendorSKU]:
        """
        Try to match a SKU from OCR text or other text input.
        
        This looks for SKU patterns in the text and tries to match them
        against the vendor SKU catalog.
        
        Args:
            text: Text to search (e.g., from OCR)
            tenant_id: Tenant ID
            
        Returns:
            VendorSKU if a match is found, None otherwise
        """
        if not text:
            return None
        
        # Common SKU patterns to look for
        # FS.com SKUs: Usually start with letters, contain numbers
        # NVIDIA SKUs: Usually alphanumeric
        # Try to extract potential SKUs from text
        
        # Split text into words and look for SKU-like patterns
        words = text.split()
        potential_skus = []
        
        for word in words:
            # Remove common punctuation
            cleaned = word.strip('.,;:()[]{}')
            # Look for alphanumeric strings that might be SKUs
            if len(cleaned) >= 3 and any(c.isdigit() for c in cleaned) and any(c.isalpha() for c in cleaned):
                potential_skus.append(cleaned)
        
        # Try to match each potential SKU
        for potential_sku in potential_skus:
            matched = self.lookup_by_sku(potential_sku, tenant_id=tenant_id)
            if matched:
                return matched
        
        return None
    
    def get_asset_data_from_sku(
        self,
        sku: str,
        vendor: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get asset field data from a vendor SKU.
        
        This is the main method used to auto-populate asset forms.
        
        Args:
            sku: SKU/part number
            vendor: Optional vendor name
            tenant_id: Tenant ID
            
        Returns:
            Dictionary of asset fields ready for asset creation, or None
        """
        vendor_sku = self.lookup_by_sku(sku, vendor=vendor, tenant_id=tenant_id)
        
        if not vendor_sku:
            return None
        
        return vendor_sku.to_asset_data()
    
    def get_vendors(self, tenant_id: Optional[int] = None) -> List[str]:
        """
        Get list of all vendors in the catalog.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of unique vendor names
        """
        # 1. Tenant Vendors
        query = self.db.query(VendorSKU.vendor).filter(
            VendorSKU.is_active == True
        )
        
        if tenant_id:
            query = query.filter(VendorSKU.tenant_id == tenant_id)
        
        local_vendors = {v[0] for v in query.distinct().all()}

        # 2. Global Catalog Vendors
        # Import dynamically to avoid circular dependencies
        from app.models.catalog_sku import CatalogSKU
        
        global_query = self.db.query(CatalogSKU.vendor).filter(
            CatalogSKU.is_active == True
        )
        global_vendors = {v[0] for v in global_query.distinct().all()}
        
        # Merge and Sort
        all_vendors = sorted(list(local_vendors.union(global_vendors)))
        return all_vendors

