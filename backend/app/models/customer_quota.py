# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Customer Quota Models

Models for tracking OCR and other metered service usage.
Supports monthly limits, unlimited plans, and pay-per-use.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class QuotaType(enum.Enum):
    """Types of quota plans."""
    MONTHLY = "monthly"          # Reset at billing cycle, has monthly_limit
    UNLIMITED = "unlimited"      # No limits (MSP/Enterprise)
    PAY_PER_USE = "pay_per_use"  # Deduct from prepaid_balance


class CustomerQuota(Base):
    """
    Tracks usage quotas for each customer.
    
    Each customer has one quota record that tracks their current
    usage, limits, and billing period.
    """
    __tablename__ = "customer_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("api_customers.id"), unique=True, nullable=False)
    
    # Quota configuration
    quota_type = Column(String(50), nullable=False, default="monthly",
                        comment="monthly, unlimited, or pay_per_use")
    monthly_limit = Column(Integer, default=100,
                          comment="Base tier limit for monthly plans")
    
    # Usage tracking
    current_usage = Column(Integer, default=0,
                          comment="Scans used this period (monthly) or total (pay_per_use)")
    bonus_scans = Column(Integer, default=0,
                        comment="Additional purchased bundles (monthly plans)")
    prepaid_balance = Column(Integer, default=0,
                            comment="Credit balance for pay_per_use customers")
    
    # Billing period (NULL for pay_per_use)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("ApiCustomer", backref="quota")
    transactions = relationship("QuotaTransaction", back_populates="quota")
    
    def __repr__(self):
        return f"<CustomerQuota(customer_id={self.customer_id}, type={self.quota_type})>"
    
    @property
    def remaining(self) -> int:
        """Calculate remaining scans available."""
        if self.quota_type == "unlimited":
            return 999999  # Effectively unlimited
        elif self.quota_type == "pay_per_use":
            return self.prepaid_balance
        else:  # monthly
            base_remaining = self.monthly_limit - self.current_usage
            return max(0, base_remaining + self.bonus_scans)
    
    @property
    def can_use(self) -> bool:
        """Check if customer can use a scan."""
        if self.quota_type == "unlimited":
            return True
        return self.remaining > 0


class TransactionType(enum.Enum):
    """Types of quota transactions."""
    USAGE = "usage"                  # Consumed a scan
    BUNDLE_PURCHASE = "bundle"       # Bought additional scans
    PREPAID_PURCHASE = "prepaid"     # Added to prepaid balance
    MONTHLY_RESET = "reset"          # Period reset (monthly plans)
    ADMIN_ADJUST = "admin"           # Manual adjustment


class QuotaTransaction(Base):
    """
    Audit trail for all quota changes.
    
    Every scan usage, bundle purchase, or reset is logged here
    for billing and debugging purposes.
    """
    __tablename__ = "quota_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    quota_id = Column(Integer, ForeignKey("customer_quotas.id"), nullable=False, index=True)
    
    transaction_type = Column(String(50), nullable=False,
                              comment="usage, bundle, prepaid, reset, admin")
    amount = Column(Integer, nullable=False,
                   comment="Change in quota (negative for usage)")
    balance_after = Column(Integer, nullable=False,
                          comment="Remaining balance after transaction")
    
    description = Column(Text, nullable=True)
    reference_id = Column(String(255), nullable=True,
                         comment="External reference (Stripe payment ID, etc.)")
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    quota = relationship("CustomerQuota", back_populates="transactions")
    
    def __repr__(self):
        return f"<QuotaTransaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"
