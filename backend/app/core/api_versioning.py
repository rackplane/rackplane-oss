# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Versioning Middleware

Adds standard API version headers to all responses:
- X-API-Version: Current API version (semantic versioning)
- X-API-Version-Major: Major version number for quick compatibility checks
- Deprecation headers when accessing deprecated endpoints (RFC 8594)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Import version constants from single source of truth
from app.core.version import API_VERSION, API_VERSION_MAJOR

# Endpoints with deprecation notices
# Format: path -> (sunset_date, replacement_path)
DEPRECATED_ENDPOINTS = {
    # Add deprecated endpoints here as they occur
    # Example:
    # "/api/v1/old-endpoint": ("2025-06-01", "/api/v1/new-endpoint"),
}


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds API versioning headers to all responses.
    
    Headers added:
    - X-API-Version: Current API version (always)
    - X-API-Version-Major: Major version number (always)
    - Deprecation: RFC 8594 deprecation header (if endpoint is deprecated)
    - Sunset: RFC 8594 sunset header (if endpoint is deprecated)
    - Link: Link to replacement endpoint (if deprecated)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Always add version headers
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-API-Version-Major"] = str(API_VERSION_MAJOR)
        
        # Check for deprecated endpoints
        path = request.url.path
        if path in DEPRECATED_ENDPOINTS:
            sunset_date, replacement = DEPRECATED_ENDPOINTS[path]
            
            # RFC 8594 standard headers
            response.headers["Deprecation"] = "true"
            if sunset_date:
                response.headers["Sunset"] = sunset_date
            if replacement:
                response.headers["Link"] = f'<{replacement}>; rel="successor-version"'
            
            # Also log for monitoring
            logger.warning(f"Deprecated endpoint accessed: {path} by {request.client.host if request.client else 'unknown'}")
        
        return response


def register_deprecation(endpoint: str, sunset_date: str, replacement: Optional[str] = None):
    """
    Register an endpoint as deprecated.
    
    Args:
        endpoint: The path to deprecate (e.g., "/api/v1/old-endpoint")
        sunset_date: Date when the endpoint will be removed (ISO format)
        replacement: Optional replacement endpoint path
    
    Usage:
        from app.core.api_versioning import register_deprecation
        register_deprecation("/api/v1/old", "2025-06-01", "/api/v1/new")
    """
    DEPRECATED_ENDPOINTS[endpoint] = (sunset_date, replacement)


def unregister_deprecation(endpoint: str):
    """Remove a deprecation notice."""
    if endpoint in DEPRECATED_ENDPOINTS:
        del DEPRECATED_ENDPOINTS[endpoint]
