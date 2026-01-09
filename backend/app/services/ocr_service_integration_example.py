# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Example: How to integrate RackPlane Services Client into OCR Service

This shows how to modify the existing OCRService to use the boring API client
instead of direct cloud OCR calls. The hard work happens on YOUR servers.
"""

# ============================================================================
# BEFORE: Direct cloud OCR calls (complex, requires credentials)
# ============================================================================

# OLD CODE (in ocr_service.py):
"""
async def process_image(self, image_data: bytes, use_cloud_ocr: bool = False, force_cloud_ocr: bool = False):
    # ... Tesseract code ...
    
    if use_cloud_ocr:
        try:
            from app.services.cloud_ocr_service import CloudOCRService
            cloud_ocr = CloudOCRService()
            if cloud_ocr.is_available():
                cloud_text = await cloud_ocr.extract_text(image_data)
                # ... handle result ...
        except Exception as e:
            logger.debug(f"Cloud OCR not available: {e}")
"""

# ============================================================================
# AFTER: Simple API call (boring, powerful backend)
# ============================================================================

# NEW CODE (in ocr_service.py):
"""
from app.bridges.rackplane_services import RackPlaneServicesClient
from sqlalchemy.orm import Session

class OCRService:
    def __init__(self, db: Session = None):
        # ... existing Tesseract init ...
        self.db = db
        # Client is created lazily (only when needed)
        self._rackplane_client = None
    
    def _get_rackplane_client(self):
        '''Get or create RackPlane Services client'''
        if self._rackplane_client is None and self.db:
            self._rackplane_client = RackPlaneServicesClient(self.db)
        return self._rackplane_client
    
    async def process_image(self, image_data: bytes, use_cloud_ocr: bool = False, force_cloud_ocr: bool = False) -> Dict:
        ocr_text = ""
        ocr_source = "none"
        confidence = "none"
        
        # Try free Tesseract first (unless forced to cloud)
        if not force_cloud_ocr:
            ocr_text = self.extract_text_from_image(image_data)
            ocr_source = "tesseract" if ocr_text else "none"
            confidence = "medium" if ocr_text else "none"
        
        # Try commercial cloud OCR via YOUR API (boring HTTP call)
        if (use_cloud_ocr or force_cloud_ocr):
            client = self._get_rackplane_client()
            if client:
                try:
                    # Boring API call - all the magic happens on YOUR servers
                    cloud_result = await client.cloud_ocr(image_data)
                    
                    cloud_text = cloud_result.get('text', '')
                    if cloud_text and len(cloud_text.strip()) > len(ocr_text.strip()):
                        ocr_text = cloud_text
                        ocr_source = cloud_result.get('service_used', 'cloud')
                        confidence = cloud_result.get('confidence', 'high')
                        logger.info(f"Using RackPlane Cloud OCR ({ocr_source})")
                        
                except HTTPException as e:
                    if e.status_code == 402:
                        # Subscription required - log but don't fail, use Tesseract result
                        logger.info(f"Cloud OCR requires subscription: {e.detail}")
                    elif e.status_code == 401:
                        # API key not configured - log but don't fail
                        logger.info(f"RackPlane Services API key not configured: {e.detail}")
                    else:
                        # Other errors - log but fall back to Tesseract
                        logger.warning(f"RackPlane Cloud OCR failed: {e.detail}")
                except Exception as e:
                    logger.warning(f"Unexpected error calling RackPlane Services: {e}")
        
        # ... rest of parsing logic ...
        parsed_data = self.parse_asset_information(ocr_text)
        
        return {
            "raw_text": ocr_text,
            "parsed_data": parsed_data,
            "confidence": confidence,
            "source": ocr_source,
            "suggestions": self._generate_suggestions(parsed_data)
        }
"""

# ============================================================================
# Example: Enhanced OCR Service Integration
# ============================================================================

"""
# In enhanced_ocr_service.py:

from app.bridges.rackplane_services import RackPlaneServicesClient

class EnhancedOCRService:
    def __init__(self, db: Session):
        self.ocr_service = OCRService(db)
        self.db = db
        self.rackplane_client = RackPlaneServicesClient(db)
    
    async def process_image_with_vendor_lookup(self, image_data: bytes, auto_fetch_vendor_data: bool = True):
        # Step 1: OCR (free Tesseract or commercial cloud via YOUR API)
        ocr_results = await self.ocr_service.process_image(image_data, use_cloud_ocr=True)
        parsed_data = ocr_results.get("parsed_data", {})
        
        # Step 2: Vendor identification (local, free)
        service_tag = self.vendor_lookup.extract_service_tag(
            ocr_results.get("raw_text", ""),
            parsed_data.get("serial_number")
        )
        vendor = self.vendor_lookup.identify_vendor(
            serial_number=parsed_data.get("serial_number"),
            service_tag=service_tag,
            model=parsed_data.get("model"),
            manufacturer=parsed_data.get("manufacturer")
        )
        
        # Step 3: Vendor API lookup (commercial, via YOUR API - boring HTTP call)
        vendor_data = None
        if auto_fetch_vendor_data and vendor != Vendor.UNKNOWN:
            try:
                # Boring API call - YOUR backend handles Dell/HP scraping
                vendor_data = await self.rackplane_client.vendor_lookup(
                    vendor=vendor.value,
                    serial=parsed_data.get("serial_number"),
                    service_tag=service_tag,
                    model=parsed_data.get("model")
                )
            except HTTPException as e:
                if e.status_code == 402:
                    logger.info(f"Vendor lookup requires subscription: {e.detail}")
                    vendor_data = {"error": "Subscription required", "message": e.detail}
                else:
                    raise
        
        return {
            "raw_text": ocr_results.get("raw_text", ""),
            "parsed_data": parsed_data,
            "vendor": vendor.value if vendor else None,
            "service_tag": service_tag,
            "vendor_data": vendor_data,
            "confidence": ocr_results.get("confidence", "medium"),
            "suggestions": ocr_results.get("suggestions", [])
        }
"""

# ============================================================================
# Example: API Endpoint Integration
# ============================================================================

"""
# In app/api/v1/images.py:

from app.bridges.rackplane_services import RackPlaneServicesClient

@router.post("/process-with-vendor-lookup")
async def process_with_vendor_lookup(
    file: UploadFile = File(...),
    auto_fetch_vendor_data: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # ... validation ...
    
    # Use enhanced OCR service (which uses boring API calls internally)
    enhanced_ocr = EnhancedOCRService(db)
    result = await enhanced_ocr.process_image_with_vendor_lookup(
        image_data=image_data,
        auto_fetch_vendor_data=auto_fetch_vendor_data
    )
    
    # ... return result ...
"""

