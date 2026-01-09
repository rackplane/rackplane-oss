# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Capabilities API Endpoint

Returns feature availability based on BUILD_MODE and tenant subscription tier.
Used by the frontend CapabilityContext to determine which features to display.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.container import get_container
from app.models.user import User
from app.models.tenant import Tenant
try:
    from app.services.license_service import LicenseService
except ImportError:
    LicenseService = None

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_capabilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get tenant capabilities based on BUILD_MODE and subscription tier.
    
    Returns feature availability for the frontend CapabilityContext.
    - In OSS builds, premium features return False.
    - In premium builds, features are based on tenant's subscription tier.
    
    Response format:
    {
        "build_mode": "oss" | "premium",
        "tier": "community" | "starter" | "pro" | "msp",
        "features": {
            "feature_name": true | false | { "enabled": bool, ... }
        }
    }
    """
    container = get_container()
    is_oss = container.is_oss_build()
    
    # Get tenant tier
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    tier = tenant.subscription_tier if tenant else "community"
    
    # Get features from LicenseService (single source of truth)
    license_service = LicenseService(db)
    
    if is_oss:
        # OSS build: Use community tier features, override premium to disabled
        features = license_service.get_tier_features("community")
        # Ensure all premium features are explicitly disabled
        features.update({
            "ocr_cloud": {"enabled": False, "reason": "Premium feature"},
            "global_catalog": False,
            "vendor_apis": False,
            "cloud_backup": False,
            "multi_tenant": False,
            "admin_portal": False,
            "sku_lookup": False,
            "label_printing": False,
        })
        tier = "community"
    else:
        # Premium build: Use actual tenant tier
        features = license_service.get_tier_features(tier)
    
    return {
        "build_mode": "oss" if is_oss else "premium",
        "tier": tier,
        "features": features
    }


@router.get("/check/{feature}")
async def check_feature(
    feature: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Check if a specific feature is available.
    
    Args:
        feature: Feature key to check (e.g., "ocr_cloud", "sku_lookup")
    
    Returns:
        {
            "feature": "ocr_cloud",
            "available": false,
            "reason": "Premium feature"
        }
    """
    capabilities = await get_capabilities(db, current_user)
    features = capabilities["features"]
    
    value = features.get(feature)
    
    # Determine availability based on value type
    if isinstance(value, dict):
        available = value.get("enabled", False)
        reason = value.get("reason", "") if not available else ""
    elif isinstance(value, bool):
        available = value
        reason = "Not available in your tier" if not available else ""
    elif value is None:
        available = False
        reason = "Unknown feature"
    else:
        available = bool(value)
        reason = ""
    
    return {
        "feature": feature,
        "available": available,
        "reason": reason
    }
