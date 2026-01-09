# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Central Catalog Submission Model
Stores pending SKU contributions from partners for moderation.
"""

from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CentralCatalogSubmission(Base):
    """
    Queue for catalog contributions.
    
    Items here are NOT live. They must be approved by a super admin
    to be moved to the CatalogSKU table.
    """
    __tablename__ = "central_catalog_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who submitted it
    customer_id = Column(Integer, ForeignKey("api_customers.id"), nullable=False, index=True)
    
    # Metadata
    status = Column(Enum(SubmissionStatus, name="submissionstatus"), default=SubmissionStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Data Payload
    proposed_data = Column(JSON, nullable=False, comment="Complete SKU data payload")
    
    # Moderation
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_notes = Column(Text, nullable=True, comment="Reason for rejection or internal notes")
    
    # Relationships
    customer = relationship("ApiCustomer", backref="submissions")
    reviewer = relationship("User", backref="reviewed_submissions")
    
    def __repr__(self):
        return f"<CentralSubmission {self.id} status={self.status} customer={self.customer_id}>"
