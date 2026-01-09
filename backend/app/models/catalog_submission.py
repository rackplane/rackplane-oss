# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Catalog Submission Model
Tracks submissions to the global catalog for review and approval.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    TENANT_APPROVED = "tenant_approved"  # Approved by Tenant Admin, awaiting Super Admin
    APPROVED = "approved"  # Approved by Super Admin, added to global catalog
    REJECTED = "rejected"


class SubmissionMethod(str, enum.Enum):
    MANUAL_EDIT = "manual_edit"  # User edited a VendorSKU and submitted
    BROWSER_SCRAPE = "browser_scrape"  # Scraped from URL via scraper tool
    API_IMPORT = "api_import"  # Imported via API (bulk import, etc.)


class CatalogSubmission(Base):
    """
    Tracks submissions to the global catalog.
    
    Workflow:
    1. User scrapes/edits SKU data
    2. User submits for review (status=pending)
    3. Admin reviews and approves/rejects
    4. If approved, data is copied to CatalogSKU table
    """
    __tablename__ = "catalog_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Submission data (snapshot of SKU at submission time)
    vendor = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), nullable=False, index=True)
    data_snapshot = Column(JSON, nullable=False, comment="Full SKU data at submission time")
    
    # Source information
    source_url = Column(String(500), nullable=True, comment="Original URL if scraped")
    submission_method = Column(String(50), nullable=False, default="manual_edit")
    
    # Existing catalog reference (if updating existing entry)
    existing_catalog_sku_id = Column(Integer, nullable=True, comment="ID in catalog_skus if this is an update")
    
    # Submission tracking
    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Review status
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Review tracking
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    submitted_by = relationship("User", foreign_keys=[submitted_by_user_id], backref="catalog_submissions")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    
    def __repr__(self):
        return f"<CatalogSubmission {self.vendor}:{self.sku} ({self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "vendor": self.vendor,
            "sku": self.sku,
            "data_snapshot": self.data_snapshot,
            "source_url": self.source_url,
            "submission_method": self.submission_method,
            "existing_catalog_sku_id": self.existing_catalog_sku_id,
            "submitted_by_user_id": self.submitted_by_user_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "status": self.status,
            "reviewed_by_user_id": self.reviewed_by_user_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
