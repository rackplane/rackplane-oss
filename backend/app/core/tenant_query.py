# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Query Helper
Utility functions to ensure tenant filtering is applied

This module provides helper functions to explicitly apply tenant filters
to database queries. While automatic filtering is handled by database event
listeners, explicit filtering provides additional security and clarity.

Security Note:
    This function will return an empty result set if tenant_id is not set,
    preventing accidental data leakage between tenants.

Usage:
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(Asset)
    query = apply_tenant_filter(query, Asset)
    assets = query.all()
"""

from sqlalchemy.orm import Query
from app.core.tenant import get_current_tenant_id
import logging

logger = logging.getLogger(__name__)


def apply_tenant_filter(query: Query, model_class) -> Query:
    """
    Apply tenant_id filter to a query if the model has tenant_id.
    
    This function ensures tenant isolation by adding a WHERE clause that
    filters results by the current tenant_id. If tenant_id is not set in
    context, it returns an empty result set for security.
    
    Args:
        query: SQLAlchemy query object to filter
        model_class: The model class being queried (for logging/validation)
        
    Returns:
        Query with tenant_id filter applied, or empty result set if no tenant_id
        
    Security:
        CRITICAL: This must be called for all queries to ensure tenant isolation.
        If tenant_id is None, returns query.filter(False) to prevent data leakage.
        
    Example:
        query = db.query(Asset).filter(Asset.status == 'active')
        query = apply_tenant_filter(query, Asset)
        # Now query only returns assets for the current tenant
    """
    tenant_id = get_current_tenant_id()
    
    if tenant_id is None:
        logger.error(
            f"SECURITY WARNING: No tenant_id in context - blocking query for {model_class.__name__}!"
        )
        # Return empty result set for security - don't expose data
        # This should never happen if middleware is working correctly
        return query.filter(False)  # This will return no results
    
    if hasattr(model_class, 'tenant_id'):
        # Always apply tenant filter - don't check if already applied (safer)
        filtered_query = query.filter(model_class.tenant_id == tenant_id)
        logger.debug(f"Applied tenant_id={tenant_id} filter to {model_class.__name__}")
        return filtered_query
    
    # Model doesn't have tenant_id (e.g., Tenant model itself)
    return query

