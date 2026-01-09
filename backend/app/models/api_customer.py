# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Customer Models

Models for customer API key authentication and usage logging
for the RackPlane Central Services (services.rackplane.com).
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ApiCustomer(Base):
    """
    Registry of customers with API access to central services.
    
    API keys are hashed (SHA256) for security - never store plaintext keys.
    """
    __tablename__ = "api_customers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(36), nullable=True, index=True,
                       comment="Tenant UUID from Tenant.uuid for contribution credit tracking")
    api_key_hash = Column(String(64), unique=True, nullable=False, index=True,
                          comment="SHA256 hash of API key")
    api_key_plain = Column(String(100), nullable=True,
                           comment="Temporary storage of plain API key for display")
    customer_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    tier = Column(String(50), default="pro", 
                  comment="Subscription tier: 'pro' or 'enterprise'")
    is_active = Column(Boolean, default=True)
    rate_limit_hour = Column(Integer, default=1000,
                             comment="Max requests per hour")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True,
                        comment="NULL means never expires")
    last_used_at = Column(DateTime, nullable=True)
    customer_metadata = Column(JSON, nullable=True,
                      comment="Extra customer data (JSON)")
    
    # Contributor tracking
    contribution_count = Column(Integer, default=0,
                                comment="Number of verified SKU contributions")
    contributor_since = Column(DateTime, nullable=True,
                               comment="Date of first contribution")
    is_lifetime_contributor = Column(Boolean, default=False,
                                     comment="True if has ever contributed - never loses access")
    can_approve_skus = Column(Boolean, default=False,
                            comment="Permission to approve SKUs into the central catalog (Direct Publish)")
    can_contribute = Column(Boolean, default=False,
                            comment="Permission to submit SKUs to the central pending queue")
    can_delete_skus = Column(Boolean, default=False,
                             comment="Permission to delete SKUs from central catalog")
    
    # Relationship to usage logs
    usage_logs = relationship("ApiUsageLog", back_populates="customer")
    
    def __repr__(self):
        return f"<ApiCustomer(id={self.id}, name='{self.customer_name}', tier='{self.tier}')>"


class ApiUsageLog(Base):
    """
    Log of API requests for tracking, analytics, and billing.
    
    Each request to protected endpoints creates a log entry.
    """
    __tablename__ = "api_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("api_customers.id"), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False, comment="HTTP method")
    status_code = Column(Integer, nullable=True)
    request_ip = Column(String(45), nullable=True, comment="IPv4 or IPv6")
    user_agent = Column(String(500), nullable=True)
    request_params = Column(JSON, nullable=True,
                            comment="Query params and relevant request data")
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationship to customer
    customer = relationship("ApiCustomer", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<ApiUsageLog(id={self.id}, customer_id={self.customer_id}, endpoint='{self.endpoint}')>"
