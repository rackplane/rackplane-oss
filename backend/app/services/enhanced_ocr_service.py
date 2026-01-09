# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Enhanced OCR Service
Extends OCR service with vendor identification and automatic warranty/config lookup
"""

import logging
from typing import Dict, Optional, Any
from app.services.ocr_service import OCRService
from app.services.vendor_lookup_service import VendorLookupService, Vendor
from app.services.vendor_api_service import VendorAPIService

logger = logging.getLogger(__name__)


class EnhancedOCRService:
    """
    Enhanced OCR service that:
    1. Extracts text from images (using OCRService)
    2. Identifies vendor from extracted data
    3. Fetches warranty and configuration from vendor APIs
    4. Returns complete asset information ready for auto-population
    """
    
    def __init__(self, db=None):
        """
        Initialize enhanced OCR service
        
        Args:
            db: Optional database session (needed for RackPlane Services client)
        """
        self.ocr_service = OCRService()
        self.vendor_lookup = VendorLookupService()
        self.vendor_api = VendorAPIService()
        self.db = db
    
    async def process_image_with_vendor_lookup(
        self,
        image_data: bytes,
        auto_fetch_vendor_data: bool = True
    ) -> Dict[str, Any]:
        """
        Process image with OCR and optionally fetch vendor warranty/config data
        
        Args:
            image_data: Image bytes
            auto_fetch_vendor_data: If True, automatically fetch warranty/config from vendor API
            
        Returns:
            Dictionary with:
            {
                "raw_text": str,
                "parsed_data": dict (serial, model, manufacturer, etc.),
                "vendor": Vendor enum,
                "service_tag": str (if Dell),
                "vendor_data": dict (warranty, config, etc.),
                "confidence": str,
                "suggestions": list
            }
        """
        # Step 1: Extract text and parse basic information
        # Uses RackPlane Services API (Tesseract or Cloud OCR)
        ocr_results = await self.ocr_service.process_image(
            image_data, 
            use_cloud_ocr=True,
            db=self.db  # Pass DB session for RackPlane Services client
        )
        parsed_data = ocr_results.get("parsed_data", {})
        
        # Step 2: Extract service tag (Dell-specific)
        service_tag = self.vendor_lookup.extract_service_tag(
            ocr_results.get("raw_text", ""),
            parsed_data.get("serial_number")
        )
        
        # Step 3: Identify vendor
        vendor = self.vendor_lookup.identify_vendor(
            serial_number=parsed_data.get("serial_number"),
            service_tag=service_tag,
            model=parsed_data.get("model"),
            manufacturer=parsed_data.get("manufacturer")
        )
        
        result = {
            "raw_text": ocr_results.get("raw_text", ""),
            "parsed_data": parsed_data,
            "vendor": vendor.value if vendor != Vendor.UNKNOWN else None,
            "service_tag": service_tag,
            "vendor_data": None,
            "confidence": ocr_results.get("confidence", "none"),
            "suggestions": ocr_results.get("suggestions", [])
        }
        
        # Step 4: Fetch vendor data if requested and vendor identified
        if auto_fetch_vendor_data and vendor != Vendor.UNKNOWN:
            try:
                vendor_data = await self.vendor_api.fetch_vendor_data(
                    vendor=vendor,
                    serial_number=parsed_data.get("serial_number"),
                    service_tag=service_tag,
                    model=parsed_data.get("model")
                )
                result["vendor_data"] = vendor_data
                
                # Add vendor data to suggestions
                if vendor_data and not vendor_data.get("error"):
                    result["suggestions"].append(f"✓ Vendor data fetched from {vendor.value}")
                    if vendor_data.get("warranty_end_date"):
                        result["suggestions"].append(
                            f"Warranty expires: {vendor_data['warranty_end_date']}"
                        )
                elif vendor_data and vendor_data.get("error"):
                    result["suggestions"].append(
                        f"⚠ Could not fetch vendor data: {vendor_data['error']}"
                    )
            except Exception as e:
                logger.error(f"Error fetching vendor data: {e}")
                result["vendor_data"] = {"error": str(e)}
                result["suggestions"].append(f"⚠ Error fetching vendor data: {str(e)}")
        
        return result
    
    def merge_vendor_data_into_asset(
        self,
        ocr_result: Dict[str, Any],
        asset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge vendor data from OCR result into asset data for auto-population
        
        Args:
            ocr_result: Result from process_image_with_vendor_lookup
            asset_data: Existing asset data dictionary
            
        Returns:
            Updated asset_data with vendor information merged in
        """
        # Start with existing asset data
        merged = asset_data.copy()
        
        # Merge parsed OCR data (if not already set)
        parsed_data = ocr_result.get("parsed_data", {})
        if parsed_data.get("serial_number") and not merged.get("serial_number"):
            merged["serial_number"] = parsed_data["serial_number"]
        if parsed_data.get("model") and not merged.get("model"):
            merged["model"] = parsed_data["model"]
        if parsed_data.get("manufacturer") and not merged.get("manufacturer"):
            merged["manufacturer"] = parsed_data["manufacturer"]
        if parsed_data.get("asset_tag") and not merged.get("asset_tag"):
            merged["asset_tag"] = parsed_data["asset_tag"]
        if parsed_data.get("sku") and not merged.get("sku"):
            merged["sku"] = parsed_data["sku"]
        
        # Merge vendor data (warranty, configuration)
        vendor_data = ocr_result.get("vendor_data")
        if vendor_data and not vendor_data.get("error"):
            # Warranty dates
            if vendor_data.get("warranty_start_date") and not merged.get("warranty_start_date"):
                merged["warranty_start_date"] = vendor_data["warranty_start_date"]
            if vendor_data.get("warranty_end_date") and not merged.get("warranty_end_date"):
                merged["warranty_end_date"] = vendor_data["warranty_end_date"]
            
            # Model (if vendor API provides more accurate model)
            if vendor_data.get("model") and not merged.get("model"):
                merged["model"] = vendor_data["model"]
            
            # Manufacturer (if vendor API provides it)
            if vendor_data.get("manufacturer") and not merged.get("manufacturer"):
                merged["manufacturer"] = vendor_data["manufacturer"]
            
            # Configuration details (store in custom_fields or notes)
            if vendor_data.get("configuration"):
                if "custom_fields" not in merged:
                    merged["custom_fields"] = {}
                merged["custom_fields"]["vendor_config"] = vendor_data["configuration"]
        
        return merged

