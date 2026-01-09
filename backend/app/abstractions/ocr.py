"""
Abstract OCR Service Interface
Defines the contract for OCR services (local Tesseract or cloud-based)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class OCRServiceInterface(ABC):
    """Abstract interface for OCR services (Tesseract or Cloud)"""

    @abstractmethod
    async def extract_text(self, image_data: bytes) -> Optional[str]:
        """
        Extract raw text from image data

        Args:
            image_data: Binary image data (JPEG, PNG, etc.)

        Returns:
            Extracted text or None if extraction failed
        """
        pass

    @abstractmethod
    async def process_image(
        self,
        image_data: bytes,
        use_cloud_ocr: bool = False,
        force_cloud_ocr: bool = False,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process image and return OCR results with parsed information

        Args:
            image_data: Binary image data
            use_cloud_ocr: Suggest using cloud OCR (may be ignored in OSS)
            force_cloud_ocr: Force cloud OCR (may raise error in OSS)
            db: Database session for quota tracking

        Returns:
            Dict containing:
                - raw_text: Extracted text
                - parsed_data: Structured data extracted from text
                - confidence: Confidence level (low/medium/high)
                - ocr_source: Source of OCR (tesseract/cloud)
                - suggestions: List of suggestions for user
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the OCR service is available and configured

        Returns:
            True if service is ready to use, False otherwise
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of the OCR service implementation

        Returns:
            Service name (e.g., "Local Tesseract", "Cloud OCR")
        """
        return self.__class__.__name__
