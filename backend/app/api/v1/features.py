# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Feature Access Endpoints
Check subscription status for commercial features
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Any

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.tenant import Tenant
try:
    from app.bridges.rackplane_services import RackPlaneServicesClient
except ImportError:
    RackPlaneServicesClient = None

router = APIRouter()


@router.get("/check")
async def check_feature_access(
    feature: str = Query(..., description="Feature name to check (e.g., 'ocr_cloud', 'vendor_lookup')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Check if tenant has access to a commercial feature.
    
    Features:
    - ocr_cloud: Cloud OCR (Google Vision, AWS Textract, Azure)
    - ocr_enhanced: Enhanced OCR with vendor identification
    - vendor_lookup: Vendor warranty/config lookup (Dell, HP, etc.)
    - warranty_management: Warranty status and alerts
    - sku_lookup: Vendor SKU catalog for auto-populating asset fields
    
    Returns:
        Dict with has_access, feature name, and subscription tier
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        return {
            "has_access": False,
            "feature": feature,
            "subscription_tier": None,
            "message": "Tenant not found"
        }
    
    # Use centralized licensing logic
    from app.core.licensing import check_feature_enabled
    has_access = check_feature_enabled(tenant.id, feature, db)
    
    return {
        "has_access": has_access,
        "feature": feature,
        "subscription_tier": tenant.subscription_tier,
        "message": f"{feature.replace('_', ' ').title()} is {'available' if has_access else 'not available'} for {tenant.subscription_tier} tier"
    }


@router.get("/list")
async def list_available_features(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    List all commercial features and their access status for current tenant.
    
    Returns:
        Dict with all features and their access status
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        return {
            "subscription_tier": None,
            "features": {}
        }
    
    # Handle missing subscription_features field (if migration not run yet)
    features = getattr(tenant, 'subscription_features', None) or {}
    
    # Define all available features
    all_features = {
        "ocr_cloud": {
            "name": "Cloud OCR",
            "description": "High-accuracy OCR using Google Vision, AWS Textract, or Azure",
            "has_access": features.get("ocr_cloud", False)
        },
        "ocr_enhanced": {
            "name": "Enhanced OCR",
            "description": "OCR with automatic vendor identification",
            "has_access": features.get("ocr_enhanced", False)
        },
        "vendor_lookup": {
            "name": "Vendor Lookup",
            "description": "Automatic warranty and configuration lookup (Dell, HP, Cisco, etc.)",
            "has_access": features.get("vendor_lookup", False)
        },
        "warranty_management": {
            "name": "Warranty Management",
            "description": "Warranty status tracking and expiration alerts",
            "has_access": features.get("warranty_management", False)
        },
        "netbox_bidirectional_sync": {
            "name": "NetBox Bidirectional Sync",
            "description": "Two-way synchronization with NetBox (push changes, conflict resolution)",
            "has_access": features.get("netbox_bidirectional_sync", False),
            "tier_required": "pro"
        },
        "sku_lookup": {
            "name": "SKU Catalog",
            "description": "Vendor SKU catalog for auto-populating asset fields from product SKUs",
            "has_access": features.get("sku_lookup", False) or (tenant.subscription_tier or "").lower() in ["pro", "msp", "enterprise"],
            "tier_required": "pro"
        },
        "multi_tenant": {
            "name": "Multi-Tenancy",
            "description": "Create and manage multiple isolated tenants (for SaaS providers and enterprises)",
            "has_access": features.get("multi_tenant", False),
            "tier_required": "msp"
        }
    }
    
    return {
        "subscription_tier": tenant.subscription_tier,
        "features": all_features,
        "rackplane_api_configured": bool(getattr(tenant, 'rackplane_api_key', None)) if hasattr(tenant, 'rackplane_api_key') else False
    }


@router.get("/usage")
async def get_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get usage statistics for commercial features.
    
    Returns:
        Usage statistics (API calls, costs, etc.)
    """
    try:
        if RackPlaneServicesClient is None:
            raise ImportError("RackPlane Services are not available in this build")
            
        client = RackPlaneServicesClient(db)
        stats = await client.get_usage_stats()
        return stats
    except Exception as e:
        # If service unavailable or API key not configured, return empty stats
        return {
            "status": "unavailable",
            "message": "Usage statistics not available",
            "error": str(e)
        }


@router.get("/health")
async def check_services_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Check health status of RackPlane Services API.
    
    Returns:
        Health status
    """
    try:
        if RackPlaneServicesClient is None:
            raise ImportError("RackPlane Services are not available in this build")
            
        client = RackPlaneServicesClient(db)
        health = await client.health_check()
        return health
    except Exception as e:
        # If service unavailable or API key not configured, return unavailable status
        return {
            "status": "unavailable",
            "message": "RackPlane Services health check failed",
            "error": str(e)
        }

