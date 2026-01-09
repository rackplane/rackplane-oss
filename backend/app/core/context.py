# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Request Context Management
Provides thread-local storage for request information using ContextVars.

This module ensures that audit logging and other deep-service functions
can access request-level metadata (IP, User Agent, User ID) without
needing to pass these values through every function call.
"""

from contextvars import ContextVar
from typing import Optional
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# Context Variables
_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default=None)
_ip_address_ctx_var: ContextVar[Optional[str]] = ContextVar("ip_address", default=None)
_user_agent_ctx_var: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)
_user_id_ctx_var: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
_username_ctx_var: ContextVar[Optional[str]] = ContextVar("username", default=None)
_tenant_id_ctx_var: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)


# Getters
def get_request_id() -> str:
    return _request_id_ctx_var.get()

def get_ip_address() -> Optional[str]:
    return _ip_address_ctx_var.get()

def get_user_agent() -> Optional[str]:
    return _user_agent_ctx_var.get()

def get_context_user_id() -> Optional[int]:
    return _user_id_ctx_var.get()

def get_context_username() -> Optional[str]:
    return _username_ctx_var.get()

def get_context_tenant_id() -> Optional[int]:
    return _tenant_id_ctx_var.get()

# Setters (primarily for internal use / middleware)
def set_context_user(user_id: int, username: str, tenant_id: int):
    _user_id_ctx_var.set(user_id)
    _username_ctx_var.set(username)
    _tenant_id_ctx_var.set(tenant_id)


class RequestContextMiddleware(BaseHTTPMiddleware):
        """
        Middleware to capture request metadata and store it in ContextVars.
        
        This allows services to access IP and User Agent information implicitly,
        enabling reliable audit logging even when these details aren't passed explicitly.
        """
        
        async def dispatch(self, request: Request, call_next):
            # Generate or capture Request ID
            request_id = request.headers.get("X-Request-ID") or str(uuid4())
            _request_id_ctx_var.set(request_id)
            
            # Capture IP Address
            # Trust X-Forwarded-For if behind proxy, otherwise fallback to client host
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip = forwarded_for.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else None
            _ip_address_ctx_var.set(ip)
            
            # Capture User Agent
            _user_agent_ctx_var.set(request.headers.get("User-Agent"))
            
            # Reset user context (will be set by Auth middleware later if applicable)
            _user_id_ctx_var.set(None)
            _username_ctx_var.set(None)
            _tenant_id_ctx_var.set(None)
            
            # Add Request ID to response headers
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            
            return response
