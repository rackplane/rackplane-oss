# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Image Processing API Endpoints
Handle image uploads and OCR processing for inventory
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.licensing import require_feature
from app.models.user import User
from app.services.ocr_service import OCRService  # Legacy - still needed for backwards compat
from app.services.ocr_scan_service import OcrScanService
from app.models.tenant import Tenant

# Dependency Injection
from app.core.container import get_ocr_service
from app.abstractions.ocr import OCRServiceInterface

# Optional: Enhanced OCR with vendor lookup
try:
    from app.services.enhanced_ocr_service import EnhancedOCRService
    ENHANCED_OCR_AVAILABLE = True
except ImportError:
    ENHANCED_OCR_AVAILABLE = False
    EnhancedOCRService = None

router = APIRouter()


# =============================================================================
# NEW: Tesseract-first OCR Scan Endpoints
# =============================================================================

@router.post("/scan")
async def scan_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and scan an image with Tesseract OCR (FREE)
    
    This endpoint:
    1. Processes the image with Tesseract (free, fast)
    2. Computes image hashes for deduplication
    3. Checks for previous matches (exact or similar)
    4. Parses text for serial numbers, part numbers, etc.
    
    To escalate to Cloud OCR (better accuracy), use POST /images/cloud-scan/{id}
    
    Returns:
        scan_id: ID for future reference
        text: Extracted text
        confidence: low/medium/high
        hashes: SHA256 and perceptual hash
        parsed_data: Structured data extracted from text
        previous_matches: Similar images previously scanned
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_data = await file.read()
        
        # Check file size (limit to 10MB)
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        # Get tenant_id from current user
        tenant_id = current_user.tenant_id
        
        # Process with OCR scan service
        ocr_scan_service = OcrScanService(db)
        try:
            result = await ocr_scan_service.scan_image(
                image_data=image_data,
                tenant_id=tenant_id,
                user_id=current_user.id,
                retention_days=90
            )
        finally:
            await ocr_scan_service.close()
        
        # Convert image to base64 for preview
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{file.content_type};base64,{image_base64}"
        
        return {
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(image_data),
            "image_preview": image_url,
            **result
        }
    
    except Exception as e:
        logger.error(f"OCR scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR scan failed: {str(e)}")


@router.post("/cloud-scan/{scan_id}")
@require_feature("ocr_cloud")
async def cloud_scan(
    scan_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Escalate an existing scan to Cloud OCR (PAID - 1 credit)
    
    **Premium Feature**: Requires 'ocr_cloud' subscription.
    
    Use this when Tesseract results are unsatisfactory and you need
    higher accuracy from Google Cloud Vision or similar.
    
    Args:
        scan_id: ID from the original /scan request
        file: Original image file (required for cloud processing)
    
    Returns:
        cloud_text: Text from Cloud OCR
        cloud_confidence: Confidence level
        cloud_service: Service used (google_vision, etc.)
        parsed_data: Re-parsed structured data
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_data = await file.read()
        
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        tenant_id = current_user.tenant_id
        
        ocr_scan_service = OcrScanService(db)
        try:
            result = await ocr_scan_service.cloud_scan_with_image(
                image_data=image_data,
                scan_id=scan_id,
                tenant_id=tenant_id
            )
        finally:
            await ocr_scan_service.close()
        
        return {
            "success": True,
            **result
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cloud OCR scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cloud OCR scan failed: {str(e)}")


@router.patch("/scan/{scan_id}/correct")
async def submit_correction(
    scan_id: int,
    corrections: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit user corrections for an OCR scan (for ML training)
    
    Help improve future OCR accuracy by submitting corrections.
    These corrections are stored for training future ML models.
    
    Args:
        scan_id: ID of the scan to correct
        corrections: Dict with corrections, e.g.:
            {
                "correct_text": "NVIDIA H100 PCIe 80GB",
                "correct_serial": "SN123456789",
                "correct_sku": "H100-PCIE-80GB",
                "notes": "Label was upside down"
            }
    
    Returns:
        Updated scan confirmation
    """
    try:
        tenant_id = current_user.tenant_id
        
        ocr_scan_service = OcrScanService(db)
        try:
            result = await ocr_scan_service.submit_correction(
                scan_id=scan_id,
                tenant_id=tenant_id,
                corrections=corrections
            )
        finally:
            await ocr_scan_service.close()
        
        return {
            "success": True,
            **result
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Correction submission failed: {e}")
        raise HTTPException(status_code=500, detail=f"Correction submission failed: {str(e)}")


# =============================================================================
# EXISTING: Cloud OCR Endpoints (Premium)
# =============================================================================


@router.post("/upload-and-process")
@require_feature("ocr_cloud")
async def upload_and_process_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    ocr: OCRServiceInterface = Depends(get_ocr_service)
):
    """
    Upload an image and process it with Cloud OCR

    **Premium Feature**: Requires 'ocr_cloud' subscription.

    Returns extracted text and parsed asset information using cloud OCR services
    (Google Cloud Vision, AWS Textract, or Azure Computer Vision).
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read file content
    try:
        image_data = await file.read()

        # Check file size (limit to 10MB)
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")

        # Process with OCR via Dependency Injection (auto-selects implementation based on BUILD_MODE)
        ocr_results = await ocr.process_image(
            image_data,
            use_cloud_ocr=True,
            db=db  # Pass DB session for quota tracking
        )

        # Convert image to base64 for preview
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{file.content_type};base64,{image_base64}"

        return {
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(image_data),
            "image_preview": image_url,
            "ocr_results": ocr_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@router.post("/process-base64")
@require_feature("ocr_cloud")
async def process_base64_image(
    image_data: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    ocr: OCRServiceInterface = Depends(get_ocr_service)
):
    """
    Process a base64-encoded image with Cloud OCR

    **Premium Feature**: Requires 'ocr_cloud' subscription.

    Useful for mobile camera captures. Uses cloud OCR services for superior accuracy.
    """
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Decode base64
        image_bytes = base64.b64decode(image_data)

        # Check file size
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")

        # Process with OCR via Dependency Injection (auto-selects implementation based on BUILD_MODE)
        ocr_results = await ocr.process_image(
            image_bytes,
            use_cloud_ocr=True,
            db=db  # Pass DB session for quota tracking
        )

        return {
            "success": True,
            "size_bytes": len(image_bytes),
            "ocr_results": ocr_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@router.get("/ocr-status")
async def get_ocr_status(ocr: OCRServiceInterface = Depends(get_ocr_service)):
    """Check if OCR service is available"""
    available = ocr.is_available()
    service_name = ocr.get_service_name()
    return {
        "available": available,
        "service": service_name,
        "message": f"OCR service is ready ({service_name})" if available else "OCR service unavailable",
        "enhanced_ocr_available": ENHANCED_OCR_AVAILABLE
    }


@router.post("/process-with-vendor-lookup")
@require_feature("vendor_lookup")
async def process_with_vendor_lookup(
    file: UploadFile = File(...),
    auto_fetch_vendor_data: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced OCR with vendor identification and warranty lookup
    
    **Premium Feature**: Requires 'vendor_lookup' subscription.
    
    This endpoint:
    1. Extracts text from the image (OCR)
    2. Identifies the vendor (Dell, HP, Cisco, etc.)
    3. Optionally fetches warranty/config data from vendor APIs
    
    Args:
        file: Image file to process
        auto_fetch_vendor_data: If True, automatically fetch warranty data from vendor API
        
    Returns:
        Enhanced OCR results with vendor identification and warranty data
    """
    if not ENHANCED_OCR_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Enhanced OCR service not available. Vendor lookup services may not be installed."
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read file content
        image_data = await file.read()
        
        # Check file size (limit to 10MB)
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        # Process with enhanced OCR (uses RackPlane Services API)
        enhanced_ocr = EnhancedOCRService(db)
        result = await enhanced_ocr.process_image_with_vendor_lookup(
            image_data=image_data,
            auto_fetch_vendor_data=auto_fetch_vendor_data
        )
        
        # Convert image to base64 for preview
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{file.content_type};base64,{image_base64}"
        
        return {
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(image_data),
            "image_preview": image_url,
            "ocr_results": {
                "raw_text": result.get("raw_text", ""),
                "parsed_data": result.get("parsed_data", {}),
                "confidence": result.get("confidence", "none"),
                "suggestions": result.get("suggestions", [])
            },
            "vendor": result.get("vendor"),
            "service_tag": result.get("service_tag"),
            "vendor_data": result.get("vendor_data")
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Enhanced OCR processing failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Enhanced OCR processing failed: {str(e)}")


@router.post("/process-base64-with-vendor-lookup")
@require_feature("vendor_lookup")
async def process_base64_with_vendor_lookup(
    image_data: str,
    auto_fetch_vendor_data: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced OCR with vendor lookup for base64-encoded images
    
    **Premium Feature**: Requires 'vendor_lookup' subscription.
    
    Useful for mobile camera captures with automatic vendor identification
    and warranty lookup.
    
    Args:
        image_data: Base64-encoded image string (with or without data URL prefix)
        auto_fetch_vendor_data: If True, automatically fetch warranty data from vendor API
        
    Returns:
        Enhanced OCR results with vendor identification and warranty data
    """
    if not ENHANCED_OCR_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Enhanced OCR service not available. Vendor lookup services may not be installed."
        )
    
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Check file size
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        # Process with enhanced OCR
        enhanced_ocr = EnhancedOCRService(db=db)
        result = await enhanced_ocr.process_image_with_vendor_lookup(
            image_data=image_bytes,
            auto_fetch_vendor_data=auto_fetch_vendor_data
        )
        
        return {
            "success": True,
            "size_bytes": len(image_bytes),
            "ocr_results": {
                "raw_text": result.get("raw_text", ""),
                "parsed_data": result.get("parsed_data", {}),
                "confidence": result.get("confidence", "none"),
                "suggestions": result.get("suggestions", [])
            },
            "vendor": result.get("vendor"),
            "service_tag": result.get("service_tag"),
            "vendor_data": result.get("vendor_data")
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Enhanced OCR processing failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Enhanced OCR processing failed: {str(e)}")
