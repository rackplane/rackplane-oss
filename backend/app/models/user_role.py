# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
User Role Enumeration
Defines user roles and their permissions

Roles:
- SUPER_ADMIN: Full system access, can manage all tenants
- TENANT_ADMIN: Can manage their tenant's data, users, and settings
- USER: Can view and edit assets, locations, etc. within their tenant
- READ_ONLY: Can only view data, cannot make changes
"""

from enum import Enum


class UserRole(str, Enum):
    """
    User role enumeration.
    
    Roles are ordered by permission level (highest to lowest):
    1. SUPER_ADMIN - Full system access
    2. TENANT_ADMIN - Tenant management access
    3. USER - Standard user access
    4. READ_ONLY - View-only access
    """
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    USER = "user"
    READ_ONLY = "read_only"
    
    @classmethod
    def has_permission(cls, user_role: 'UserRole', required_role: 'UserRole') -> bool:
        """
        Check if a user role has permission for a required role.
        
        Permission hierarchy:
        - SUPER_ADMIN has all permissions
        - TENANT_ADMIN has USER and READ_ONLY permissions
        - USER has READ_ONLY permissions
        - READ_ONLY has no additional permissions
        
        Args:
            user_role: The user's role
            required_role: The required role for the operation
            
        Returns:
            True if user has permission, False otherwise
        """
        if user_role == cls.SUPER_ADMIN:
            return True
        
        if required_role == cls.SUPER_ADMIN:
            return False
        
        if user_role == cls.TENANT_ADMIN:
            return required_role in [cls.TENANT_ADMIN, cls.USER, cls.READ_ONLY]
        
        if user_role == cls.USER:
            return required_role in [cls.USER, cls.READ_ONLY]
        
        if user_role == cls.READ_ONLY:
            return required_role == cls.READ_ONLY
        
        return False
    
    @classmethod
    def can_write(cls, user_role: 'UserRole') -> bool:
        """Check if role can write/modify data."""
        return user_role in [cls.SUPER_ADMIN, cls.TENANT_ADMIN, cls.USER]
    
    @classmethod
    def can_manage_users(cls, user_role: 'UserRole') -> bool:
        """Check if role can manage users."""
        return user_role in [cls.SUPER_ADMIN, cls.TENANT_ADMIN]
    
    @classmethod
    def can_manage_tenants(cls, user_role: 'UserRole') -> bool:
        """Check if role can manage tenants."""
        return user_role == cls.SUPER_ADMIN

