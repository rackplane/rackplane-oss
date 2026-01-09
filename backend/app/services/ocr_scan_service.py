# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
OCR Scan Service
Integrates with the deployed OCR service for Tesseract and Cloud OCR processing.
Stores results in OcrScan model for matching and ML training.
"""

import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from io import BytesIO

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.models.ocr_scan import OcrScan
except ImportError:
    OcrScan = None
from app.models.vendor_sku import VendorSKU
from app.core.config import settings

logger = logging.getLogger(__name__)

# OCR Service configuration
OCR_SERVICE_URL = os.environ.get("OCR_SERVICE_URL", "http://localhost:8000")
OCR_SERVICE_SECRET = os.environ.get("OCR_SERVICE_SECRET", "change-me-in-production")


class OcrScanService:
    """
    Service for OCR scanning with image deduplication and ML training support.
    
    Flow:
    1. Upload image → compute hashes
    2. Check for previous matches (exact or similar)
    3. Run Tesseract OCR (free)
    4. Optionally escalate to Cloud OCR (costs credits)
    5. Store results for future matching and ML training
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def scan_image(
        self,
        image_data: bytes,
        tenant_id: int,
        user_id: Optional[int] = None,
        retention_days: int = 90
    ) -> Dict[str, Any]:
        """
        Scan an image with Tesseract OCR and check for previous matches.
        
        Args:
            image_data: Raw image bytes
            tenant_id: Tenant ID for multi-tenancy
            user_id: Optional user ID
            retention_days: Days to keep the scan record (0 = never expires)
            
        Returns:
            Dict with OCR results, hashes, and match information
        """
        # Step 1: Call OCR service for Tesseract processing
        try:
            ocr_response = await self._call_ocr_service(image_data, "tesseract")
        except Exception as e:
            logger.error(f"OCR service call failed: {e}")
            # Create a failed scan record
            scan = self._create_scan_record(
                tenant_id=tenant_id,
                user_id=user_id,
                scan_status="failed",
                error_message=str(e),
                retention_days=retention_days
            )
            self.db.add(scan)
            self.db.commit()
            raise
        
        # Step 2: Check for previous matches based on image hash
        image_hash = ocr_response.get("hashes", {}).get("sha256")
        image_phash = ocr_response.get("hashes", {}).get("phash")
        
        previous_matches = await self._find_previous_matches(
            tenant_id=tenant_id,
            image_hash=image_hash,
            image_phash=image_phash
        )
        
        # Step 3: Create scan record
        scan = OcrScan(
            tenant_id=tenant_id,
            user_id=user_id,
            image_hash=image_hash,
            image_phash=image_phash,
            tesseract_text=ocr_response.get("text", ""),
            tesseract_confidence=ocr_response.get("confidence", "low"),
            tesseract_metadata=ocr_response.get("metadata", {}),
            parsed_data=self._parse_ocr_text(ocr_response.get("text", "")),
            scan_status="success",
        )
        
        # Set retention policy
        if retention_days > 0:
            scan.set_retention(retention_days)
        
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        
        return {
            "scan_id": scan.id,
            "text": scan.tesseract_text,
            "confidence": scan.tesseract_confidence,
            "hashes": {
                "sha256": image_hash,
                "phash": image_phash
            },
            "parsed_data": scan.parsed_data,
            "previous_matches": previous_matches,
            "created_at": scan.created_at.isoformat()
        }
    
    async def cloud_scan(
        self,
        scan_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Escalate an existing scan to Cloud OCR.
        
        Args:
            scan_id: ID of the existing OcrScan record
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Dict with Cloud OCR results
        """
        # Get existing scan
        scan = self.db.query(OcrScan).filter(
            OcrScan.id == scan_id,
            OcrScan.tenant_id == tenant_id
        ).first()
        
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        if scan.cloud_text is not None:
            # Already has cloud OCR, return existing results
            return {
                "scan_id": scan.id,
                "cloud_text": scan.cloud_text,
                "cloud_confidence": scan.cloud_confidence,
                "cloud_service": scan.cloud_service,
                "already_processed": True
            }
        
        # We don't have the original image, so we can't call cloud OCR
        # This endpoint should be called with the image data
        raise ValueError("Cannot escalate to cloud OCR without original image. Use cloud_scan_with_image instead.")
    
    async def cloud_scan_with_image(
        self,
        image_data: bytes,
        scan_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        Escalate an existing scan to Cloud OCR with the original image.
        
        Args:
            image_data: Raw image bytes
            scan_id: ID of the existing OcrScan record
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Dict with Cloud OCR results
        """
        # Get existing scan
        scan = self.db.query(OcrScan).filter(
            OcrScan.id == scan_id,
            OcrScan.tenant_id == tenant_id
        ).first()
        
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        if scan.cloud_text is not None:
            return {
                "scan_id": scan.id,
                "cloud_text": scan.cloud_text,
                "cloud_confidence": scan.cloud_confidence,
                "cloud_service": scan.cloud_service,
                "already_processed": True
            }
        
        # Call Cloud OCR service
        try:
            ocr_response = await self._call_ocr_service(image_data, "cloud")
        except Exception as e:
            logger.error(f"Cloud OCR service call failed: {e}")
            scan.error_message = f"Cloud OCR failed: {str(e)}"
            self.db.commit()
            raise
        
        # Update scan record with cloud results
        scan.cloud_text = ocr_response.get("text", "")
        scan.cloud_confidence = ocr_response.get("confidence", "low")
        scan.cloud_service = ocr_response.get("service", "google_vision")
        scan.cloud_scanned_at = datetime.utcnow()
        scan.cloud_cost_credits = 1  # Each cloud scan costs 1 credit
        
        # Re-parse with cloud text if it's better
        if ocr_response.get("confidence") in ["high", "medium"]:
            scan.parsed_data = self._parse_ocr_text(ocr_response.get("text", ""))
        
        self.db.commit()
        self.db.refresh(scan)
        
        return {
            "scan_id": scan.id,
            "cloud_text": scan.cloud_text,
            "cloud_confidence": scan.cloud_confidence,
            "cloud_service": scan.cloud_service,
            "parsed_data": scan.parsed_data,
            "already_processed": False
        }
    
    async def submit_correction(
        self,
        scan_id: int,
        tenant_id: int,
        corrections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit user corrections for ML training.
        
        Args:
            scan_id: ID of the OcrScan record
            tenant_id: Tenant ID for multi-tenancy
            corrections: User-provided corrections
            
        Returns:
            Updated scan summary
        """
        scan = self.db.query(OcrScan).filter(
            OcrScan.id == scan_id,
            OcrScan.tenant_id == tenant_id
        ).first()
        
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        scan.mark_corrected(corrections)
        self.db.commit()
        
        return {
            "scan_id": scan.id,
            "user_corrected": True,
            "corrected_data": scan.corrected_data
        }
    
    async def _call_ocr_service(
        self,
        image_data: bytes,
        ocr_type: str = "tesseract"
    ) -> Dict[str, Any]:
        """Call the deployed OCR service."""
        endpoint = f"{OCR_SERVICE_URL}/ocr/{ocr_type}"
        
        files = {"file": ("image.jpg", BytesIO(image_data), "image/jpeg")}
        headers = {"X-OCR-Service-Secret": OCR_SERVICE_SECRET}
        
        response = await self.client.post(endpoint, files=files, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"OCR service returned {response.status_code}: {response.text}")
        
        return response.json()
    
    async def _find_previous_matches(
        self,
        tenant_id: int,
        image_hash: Optional[str],
        image_phash: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find previous scans with matching or similar images."""
        matches = []
        
        # Exact hash match
        if image_hash:
            exact_matches = self.db.query(OcrScan).filter(
                OcrScan.tenant_id == tenant_id,
                OcrScan.image_hash == image_hash,
                OcrScan.scan_status == "success"
            ).order_by(OcrScan.created_at.desc()).limit(5).all()
            
            for match in exact_matches:
                matches.append({
                    "scan_id": match.id,
                    "match_type": "exact",
                    "confidence": 1.0,
                    "parsed_data": match.parsed_data,
                    "matched_sku_id": match.matched_sku_id,
                    "matched_asset_id": match.matched_asset_id,
                    "created_at": match.created_at.isoformat()
                })
        
        # Perceptual hash match (for similar but not identical images)
        # Note: Full pHash similarity requires comparison - for now we just do exact pHash match
        if image_phash and not matches:
            phash_matches = self.db.query(OcrScan).filter(
                OcrScan.tenant_id == tenant_id,
                OcrScan.image_phash == image_phash,
                OcrScan.scan_status == "success"
            ).order_by(OcrScan.created_at.desc()).limit(5).all()
            
            for match in phash_matches:
                matches.append({
                    "scan_id": match.id,
                    "match_type": "perceptual",
                    "confidence": 0.9,  # pHash matches are slightly less certain
                    "parsed_data": match.parsed_data,
                    "matched_sku_id": match.matched_sku_id,
                    "matched_asset_id": match.matched_asset_id,
                    "created_at": match.created_at.isoformat()
                })
        
        return matches
    
    def _parse_ocr_text(self, text: str) -> Dict[str, Any]:
        """
        Parse OCR text to extract structured data.
        
        Looks for:
        - Serial numbers (SN:, S/N:, Serial:)
        - Part numbers (PN:, P/N:, Part:)
        - Model numbers
        - Potential SKUs
        """
        import re
        
        parsed = {
            "serial_numbers": [],
            "part_numbers": [],
            "model_numbers": [],
            "potential_skus": []
        }
        
        if not text:
            return parsed
        
        # Serial number patterns
        sn_patterns = [
            r'(?:SN|S/N|Serial(?:\s*Number)?)[:\s]*([A-Z0-9]{6,20})',
            r'(?:Service\s*Tag)[:\s]*([A-Z0-9]{6,10})'
        ]
        
        for pattern in sn_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            parsed["serial_numbers"].extend(matches)
        
        # Part number patterns
        pn_patterns = [
            r'(?:PN|P/N|Part(?:\s*Number)?)[:\s]*([A-Z0-9\-]{6,30})'
        ]
        
        for pattern in pn_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            parsed["part_numbers"].extend(matches)
        
        # Model patterns (common vendor formats)
        model_patterns = [
            r'(?:Model)[:\s]*([A-Z0-9\-]+)',
            r'(H100|A100|A10|L40|RTX\s*\d+)',  # NVIDIA models
            r'(PowerEdge\s*[A-Z0-9]+)',  # Dell servers
            r'(ProLiant\s*[A-Z0-9]+)',  # HP servers
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            parsed["model_numbers"].extend(matches)
        
        # Potential SKUs (alphanumeric strings that look like product codes)
        sku_pattern = r'\b([A-Z]{2,4}[\-]?[A-Z0-9]{3,10}(?:[\-][A-Z0-9]+)*)\b'
        potential_skus = re.findall(sku_pattern, text.upper())
        # Filter out common false positives
        filtered_skus = [s for s in potential_skus if len(s) >= 6 and s not in ["SERIAL", "NUMBER", "MODEL"]]
        parsed["potential_skus"] = list(set(filtered_skus))[:10]  # Limit to 10
        
        # Deduplicate
        parsed["serial_numbers"] = list(set(parsed["serial_numbers"]))
        parsed["part_numbers"] = list(set(parsed["part_numbers"]))
        parsed["model_numbers"] = list(set(parsed["model_numbers"]))
        
        return parsed
    
    def _create_scan_record(
        self,
        tenant_id: int,
        user_id: Optional[int],
        scan_status: str,
        error_message: Optional[str] = None,
        retention_days: int = 90
    ) -> OcrScan:
        """Create a new OcrScan record."""
        scan = OcrScan(
            tenant_id=tenant_id,
            user_id=user_id,
            scan_status=scan_status,
            error_message=error_message
        )
        if retention_days > 0:
            scan.set_retention(retention_days)
        return scan
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
