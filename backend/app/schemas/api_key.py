# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Key Schemas
Pydantic models for API key requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    label: Optional[str] = Field(None, max_length=100, description="Human-readable label (e.g., 'Warehouse Relay')")
    scopes: Optional[List[str]] = Field(None, description="List of allowed scopes. Empty list or None = all scopes. Example: ['printer:read', 'printer:write', 'assets:read']")


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key."""
    label: Optional[str] = Field(None, max_length=100, description="Human-readable label")
    is_active: Optional[bool] = Field(None, description="Whether the key is active (kill switch)")
    scopes: Optional[List[str]] = Field(None, description="List of allowed scopes. Empty list = all scopes")


class ApiKeyResponse(BaseModel):
    """Schema for API key response (does not include the actual key)."""
    id: int
    user_id: int
    label: Optional[str]
    last_used_at: Optional[datetime]
    is_active: bool
    scopes: Optional[List[str]] = Field(None, description="List of allowed scopes. Empty list = all scopes")
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    """Schema for API key creation response (includes the key once)."""
    id: int
    user_id: int
    label: Optional[str]
    key: str = Field(..., description="The API key (shown only once - save it now!)")
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

