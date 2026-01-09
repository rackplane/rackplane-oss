# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Tenant Model
Multi-tenancy support for SaaS architecture

This model represents a tenant (organization/customer) in the multi-tenant system.
Each tenant has isolated data and can have multiple users. The tenant_id is used
throughout the application to ensure complete data isolation.

Key Features:
- Unique name and slug for identification
- Subscription tier management
- Active/inactive status
- Contact information

Note:
    This model does NOT inherit from TenantMixin because it is the root tenant
    table itself. All other models inherit TenantMixin to reference this table.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, event
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional
import uuid as uuid_lib
from app.core.database import Base


class Tenant(Base):
    """
    Tenant model for multi-tenancy isolation.
    
    Represents an organization/customer that uses the DCMS system. All data
    in the system is scoped to a tenant, ensuring complete isolation between
    different customers.
    
    Attributes:
        id: Primary key
        uuid: Globally unique identifier for central services tracking
        name: Display name of the tenant (e.g., "Acme Corporation")
        slug: URL-friendly identifier (e.g., "acme-corp")
        is_active: Whether the tenant account is active
        subscription_tier: Subscription level (free, standard, premium, enterprise)
        contact_email: Primary contact email
        contact_phone: Primary contact phone
        created_at: Timestamp when tenant was created
        updated_at: Timestamp when tenant was last updated
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)

    # Unique identifier for cross-instance tracking (services.rackplane.com)
    uuid = Column(String(36), unique=True, nullable=False, index=True,
                  default=lambda: str(uuid_lib.uuid4()),
                  comment="Globally unique tenant identifier for central services")

    name = Column(String(200), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True, comment="URL-friendly identifier")
    
    # Subscription and Status
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether tenant account is active")
    subscription_tier = Column(String(50), default="community", comment="Subscription level: community, starter, pro, msp")
    
    # Tenant Settings (JSON field for flexible configuration)
    tenant_settings = Column(JSON, default=lambda: {
        "show_dev_troubleshooting": False,  # Default: OFF (tenant-wide setting)
        "enable_debug_logs": False  # Default: OFF (tenant-wide setting)
    }, nullable=True, comment="Tenant-wide settings (UI preferences, feature flags, etc.)")
    
    # Metadata
    contact_email = Column(String(200), nullable=True, comment="Primary contact email")
    contact_phone = Column(String(50), nullable=True, comment="Primary contact phone")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Subscription Features (added by migration)
    subscription_features = Column(JSON, default={}, nullable=True, comment="Enabled premium features")
    
    # RackPlane Services API Key (added by migration)
    # Note: Changed to Text() to support JWT license tokens (600+ characters)
    rackplane_api_key = Column(Text(), nullable=True, comment="API key for RackPlane Services (supports JWT tokens)")
    rackplane_api_key_hash = Column(String(255), nullable=True, comment="Hashed API key for security")
    
    # Stripe Integration
    stripe_customer_id = Column(String(255), nullable=True, comment="Stripe Customer ID for billing")
    subscription_status = Column(String(50), default="demo", comment="Current subscription status: demo, active, past_due, cancelled")
    
    # Subscription Renewal Tracking (added by migration)
    subscription_renewal_date = Column(DateTime(timezone=True), nullable=True, 
        comment="Next billing date from Stripe (current_period_end)")
    subscription_grace_days = Column(Integer, default=3, nullable=True,
        comment="Grace days after renewal date before online features expire")

    # ========== White-Label Configuration ==========
    
    # Branding Configuration
    branding_config = Column(JSON, default=lambda: {
        "name": None,  # White-label product name (e.g., "MercyTrack")
        "logo_url": None,
        "favicon_url": None,
        "primary_color": "#6366f1",  # Default indigo
        "secondary_color": "#4f46e5",
        "accent_color": "#818cf8",
        "font_family": "Inter",
        "custom_domain": None,
        "email_from_name": None,
        "email_from_address": None
    }, nullable=True, comment="White-label branding configuration (logo, colors, domain, etc.)")

    # Terminology Configuration
    terminology = Column(JSON, default=lambda: {}, nullable=True, comment="Configurable UI terminology (item->Supply, bin->Cabinet, etc.)")

    # Vertical Pack
    vertical_pack = Column(String(50), default="datacenter", index=True,
        comment="Active vertical pack: datacenter, healthcare, warehouse")

    # Feature Flags for Vertical-Specific Features
    vertical_features = Column(JSON, default=lambda: {
        "expiration_tracking": False,
        "par_levels": False,
        "lot_tracking": False,
        "department_attribution": False
    }, nullable=True, comment="Vertical-specific feature flags (expiration_tracking, par_levels, etc.)")

    # Plugin Configuration
    plugin_config = Column(JSON, default=lambda: {
        "plugins": []
    }, nullable=True, comment="Per-tenant plugin configuration and enablement state")

    @property
    def subscription_expires_at(self) -> Optional[datetime]:
        """
        Calculate subscription expiration from renewal date + grace days.
        
        Returns:
            datetime when subscription expires, or None if no renewal date set
        """
        if not self.subscription_renewal_date:
            return None
        grace_days = self.subscription_grace_days if self.subscription_grace_days is not None else 3
        return self.subscription_renewal_date + timedelta(days=grace_days)

    def has_feature(self, feature_name: str) -> bool:
        """
        Check if tenant has access to a premium feature.
        
        Args:
            feature_name: Name of the feature (e.g., "netbox_bidirectional_sync")
            
        Returns:
            True if feature is enabled, False otherwise
        """
        features = self.subscription_features or {}
        return features.get(feature_name, False)

    def get_term(self, key: str, default: str = None) -> str:
        """
        Get terminology value for a key.
        
        Args:
            key: Terminology key (e.g., "item", "bin", "check_out")
            default: Default value if key not found
            
        Returns:
            Configured term or default value
        """
        terms = self.terminology or {}
        return terms.get(key, default or key)

    def has_vertical_feature(self, feature_name: str) -> bool:
        """
        Check if a vertical-specific feature is enabled.
        
        Args:
            feature_name: Feature name (e.g., "expiration_tracking", "par_levels")
            
        Returns:
            True if feature is enabled for this tenant's vertical pack
        """
        features = self.vertical_features or {}
        return features.get(feature_name, False)

    def get_branding(self, key: str, default: str = None) -> str:
        """
        Get branding configuration value.
        
        Args:
            key: Branding key (e.g., "primary_color", "logo_url")
            default: Default value if key not found
            
        Returns:
            Configured branding value or default
        """
        branding = self.branding_config or {}
        return branding.get(key, default)

    def get_display_name(self) -> str:
        """
        Get display name for the white-labeled product.
        
        Returns:
            Custom branding name or default "RackPlane"
        """
        branding = self.branding_config or {}
        return branding.get("name") or "RackPlane"

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"


# Event handler to ensure UUID is always set before insert
@event.listens_for(Tenant, 'before_insert')
def receive_before_insert(mapper, connection, target):
    """Ensure UUID is set before inserting a new tenant."""
    if not target.uuid:
        target.uuid = str(uuid_lib.uuid4())
