# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Middleware
Extracts tenant_id from JWT token and sets it in context

This middleware is responsible for:
- Extracting tenant_id from JWT tokens in Authorization headers
- Setting tenant_id in request context for automatic query filtering
- Handling public endpoints that don't require authentication
- Fallback to database lookup if tenant_id is missing from token

Architecture:
- Runs on every request before the endpoint handler
- Extracts JWT from Authorization: Bearer <token> header
- Decodes JWT to get tenant_id and username
- Sets tenant_id in context using contextvars
- Context is automatically cleared at start of each request

Security:
- Public endpoints (health, docs, login) skip tenant extraction
- Invalid tokens are logged but don't break the request
- Missing tenant_id triggers database lookup as fallback

Usage:
    Add to FastAPI app:
    from app.core.middleware import TenantMiddleware
    app.add_middleware(TenantMiddleware)
"""

from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from jose import JWTError, jwt
from app.core.config import settings
from app.core.tenant import set_current_tenant_id, clear_tenant_id
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant_id from JWT and set in context.
    
    This middleware processes every request and:
    1. Clears tenant context at start (clean slate)
    2. Skips public endpoints (health, docs, login)
    3. Extracts JWT token from Authorization header
    4. Decodes JWT to get tenant_id
    5. Sets tenant_id in context for automatic query filtering
    
    Public Endpoints (skip tenant extraction):
    - /health
    - /api/docs, /api/redoc, /api/openapi.json
    - /api/v1/auth/login
    - /api/v1/tenants/onboard
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and extract tenant context.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response from the endpoint
        """
        # Clear tenant context at the start of each request
        clear_tenant_id()

        # Skip tenant extraction for public endpoints
        public_paths = [
            "/health",
            "/",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/demo-login",  # Demo auto-login endpoint (public)
            "/api/v1/auth/demo-info",  # Demo info endpoint (public)
            "/api/v1/tenants/onboard",  # Tenant onboarding endpoint (public)
        ]

        if any(request.url.path.startswith(path) for path in public_paths):
            response = await call_next(request)
            return response

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # No token - let the endpoint handle authentication
            response = await call_next(request)
            return response

        token = auth_header.split(" ")[1]

        try:
            # Decode JWT to extract tenant_id
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            tenant_id = payload.get("tenant_id")
            username = payload.get("sub")
            
            logger.info(f"JWT decoded for user={username}, tenant_id={tenant_id}, path={request.url.path}")

            if tenant_id:
                # Set tenant_id in context for this request
                set_current_tenant_id(int(tenant_id))
                logger.info(f"✓ Tenant context set from token: tenant_id={tenant_id} for user={username}")
            else:
                # Token missing tenant_id - fetch from database as fallback
                # Note: We query User without tenant filtering since tenant_id isn't set yet
                logger.warning(f"JWT token missing tenant_id for user={username}, fetching from database")
                from app.core.database import engine
                from app.models.user import User
                from sqlalchemy.orm import sessionmaker
                from sqlalchemy.exc import SQLAlchemyError
                import asyncio
                # Create a session without tenant filtering for this lookup
                # Use execution_options to bypass tenant filtering for this lookup
                temp_session = sessionmaker(bind=engine)()
                try:
                    # Query with timeout protection (statement_timeout is set in engine connect_args)
                    user = temp_session.query(User).execution_options(skip_tenant_filter=True).filter(User.username == username).first()
                    if user and user.tenant_id:
                        set_current_tenant_id(user.tenant_id)
                        logger.info(f"✓ Set tenant_id={user.tenant_id} from database for user={username}")
                    else:
                        logger.error(f"✗ User {username} found but has no tenant_id! This is a data integrity issue.")
                except SQLAlchemyError as e:
                    logger.error(f"✗ Database error fetching tenant_id for user {username}: {e}")
                except Exception as e:
                    logger.error(f"✗ Error fetching tenant_id for user {username}: {e}")
                finally:
                    temp_session.close()
            
            # Verify tenant_id is set
            from app.core.tenant import get_current_tenant_id
            verify_tenant_id = get_current_tenant_id()
            logger.info(f"Verified tenant_id in context: {verify_tenant_id}")

        except JWTError as e:
            # Invalid token - let the endpoint handle it
            logger.warning(f"JWT decode error: {e}")
        except (ValueError, TypeError) as e:
            # Invalid tenant_id format
            logger.warning(f"Invalid tenant_id in token: {e}")
        except Exception as e:
            # Any other error - log but don't break the request
            logger.error(f"Error setting tenant context: {e}", exc_info=True)

        response = await call_next(request)
        return response

