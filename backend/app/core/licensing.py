# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Feature Licensing and Gating
Premium feature access control for subscription-based features

This module provides decorators and utilities for gating premium features
behind subscription tiers. Features are checked against tenant's 
subscription_features JSON field.

Usage:
    from app.core.licensing import require_feature
    
    @require_feature("netbox_bidirectional_sync")
    def premium_function():
        # Only accessible to tenants with this feature enabled
        pass
"""

from functools import wraps
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Callable
import logging

from app.core.tenant import get_current_tenant_id
from app.core.database import get_db

logger = logging.getLogger(__name__)


def require_feature(feature_name: str):
    """
    Decorator to restrict access to premium features.
    
    Checks if the current tenant has access to the specified feature.
    Returns 402 Payment Required if feature is not available.
    
    Args:
        feature_name: Name of the feature to check (e.g., "netbox_bidirectional_sync")
        
    Raises:
        HTTPException: 402 if tenant doesn't have feature access
        HTTPException: 403 if no tenant context available
        
    Example:
        @require_feature("netbox_bidirectional_sync")
        def sync_to_netbox(asset_id: int):
            # This function requires premium subscription
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await _check_feature_access(feature_name)
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to get db from kwargs or create one
            _check_feature_access_sync(feature_name, kwargs.get('db'))
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def _check_feature_access(feature_name: str):
    """Check feature access (async version)"""
    from app.models.tenant import Tenant
    
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        logger.warning(f"Feature check failed: No tenant context for feature '{feature_name}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant context available"
        )
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Query tenant fresh with explicit execution options to ensure we get latest data
        # Use execution_options to bypass any caching and get fresh data from database
        tenant = db.query(Tenant).execution_options(expire_on_commit=True).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Force refresh to get latest subscription_features
        db.refresh(tenant, ['subscription_features', 'subscription_tier'])
        
        if not check_feature_enabled(tenant_id, feature_name, db):
            logger.info(f"Feature access denied: tenant_id={tenant_id}, feature='{feature_name}', tier={tenant.subscription_tier}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Premium feature not available",
                    "feature": feature_name,
                    "message": f"This feature requires a premium subscription. Your current tier is '{tenant.subscription_tier}'.",
                    "upgrade_url": "/api/v1/features/list",
                    "suggestion": f"Upgrade your subscription to access '{feature_name.replace('_', ' ').title()}'"
                }
            )
        
        logger.debug(f"Feature access granted: tenant_id={tenant_id}, feature='{feature_name}'")
    finally:
        db.close()


def _check_feature_access_sync(feature_name: str, db: Session = None):
    """Check feature access (sync version)"""
    from app.models.tenant import Tenant
    
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        logger.warning(f"Feature check failed: No tenant context for feature '{feature_name}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant context available"
        )
    
    # Use provided db or create new one
    if db is None:
        db_gen = get_db()
        db = next(db_gen)
        should_close = True
    else:
        should_close = False
    
    try:
        # Query tenant fresh with explicit execution options to ensure we get latest data
        # Use execution_options to bypass any caching and get fresh data from database
        tenant = db.query(Tenant).execution_options(expire_on_commit=True).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Force refresh to get latest subscription_features
        db.refresh(tenant, ['subscription_features', 'subscription_tier'])
        
        if not check_feature_enabled(tenant_id, feature_name, db):
            logger.info(f"Feature access denied: tenant_id={tenant_id}, feature='{feature_name}', tier={tenant.subscription_tier}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Premium feature not available",
                    "feature": feature_name,
                    "message": f"This feature requires a premium subscription. Your current tier is '{tenant.subscription_tier}'.",
                    "upgrade_url": "/api/v1/features/list",
                    "suggestion": f"Upgrade your subscription to access '{feature_name.replace('_', ' ').title()}'"
                }
            )
        
        logger.debug(f"Feature access granted: tenant_id={tenant_id}, feature='{feature_name}'")
    finally:
        if should_close:
            db.close()


def check_feature_enabled(tenant_id: int, feature_name: str, db: Session) -> bool:
    """
    Check if a tenant has a feature enabled (utility function).
    
    Args:
        tenant_id: Tenant ID to check
        feature_name: Feature to check
        db: Database session
        
    Returns:
        True if feature is enabled, False otherwise
    """
    from app.models.tenant import Tenant
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False
    
    # Expire and refresh to ensure we get the latest data
    db.expire(tenant)
    db.refresh(tenant)
    
    features = getattr(tenant, 'subscription_features', None) or {}

    # Check if feature is explicitly set in subscription_features
    if feature_name in features:
        # Feature is explicitly configured - use that value (could be True or False)
        has_access = features[feature_name]
    else:
        # Feature not explicitly set - check subscription tier defaults
        has_access = False
        tier = (tenant.subscription_tier or "").lower()
        if feature_name == "sku_lookup" and tier in ["pro", "msp", "enterprise"]:
            has_access = True
        elif feature_name == "netbox_bidirectional_sync" and tier in ["pro", "msp", "enterprise"]:
            has_access = True
        elif feature_name == "multi_tenant" and tier in ["msp", "enterprise"]:
            has_access = True

    return has_access
