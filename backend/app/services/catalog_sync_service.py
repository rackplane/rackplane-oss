# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog Sync Service
Handles synchronization of catalog data to the central RackPlane server.
"""

import logging
import requests
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class CatalogSyncService:
    @staticmethod
    def push_to_central(submission_data: Dict[str, Any], api_key: str = None, sync_secret: str = None) -> tuple[Optional[str], Optional[str]]:
        """
        Push approved submission data to the Central Catalog.
        
        Args:
            submission_data: Dictionary containing SKU data (vendor, sku, name, etc.)
            api_key: Optional API key.
            sync_secret: Optional restricted sync secret.
            
        Returns:
            tuple: (source_id, error_message)
        """
        # Use provided api_key, or fall back to settings
        effective_api_key = api_key or settings.RACKPLANE_SERVICES_API_KEY
        
        # Extract vendor/sku early for logging context
        vendor = submission_data.get("vendor")
        sku = submission_data.get("sku")
        
        if not effective_api_key and not sync_secret:
            logger.warning(
                f"Skipping catalog sync: No API key or secret available "
                f"(vendor={vendor}, sku={sku})"
            )
            return None, "No API key or secret available"

        # Prepare payload
        payload = {
            "vendor": vendor,
            "sku": sku,
            "name": submission_data.get("name"),
            "manufacturer": submission_data.get("manufacturer"),
            "part_number": submission_data.get("part_number"),
            "asset_type": submission_data.get("asset_type"),
            "description": submission_data.get("description"),
            "price_usd": submission_data.get("price_usd"),
            "currency": submission_data.get("currency", "USD"),
            "specifications": submission_data.get("specifications"),
            "datasheet_url": submission_data.get("datasheet_url"),
            "vendor_url": submission_data.get("vendor_url"),
            "image_url": submission_data.get("image_url"),
            "tenant_uuid": submission_data.get("tenant_uuid"),  # For credit tracking
        }
        
        url = f"{settings.RACKPLANE_SERVICES_URL}/provision/catalog-sku"
        headers = {
            "Content-Type": "application/json"
        }
        
        if sync_secret:
            headers["X-Sync-Secret"] = sync_secret
        if effective_api_key:
            headers["X-API-Key"] = effective_api_key
        
        try:
            logger.info(f"Syncing to URL: {url} (vendor={vendor}, sku={sku})")
            response = requests.post(url, json=payload, headers=headers, timeout=10.0)
            
            if response.status_code in (200, 201):
                data = response.json()
                source_id = data.get("source_id")
                logger.info(f"Successfully synced {vendor}/{sku} to central catalog. Source ID: {source_id}")
                return source_id, None
                
            elif response.status_code == 409:
                logger.warning(f"Catalog sync conflict (409): {vendor}/{sku} already exists in central catalog")
                return None, "Conflict: Item already exists in central catalog"
            
            elif response.status_code == 401:
                logger.error(
                    f"Catalog sync auth failed (401) for {vendor}/{sku}. "
                    f"Check API key/secret validity."
                )
                return None, "Authentication failed: Invalid or expired API key/secret"
                
            else:
                error_detail = response.text[:500]  # Truncate for logging
                try:
                    error_detail = response.json().get("detail", error_detail)
                except:
                    pass
                logger.error(
                    f"Catalog sync failed for {vendor}/{sku}: "
                    f"status={response.status_code}, detail={error_detail}"
                )
                return None, f"Server error ({response.status_code}): {error_detail}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Catalog sync network error for {vendor}/{sku}: {str(e)}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during catalog sync for {vendor}/{sku}: {str(e)}")
            return None, f"Unexpected error: {str(e)}"
