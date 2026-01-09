# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
OCR Scan Model
Stores OCR scan results, image hashes, and user corrections for ML training.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON, Boolean, Index, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class OcrScan(Base, TenantMixin):
    """
    OCR scan results for label/barcode scanning.
    
    Stores both Tesseract (local) and Cloud OCR results, image fingerprints
    for deduplication, and user corrections for ML training data.
    
    Workflow:
    1. Image uploaded → Tesseract scan (free)
    2. Hash computed → Check for previous matches
    3. Optional cloud OCR escalation (costs credits)
    4. User corrections captured for ML training
    """
    __tablename__ = "ocr_scans"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Image Fingerprinting
    image_hash = Column(String(64), nullable=True, index=True, comment="SHA256 hash for exact match")
    image_phash = Column(String(16), nullable=True, index=True, comment="Perceptual hash for similar images")
    image_url = Column(String(500), nullable=True, comment="MinIO/S3 URL to stored image")
    
    # Tesseract Results (always populated)
    tesseract_text = Column(Text, nullable=True, comment="Raw Tesseract OCR output")
    tesseract_confidence = Column(String(20), nullable=True, comment="Confidence level: low/medium/high")
    tesseract_metadata = Column(JSON, nullable=True, comment="PSM mode, preprocessing flags, timing")
    """
    Example tesseract_metadata:
    {
        "psm": 3,
        "preprocessing": ["deskew", "contrast"],
        "processing_time_ms": 245,
        "word_confidences": [0.95, 0.87, 0.92]
    }
    """
    
    # Cloud OCR Results (populated if escalated)
    cloud_text = Column(Text, nullable=True, comment="Cloud OCR output (Google Vision etc.)")
    cloud_confidence = Column(String(20), nullable=True, comment="Cloud confidence: low/medium/high")
    cloud_service = Column(String(50), nullable=True, comment="Service used: google_vision, aws_textract")
    cloud_scanned_at = Column(DateTime, nullable=True, comment="When cloud OCR was performed")
    cloud_cost_credits = Column(Integer, nullable=True, comment="Credits consumed for cloud OCR")
    
    # Parsed Data (extracted from OCR text)
    parsed_data = Column(JSON, nullable=True, comment="Structured data extracted from OCR")
    """
    Example parsed_data:
    {
        "serial_numbers": ["SN123456", "SN789012"],
        "model": "NVIDIA H100",
        "manufacturer": "NVIDIA",
        "part_number": "900-21010-0000-000",
        "potential_skus": ["H100-PCIE-80GB"]
    }
    """
    
    # Matching Results
    matched_sku_id = Column(Integer, ForeignKey("vendor_skus.id"), nullable=True, index=True)
    matched_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
    match_type = Column(String(20), nullable=True, comment="Match type: exact_hash, similar_hash, sku_lookup")
    match_confidence = Column(Float, nullable=True, comment="Match confidence 0.0-1.0")
    
    # User Corrections (for ML training)
    user_corrected = Column(Boolean, default=False, index=True, comment="Whether user made corrections")
    corrected_data = Column(JSON, nullable=True, comment="User-provided corrections")
    """
    Example corrected_data:
    {
        "correct_text": "NVIDIA H100 PCIe 80GB",
        "correct_serial": "SN123456789",
        "correct_sku": "H100-PCIE-80GB",
        "notes": "Label was upside down"
    }
    """
    
    # Scan Status and Lifecycle
    scan_status = Column(String(20), default="pending", index=True, comment="Status: pending/processing/success/failed")
    error_message = Column(Text, nullable=True, comment="Error message if scan failed")
    
    # Retention Policy (CPO addition)
    expires_at = Column(DateTime, nullable=True, index=True, comment="NULL = never expires")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    matched_sku = relationship("VendorSKU", foreign_keys=[matched_sku_id])
    matched_asset = relationship("Asset", foreign_keys=[matched_asset_id])
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_ocr_scans_tenant_status', 'tenant_id', 'scan_status'),
        Index('ix_ocr_scans_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_ocr_scans_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<OcrScan id={self.id} status={self.scan_status} confidence={self.tesseract_confidence}>"
    
    def set_retention(self, days: int = 90):
        """Set expiration date for this scan."""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
    
    def mark_corrected(self, corrections: dict):
        """Record user corrections for ML training."""
        self.user_corrected = True
        self.corrected_data = corrections
        self.updated_at = datetime.utcnow()
    
    def to_summary(self) -> dict:
        """Return a summary suitable for API responses."""
        return {
            "id": self.id,
            "status": self.scan_status,
            "tesseract_text": self.tesseract_text,
            "tesseract_confidence": self.tesseract_confidence,
            "cloud_text": self.cloud_text,
            "cloud_confidence": self.cloud_confidence,
            "parsed_data": self.parsed_data,
            "matched_sku_id": self.matched_sku_id,
            "matched_asset_id": self.matched_asset_id,
            "match_type": self.match_type,
            "user_corrected": self.user_corrected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
