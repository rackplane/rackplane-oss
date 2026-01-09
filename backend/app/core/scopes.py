# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Key Scopes
Scope-based access control for API keys

Scopes allow API keys to be restricted to specific functionality.
For example, a print agent API key can be scoped to only printer endpoints.

Scope Format:
- Resource:action (e.g., "printer:read", "printer:write")
- Wildcard: "*" means all scopes (default if scopes is None or empty)

Available Scopes:
- printer:read - Read print jobs (GET /api/v1/print-jobs/pending)
- printer:write - Complete print jobs (POST /api/v1/print-jobs/{id}/complete)
- printer:heartbeat - Send agent heartbeat (POST /api/v1/print-jobs/agents/heartbeat)
- assets:read - Read assets (GET /api/v1/assets)
- assets:write - Write assets (POST/PUT/DELETE /api/v1/assets)

Note: Scope enforcement happens at the endpoint level using FastAPI's Security dependency.
This ensures that even if authentication succeeds, the API key must have the required scope
to access the endpoint.
"""

from fastapi import HTTPException, status, Depends, Security
from fastapi.security import SecurityScopes
from typing import Optional, List
from app.core.auth import get_current_api_key_id, get_current_user
from app.models.api_key import ApiKey
from app.models.user import User
from sqlalchemy.orm import Session
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

# Context variable to store current API key object
_current_api_key: Optional[ApiKey] = None


def get_current_api_key() -> Optional[ApiKey]:
    """Get the current API key object from context."""
    return _current_api_key


def set_current_api_key(api_key: Optional[ApiKey]) -> None:
    """Set the current API key object in context."""
    global _current_api_key
    _current_api_key = api_key


def check_scope(required_scope: str, api_key: Optional[ApiKey]) -> bool:
    """
    Check if an API key has the required scope.
    
    Args:
        required_scope: The required scope (e.g., "printer:read")
        api_key: The API key object (None if not using API key auth)
        
    Returns:
        True if scope is allowed, False otherwise
        
    Rules:
        - If api_key is None (user auth), always allow (users have all permissions)
        - If api_key.scopes is None or empty list, allow all (backward compatibility)
        - If api_key.scopes contains "*", allow all
        - If api_key.scopes contains the exact required_scope, allow
        - Otherwise, deny
    """
    # If not using API key (user auth), allow (users have full permissions)
    if api_key is None:
        return True
    
    # If scopes is None or empty, allow all (backward compatibility)
    if not api_key.scopes:
        return True
    
    # If scopes contains "*", allow all
    if "*" in api_key.scopes:
        return True
    
    # Check if required scope is in the list
    return required_scope in api_key.scopes


async def get_current_api_key_with_scopes(
    security_scopes: SecurityScopes,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[ApiKey]:
    """
    FastAPI Security dependency to get current API key and validate scopes.
    
    This is the dependency to use with FastAPI's Security() for endpoint-level scope enforcement.
    
    Usage:
        @router.get("/printer/jobs", dependencies=[Security(get_current_api_key_with_scopes, scopes=["printer:read"])])
        async def get_print_jobs(api_key: Optional[ApiKey] = Depends(get_current_api_key_with_scopes)):
            ...
    
    Args:
        security_scopes: FastAPI SecurityScopes object (automatically injected)
        db: Database session
        current_user: Current user (if authenticated via user token)
        
    Returns:
        ApiKey object if authenticated via API key, None if authenticated via user token
        
    Raises:
        HTTPException: 403 if API key doesn't have required scopes
    """
    # Get API key ID from context (set during authentication)
    api_key_id = get_current_api_key_id()
    
    # If not using API key (user auth), return None (users have all permissions)
    if api_key_id is None:
        return None
    
    # Get the API key object
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    
    if not api_key:
        logger.warning(f"get_current_api_key_with_scopes: API key {api_key_id} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if API key is active
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate scopes if required
    if security_scopes.scopes:
        for required_scope in security_scopes.scopes:
            if not check_scope(required_scope, api_key):
                logger.warning(
                    f"get_current_api_key_with_scopes: API key {api_key_id} missing required scope '{required_scope}'. "
                    f"Has: {api_key.scopes}, Required: {security_scopes.scopes}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key does not have required scope: {required_scope}. "
                           f"Required scopes: {', '.join(security_scopes.scopes)}. "
                           f"Key has scopes: {api_key.scopes or 'all (no restrictions)'}",
                    headers={"WWW-Authenticate": f'Bearer scope="{required_scope}"'},
                )
    
    return api_key

