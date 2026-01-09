# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
User Schemas
Pydantic models for user and authentication

This module defines Pydantic schemas for user management and authentication.
Schemas are used for request/response validation in FastAPI endpoints.

Key Schemas:
- UserBase: Base fields shared across user schemas
- UserCreate: Schema for creating new users
- UserUpdate: Schema for updating existing users
- UserResponse: Schema for API responses
- Token: JWT token response
- LoginRequest: Login endpoint request
- PasswordReset: Password reset request

Validation:
- Username: 3-100 characters
- Password: 6-100 characters (will be hashed before storage)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.user_role import UserRole


class UserBase(BaseModel):
    """
    Base user schema with common fields.
    
    This is the base class for all user-related schemas. It contains
    fields that are common across create, update, and response schemas.
    """
    username: str = Field(..., min_length=3, max_length=100, description="Login username (unique per tenant)")


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Used in POST /api/v1/users endpoint. The password will be hashed
    using bcrypt before storage.
    
    Note:
        If tenant_id is not provided, the user will be assigned to the
        current user's tenant (from JWT token).
        If role is not provided, defaults to USER.
    """
    password: str = Field(..., min_length=6, max_length=100, description="Plain text password (will be hashed)")
    tenant_id: Optional[int] = Field(None, description="Tenant ID (defaults to current user's tenant if not provided)")
    role: Optional[UserRole] = Field(UserRole.USER, description="User role (super_admin, tenant_admin, user, read_only)")


class UserUpdate(BaseModel):
    """
    Schema for updating an existing user.
    
    Used in PUT/PATCH /api/v1/users/{id} endpoint. All fields are optional.
    Only provided fields will be updated.
    """
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="New password (will be hashed)")
    role: Optional[UserRole] = Field(None, description="User role (super_admin, tenant_admin, user, read_only)")
    is_active: Optional[bool] = Field(None, description="Whether user account is active")


class UserResponse(UserBase):
    """
    Schema for user API responses.
    
    Used in GET /api/v1/users endpoints. Includes all user information
    except the password hash (for security).
    """
    id: int = Field(..., description="User ID")
    tenant_id: Optional[int] = Field(None, description="Tenant ID")
    role: str = Field(..., description="User role (super_admin, tenant_admin, user, read_only)")
    is_active: bool = Field(..., description="Whether user account is active")
    is_super_admin: bool = Field(..., description="Legacy super admin flag (for backward compatibility)")
    ui_preferences: Optional[dict] = Field(default=None, description="UI preferences (nav bar layout, theme, etc.)")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class Token(BaseModel):
    """
    JWT token response schema.
    
    Used in POST /api/v1/auth/login endpoint. Returns the access token
    and token type (always "bearer").
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class TokenData(BaseModel):
    """
    Token payload data extracted from JWT.
    
    Used internally for JWT token validation. Contains the username
    (subject) from the token payload.
    """
    username: Optional[str] = Field(None, description="Username from token (subject)")


class LoginRequest(BaseModel):
    """
    Login request schema.
    
    Used in POST /api/v1/auth/login endpoint. Validates username and
    password for authentication.
    """
    username: str = Field(..., description="Login username")
    password: str = Field(..., description="Login password")


class PasswordReset(BaseModel):
    """
    Password reset request schema.
    
    Used in POST /api/v1/auth/reset-password endpoint. Validates the
    new password before updating.
    """
    new_password: str = Field(..., min_length=6, max_length=100, description="New password (will be hashed)")
