# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Onboarding Schemas
Pydantic models for tenant onboarding (signup flow)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re


class DatacenterOnboarding(BaseModel):
    """Schema for datacenter creation during onboarding"""
    name: str = Field(..., min_length=1, max_length=200, description="Datacenter name")
    code: str = Field(..., min_length=1, max_length=100, description="Datacenter code (e.g., DC1, PRIMARY)")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)


class RackOnboarding(BaseModel):
    """Schema for rack creation during onboarding"""
    name: str = Field(..., min_length=1, max_length=200, description="Rack name")
    code: str = Field(..., min_length=1, max_length=50, description="Rack code (e.g., A1, RACK-01)")
    datacenter_code: str = Field(..., description="Code of the datacenter this rack belongs to")
    room_code: Optional[str] = Field(None, description="Room code (optional)")
    height_u: Optional[int] = Field(42, ge=1, le=100, description="Rack height in U (default: 42)")
    row: Optional[str] = Field(None, max_length=20, description="Row identifier")
    position: Optional[str] = Field(None, max_length=20, description="Position identifier")


class TenantOnboardingRequest(BaseModel):
    """Schema for tenant onboarding (signup)"""
    # Tenant information
    company_name: str = Field(..., min_length=1, max_length=200, description="Company/Organization name")
    company_slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="URL-friendly identifier (auto-generated if not provided)")
    contact_email: Optional[str] = Field(None, max_length=200, description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Primary contact phone")
    
    # First user (admin) information
    admin_username: str = Field(..., min_length=3, max_length=100, description="Username for the first admin user (display name, tenant-scoped)")
    admin_email: str = Field(..., max_length=200, description="Email for the first admin user (required, used for login)")
    admin_password: str = Field(..., min_length=8, max_length=100, description="Password for the first admin user (minimum 8 characters, NIST recommended)")
    
    # Subscription tier (defaults to starter)
    subscription_tier: str = Field(default="starter", max_length=50, description="Subscription tier (community, starter, pro, msp)")
    
    # Vertical pack (defaults to datacenter)
    vertical_pack: str = Field(default="datacenter", max_length=50, description="Industry vertical (datacenter, healthcare, warehouse)")
    
    # Optional: Datacenters and racks to create during onboarding
    datacenters: Optional[List[DatacenterOnboarding]] = Field(None, description="List of datacenters to create")
    racks: Optional[List[RackOnboarding]] = Field(None, description="List of racks to create")
    
    @field_validator('contact_email', 'admin_email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format if provided"""
        if v is None:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v


class TenantOnboardingResponse(BaseModel):
    """Response schema for tenant onboarding"""
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    user_id: int
    username: str
    access_token: str
    token_type: str = "bearer"
    message: str
    datacenters: Optional[List[dict]] = Field(default_factory=list, description="Created datacenters")
    racks: Optional[List[dict]] = Field(default_factory=list, description="Created racks")

