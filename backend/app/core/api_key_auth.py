# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Key Authentication Module

Provides authentication and logging for the RackPlane Central Services API.
Validates customer API keys and logs all requests for analytics.

Usage:
    from app.core.api_key_auth import get_api_customer
    
    @router.get("/protected-endpoint")
    async def protected(customer: ApiCustomer = Depends(get_api_customer)):
        # customer is verified and logged
        return {"message": f"Hello {customer.customer_name}"}
"""

import hashlib
import time
import logging
from datetime import datetime
from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_services_db
from app.core.config import settings

logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA256.
    
    Args:
        api_key: Plaintext API key
        
    Returns:
        SHA256 hash of the key (64 character hex string)
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a new random API key.
    
    Returns:
        A 32-character random API key (rk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
    """
    import secrets
    return f"rk_{secrets.token_hex(16)}"


async def verify_api_key(
    api_key: str,
    db: Session
) -> Optional["ApiCustomer"]:
    """
    Verify an API key and return the customer if valid.
    
    Args:
        api_key: Plaintext API key from request
        db: Database session
        
    Returns:
        ApiCustomer if valid, None if invalid
    """
    from app.models.api_customer import ApiCustomer
    
    key_hash = hash_api_key(api_key)
    
    customer = db.query(ApiCustomer).filter(
        ApiCustomer.api_key_hash == key_hash,
        ApiCustomer.is_active == True
    ).first()
    
    if customer:
        # Check expiration
        if customer.expires_at and customer.expires_at < datetime.utcnow():
            logger.warning(f"Expired API key for customer {customer.id}")
            return None
        
        # Update last_used_at
        customer.last_used_at = datetime.utcnow()
        db.commit()
        
    return customer


async def log_api_usage(
    customer_id: int,
    request: Request,
    db: Session,
    endpoint: str,
    status_code: int = 200,
    response_time_ms: int = 0,
    error_message: str = None
):
    """
    Log an API request for analytics and billing.
    
    Args:
        customer_id: Customer who made the request
        request: FastAPI request object
        db: Database session
        endpoint: API endpoint path
        status_code: HTTP response status
        response_time_ms: Request processing time
        error_message: Error message if failed
    """
    from app.models.api_customer import ApiUsageLog
    
    log_entry = ApiUsageLog(
        customer_id=customer_id,
        endpoint=endpoint,
        method=request.method,
        status_code=status_code,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
        request_params=dict(request.query_params),
        response_time_ms=response_time_ms,
        error_message=error_message
    )
    
    db.add(log_entry)
    db.commit()





async def get_api_customer(
    request: Request,
    db: Session = Depends(get_services_db)  # Use services DB for API keys
) -> "ApiCustomer":
    """
    FastAPI dependency to verify API key and get customer.
    """
    from app.models.api_customer import ApiCustomer
    
    start_time = time.time()
    
    # Extract API key from header
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    
    # Verify key
    customer = await verify_api_key(api_key, db)
    
    if not customer:
        client_host = request.client.host if request.client else "unknown"
        logger.warning(f"Invalid API key attempt from {client_host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    # Log successful access
    response_time_ms = int((time.time() - start_time) * 1000)
    await log_api_usage(
        customer_id=customer.id,
        request=request,
        db=db,
        endpoint=str(request.url.path),
        status_code=200,
        response_time_ms=response_time_ms
    )
    
    return customer


async def get_api_customer_or_sync_secret(
    request: Request,
    db: Session = Depends(get_services_db)
) -> "ApiCustomer":
    """
    Dependency that allows EITHER a valid API Key OR a valid Sync Secret.
    
    The Sync Secret bypasses normal API Key validation and rate limiting
    to ensure critical system syncs always succeed if the secret is known.
    
    For sync-secret authentication, we return a synthetic "SystemPrincipal"
    object that is NOT bound to any real ApiCustomer row, avoiding coupling
    the identity to arbitrary PK ordering or mutable database contents.
    """
    from dataclasses import dataclass
    
    @dataclass
    class SystemPrincipal:
        """
        Synthetic principal used for sync-secret authentication.
        
        This is intentionally not persisted in the database and should only
        be used for internal/system operations where we need an identity
        object but do not want to couple to any particular ApiCustomer row.
        """
        id: int
        customer_name: str
        is_active: bool
        rate_limit_hour: int
        is_system: bool = True
    
    # 1. Check for Sync Secret first (highest priority)
    sync_secret = request.headers.get("X-Sync-Secret")
    if sync_secret and settings.RACKPLANE_SYNC_SECRET:
        if sync_secret == settings.RACKPLANE_SYNC_SECRET:
            # Return a synthetic, deterministic principal instead of a real DB row
            logger.info(f"Access granted via RACKPLANE_SYNC_SECRET for {request.url.path}")
            return SystemPrincipal(
                id=0,  # System operations use ID 0
                customer_name="system-sync",
                is_active=True,
                rate_limit_hour=999999,  # Effectively unlimited
            )

    # 2. Fall back to normal API Key validation
    return await get_api_customer(request, db)


def get_optional_api_customer(
    request: Request,
    db: Session = Depends(get_services_db)  # Use services DB for API keys
) -> Optional["ApiCustomer"]:
    """
    Optional version - returns None instead of raising if no key.
    
    Useful for endpoints that work differently for authenticated vs anonymous.
    """
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return None
    
    try:
        # Use sync query for optional version
        from app.models.api_customer import ApiCustomer
        key_hash = hash_api_key(api_key)
        customer = db.query(ApiCustomer).filter(
            ApiCustomer.api_key_hash == key_hash,
            ApiCustomer.is_active == True
        ).first()
        return customer
    except Exception as e:
        logger.warning(f"Error verifying optional API key: {e}")
        return None
