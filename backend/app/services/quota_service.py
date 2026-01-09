# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Quota Service

Business logic for checking, consuming, and managing customer quotas.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.customer_quota import CustomerQuota, QuotaTransaction
from app.models.api_customer import ApiCustomer

logger = logging.getLogger(__name__)


class QuotaError(Exception):
    """Base exception for quota errors."""
    pass


class QuotaExceeded(QuotaError):
    """Raised when quota is exhausted."""
    pass


class QuotaNotFound(QuotaError):
    """Raised when customer has no quota record."""
    pass


def get_or_create_quota(db: Session, customer_id: int) -> CustomerQuota:
    """
    Get or create quota record for a customer.
    
    New customers default to monthly with 100 scan limit (Starter tier).
    """
    quota = db.query(CustomerQuota).filter(
        CustomerQuota.customer_id == customer_id
    ).first()
    
    if not quota:
        # Create default quota
        today = date.today()
        quota = CustomerQuota(
            customer_id=customer_id,
            quota_type="monthly",
            monthly_limit=100,
            current_usage=0,
            bonus_scans=0,
            prepaid_balance=0,
            period_start=today,
            period_end=today + timedelta(days=30)
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)
        logger.info(f"Created default quota for customer {customer_id}")
    
    return quota


def check_and_reset_period(db: Session, quota: CustomerQuota) -> bool:
    """
    Check if billing period has ended and reset if needed.
    
    Returns True if a reset was performed.
    """
    if quota.quota_type != "monthly":
        return False
    
    if quota.period_end and date.today() > quota.period_end:
        # Period has ended, reset
        old_usage = quota.current_usage
        quota.current_usage = 0
        quota.bonus_scans = 0  # Bundles don't roll over
        quota.period_start = date.today()
        quota.period_end = date.today() + timedelta(days=30)
        
        # Log the reset
        transaction = QuotaTransaction(
            quota_id=quota.id,
            transaction_type="reset",
            amount=old_usage,  # Record what was reset
            balance_after=quota.remaining,
            description=f"Monthly reset. Previous usage: {old_usage}"
        )
        db.add(transaction)
        db.commit()
        
        logger.info(f"Reset quota for customer {quota.customer_id}")
        return True
    
    return False


def get_quota_status(db: Session, customer_id: int) -> dict:
    """
    Get current quota status for a customer.
    
    Returns dict with current usage, limits, and remaining scans.
    """
    quota = get_or_create_quota(db, customer_id)
    check_and_reset_period(db, quota)
    
    # Get customer info for plan name
    customer = db.query(ApiCustomer).filter(ApiCustomer.id == customer_id).first()
    plan_name = customer.tier if customer else "unknown"
    
    return {
        "customer_id": customer_id,
        "plan": plan_name,
        "quota_type": quota.quota_type,
        "monthly_limit": quota.monthly_limit if quota.quota_type == "monthly" else None,
        "current_usage": quota.current_usage,
        "bonus_scans": quota.bonus_scans if quota.quota_type == "monthly" else None,
        "prepaid_balance": quota.prepaid_balance if quota.quota_type == "pay_per_use" else None,
        "remaining": quota.remaining,
        "is_unlimited": quota.quota_type == "unlimited",
        "period_start": quota.period_start.isoformat() if quota.period_start else None,
        "period_end": quota.period_end.isoformat() if quota.period_end else None
    }


def consume_quota(
    db: Session, 
    customer_id: int, 
    scans: int = 1,
    description: str = None
) -> Tuple[bool, int]:
    """
    Consume scans from customer's quota.
    
    Args:
        db: Database session
        customer_id: Customer to charge
        scans: Number of scans to consume (default 1)
        description: Optional description for audit log
        
    Returns:
        Tuple of (success: bool, remaining: int)
        
    Raises:
        QuotaExceeded: If not enough quota available
    """
    quota = get_or_create_quota(db, customer_id)
    check_and_reset_period(db, quota)
    
    # Check if enough quota
    if quota.quota_type == "unlimited":
        # Unlimited - always succeeds, still log
        pass
    elif quota.quota_type == "pay_per_use":
        if quota.prepaid_balance < scans:
            raise QuotaExceeded(
                f"Insufficient prepaid balance. Have {quota.prepaid_balance}, need {scans}"
            )
        quota.prepaid_balance -= scans
    else:  # monthly
        if quota.remaining < scans:
            raise QuotaExceeded(
                f"Monthly quota exceeded. Remaining: {quota.remaining}, need {scans}"
            )
        quota.current_usage += scans
    
    # Log transaction
    transaction = QuotaTransaction(
        quota_id=quota.id,
        transaction_type="usage",
        amount=-scans,
        balance_after=quota.remaining,
        description=description or f"Used {scans} OCR scan(s)"
    )
    db.add(transaction)
    db.commit()
    
    logger.info(f"Customer {customer_id} used {scans} scan(s), remaining: {quota.remaining}")
    
    return True, quota.remaining


def add_bundle(
    db: Session,
    customer_id: int,
    scans: int,
    reference_id: str = None,
    description: str = None
) -> int:
    """
    Add purchased bundle scans to customer's quota.
    
    For monthly plans, adds to bonus_scans.
    For pay_per_use, adds to prepaid_balance.
    
    Returns new remaining balance.
    """
    quota = get_or_create_quota(db, customer_id)
    
    if quota.quota_type == "unlimited":
        logger.warning(f"Tried to add bundle to unlimited customer {customer_id}")
        return quota.remaining
    
    if quota.quota_type == "pay_per_use":
        quota.prepaid_balance += scans
        tx_type = "prepaid"
    else:  # monthly
        quota.bonus_scans += scans
        tx_type = "bundle"
    
    # Log transaction
    transaction = QuotaTransaction(
        quota_id=quota.id,
        transaction_type=tx_type,
        amount=scans,
        balance_after=quota.remaining,
        reference_id=reference_id,
        description=description or f"Purchased {scans} additional scans"
    )
    db.add(transaction)
    db.commit()
    
    logger.info(f"Added {scans} scans to customer {customer_id}, new balance: {quota.remaining}")
    
    return quota.remaining


def set_quota_type(
    db: Session,
    customer_id: int,
    quota_type: str,
    monthly_limit: int = None
) -> CustomerQuota:
    """
    Set or change a customer's quota type.
    
    Used when customer upgrades/downgrades plan.
    """
    quota = get_or_create_quota(db, customer_id)
    
    old_type = quota.quota_type
    quota.quota_type = quota_type
    
    if monthly_limit is not None:
        quota.monthly_limit = monthly_limit
    
    if quota_type == "monthly" and not quota.period_start:
        quota.period_start = date.today()
        quota.period_end = date.today() + timedelta(days=30)
    
    # Log the change
    transaction = QuotaTransaction(
        quota_id=quota.id,
        transaction_type="admin",
        amount=0,
        balance_after=quota.remaining,
        description=f"Plan changed from {old_type} to {quota_type}"
    )
    db.add(transaction)
    db.commit()
    
    logger.info(f"Changed customer {customer_id} from {old_type} to {quota_type}")
    
    return quota
