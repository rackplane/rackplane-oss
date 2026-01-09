# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Context Management
Request-scoped tenant isolation using contextvars

This module provides tenant context management for multi-tenant isolation.
The tenant_id is stored in a context variable that is automatically scoped
to each request, ensuring complete data isolation between tenants.

Architecture:
- Uses Python's contextvars for request-scoped storage
- Tenant ID is set by middleware from JWT token
- All database queries are automatically filtered by tenant_id
- Context is cleared at the start of each request

Usage:
    from app.core.tenant import get_current_tenant_id, set_current_tenant_id
    
    tenant_id = get_current_tenant_id()
    set_current_tenant_id(123)
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store tenant_id for the current request
# This is automatically scoped per request/async task
tenant_context: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)


def get_current_tenant_id() -> Optional[int]:
    """
    Get the current tenant_id from request context.
    
    Returns:
        The tenant_id for the current request, or None if not set.
        
    Note:
        This should always return a value for authenticated requests.
        None indicates the request is public (health check, docs, etc.)
        or there's a configuration issue.
    """
    return tenant_context.get()


def set_current_tenant_id(tenant_id: int) -> None:
    """
    Set the tenant_id in context for the current request.
    
    Args:
        tenant_id: The tenant ID to set in context
        
    Note:
        This is typically called by TenantMiddleware when processing
        JWT tokens. Manual calls are needed for scripts or background tasks.
    """
    tenant_context.set(tenant_id)


def clear_tenant_id() -> None:
    """
    Clear the tenant_id from context.
    
    Note:
        Called at the start of each request by middleware to ensure
        clean context for each request.
    """
    tenant_context.set(None)

