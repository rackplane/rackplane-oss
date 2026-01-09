"""
OSS OCR Service Implementation
Uses local Tesseract OCR only (no cloud services)
"""
import logging
from typing import Dict, Any, Optional

from app.abstractions.ocr import OCRServiceInterface
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


class LocalOCRService(OCRServiceInterface):
    """OSS implementation using local Tesseract OCR only"""

    def __init__(self):
        try:
            self._tesseract = OCRService()
            self._initialization_error = None
        except Exception as e:
            logger.warning(f"Failed to initialize Tesseract OCR: {e}")
            self._tesseract = None
            self._initialization_error = str(e)

    async def extract_text(self, image_data: bytes) -> Optional[str]:
        """Extract text using local Tesseract"""
        if self._tesseract is None:
            logger.error(f"Tesseract not available: {self._initialization_error}")
            return None

        try:
            text = self._tesseract.extract_text_from_image(image_data)
            return text or None
        except Exception as e:
            logger.error(f"Local OCR extraction failed: {e}")
            return None

    async def process_image(
        self,
        image_data: bytes,
        use_cloud_ocr: bool = False,
        force_cloud_ocr: bool = False,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Process with Tesseract only (ignore cloud flags in OSS mode)"""

        if use_cloud_ocr or force_cloud_ocr:
            logger.warning(
                "Cloud OCR requested but not available in OSS build. "
                "Using local Tesseract instead."
            )

        # Handle case when Tesseract initialization failed
        if self._tesseract is None:
            return {
                "raw_text": "",
                "parsed_data": {},
                "confidence": "low",
                "ocr_source": "tesseract",
                "suggestions": [],
                "error": self._initialization_error or "Tesseract not available",
                "cloud_ocr_available": False,
            }

        # Use existing Tesseract implementation
        try:
            text = self._tesseract.extract_text_from_image(image_data)
            parsed = self._tesseract.parse_asset_information(text)

            return {
                "raw_text": text,
                "parsed_data": parsed,
                "confidence": "medium" if text else "low",
                "ocr_source": "tesseract",
                "suggestions": self._tesseract._generate_suggestions(parsed),
                "cloud_ocr_available": False,  # Indicate OSS mode
            }
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {
                "raw_text": "",
                "parsed_data": {},
                "confidence": "low",
                "ocr_source": "tesseract",
                "suggestions": [],
                "error": str(e),
                "cloud_ocr_available": False,
            }

    def is_available(self) -> bool:
        """Check if Tesseract is installed and available"""
        if self._tesseract is None:
            return False
        return self._tesseract.has_tesseract

    def get_service_name(self) -> str:
        return "Local Tesseract OCR (OSS)"
