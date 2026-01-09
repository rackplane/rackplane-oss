# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Schemas
Pydantic models for tenant management

This module defines Pydantic schemas for tenant (organization/customer) management.
Schemas are used for request/response validation in tenant management endpoints.

Key Schemas:
- TenantBase: Base fields shared across tenant schemas
- TenantCreate: Schema for creating new tenants (onboarding)
- TenantUpdate: Schema for updating existing tenants
- TenantResponse: Schema for API responses
- TenantWithUsers: Tenant response including user list
- UserAssignTenant: Schema for assigning users to tenants

Validation:
- Name: 1-200 characters
- Slug: 1-100 characters, lowercase alphanumeric with hyphens only
- Subscription tiers: community, starter, pro, msp
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TenantBase(BaseModel):
    """
    Base tenant schema with common fields.
    
    This is the base class for all tenant-related schemas. It contains
    fields that are common across create, update, and response schemas.
    """
    name: str = Field(..., min_length=1, max_length=200, description="Tenant display name")
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="URL-friendly identifier (lowercase, alphanumeric, hyphens only)")
    subscription_tier: str = Field(default="starter", max_length=50, description="Subscription tier: community, starter, pro, msp")
    contact_email: Optional[str] = Field(None, max_length=200, description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Primary contact phone")
    vertical_pack: str = Field(default="datacenter", max_length=50, description="Active vertical pack: datacenter, healthcare, warehouse")


class TenantCreate(TenantBase):
    """
    Schema for creating a new tenant.
    
    Used in POST /api/v1/tenants/onboard endpoint (public endpoint for
    tenant onboarding). All fields from TenantBase are required.
    """
    pass


class TenantUpdate(BaseModel):
    """
    Schema for updating an existing tenant.
    
    Used in PUT/PATCH /api/v1/tenants/{id} endpoint. All fields are optional.
    Only provided fields will be updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Tenant display name")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="URL-friendly identifier")
    is_active: Optional[bool] = Field(None, description="Whether tenant account is active")
    subscription_tier: Optional[str] = Field(None, max_length=50, description="Subscription tier")
    contact_email: Optional[str] = Field(None, max_length=200, description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Primary contact phone")
    vertical_pack: Optional[str] = Field(None, max_length=50, description="Vertical pack preset")


class TenantResponse(TenantBase):
    """
    Schema for tenant API responses.
    
    Used in GET /api/v1/tenants endpoints. Includes all tenant information
    plus metadata like user count.
    """
    id: int = Field(..., description="Tenant ID")
    is_active: bool = Field(..., description="Whether tenant account is active")
    created_at: datetime = Field(..., description="Tenant creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    user_count: Optional[int] = Field(None, description="Number of users in this tenant")
    branding_config: Optional[dict] = Field(None, description="White-label branding configuration")
    terminology: Optional[dict] = Field(None, description="Custom UI terminology")

    class Config:
        from_attributes = True


class TenantWithUsers(TenantResponse):
    """
    Tenant response schema including user list.
    
    Used in GET /api/v1/tenants/{id} endpoint when including users.
    Contains all tenant information plus a list of associated users.
    """
    users: List['UserResponse'] = Field(default=[], description="List of users in this tenant")

    class Config:
        from_attributes = True


class UserAssignTenant(BaseModel):
    """
    Schema for assigning a user to a tenant.
    
    Used in POST /api/v1/users/{id}/assign-tenant endpoint. Allows
    super admins to assign users to different tenants.
    """
    tenant_id: int = Field(..., description="Tenant ID to assign user to")


class TenantSettingsUpdate(BaseModel):
    """
    Schema for updating tenant settings.
    
    Used in PUT /api/v1/tenants/current/settings endpoint. All fields are optional.
    Only provided fields will be updated.
    """
    show_dev_troubleshooting: Optional[bool] = Field(None, description="Whether to show DEV Troubleshooting button")
    enable_debug_logs: Optional[bool] = Field(None, description="Whether to enable debug logging")
    rackplane_api_key: Optional[str] = Field(None, max_length=255, description="RackPlane Services API key (rk_xxx)")


class TenantSettingsResponse(BaseModel):
    """
    Schema for tenant settings API responses.
    
    Used in GET /api/v1/tenants/current/settings endpoint. Returns current
    tenant-wide settings.
    """
    show_dev_troubleshooting: bool = Field(default=False, description="Whether to show DEV Troubleshooting button")
    enable_debug_logs: bool = Field(default=False, description="Whether to enable debug logging")
    rackplane_api_key_configured: bool = Field(default=False, description="Whether API key is configured")
    rackplane_api_key_preview: Optional[str] = Field(None, description="Masked API key (rk_xxxx...xxxx)")
    rackplane_cloud_connected: bool = Field(default=False, description="Whether actually connected to RackPlane Cloud (tested)")
    contributor_program_enrolled: bool = Field(default=False, description="Whether tenant is enrolled in contributor program")
    subscription_tier: str = Field(default="community", description="Current subscription tier")

    class Config:
        from_attributes = True


# Import here to avoid circular dependency
from app.schemas.user import UserResponse
TenantWithUsers.model_rebuild()

