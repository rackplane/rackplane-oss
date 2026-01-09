# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
API Version Endpoint

Provides version information and API stability guarantees.
This endpoint helps clients understand:
- Current API version
- Supported API versions
- Deprecation notices
- Changelog location
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import List, Optional, Dict

# Import version constants from single source of truth
from app.core.version import (
    API_VERSION,
    API_VERSION_MAJOR,
    API_VERSION_MINOR,
    API_VERSION_PATCH,
    CHANGELOG_URL,
    get_migration_guide_url,
)

router = APIRouter()

# API Release date (keep with endpoint-specific metadata)
API_RELEASED_DATE = "2024-12-01"

# Supported versions (for future multi-version support)
SUPPORTED_VERSIONS = [
    {
        "version": "v1",
        "status": "stable",
        "released": "2024-12-01",
        "deprecated": None,
        "sunset": None,
        "description": "Current stable API version"
    }
]

# Deprecation notices for specific endpoints
DEPRECATION_NOTICES: Dict[str, Dict] = {
    # Example format:
    # "/api/v1/old-endpoint": {
    #     "deprecated_at": "2024-12-01",
    #     "sunset_at": "2025-06-01",
    #     "replacement": "/api/v1/new-endpoint",
    #     "reason": "Endpoint consolidated with new-endpoint"
    # }
}


class VersionInfo(BaseModel):
    """API version information"""
    version: str
    version_major: int
    version_minor: int
    version_patch: int
    released: str
    status: str = "stable"


class SupportedVersion(BaseModel):
    """Information about a supported API version"""
    version: str
    status: str  # "stable", "deprecated", "sunset"
    released: str
    deprecated: Optional[str] = None
    sunset: Optional[str] = None  # Date when version will be removed
    description: str


class DeprecationNotice(BaseModel):
    """Deprecation notice for an endpoint"""
    endpoint: str
    deprecated_at: str
    sunset_at: Optional[str] = None
    replacement: Optional[str] = None
    reason: str

class VersionResponse(BaseModel):
    """Full API version response"""
    api_version: str
    api_version_full: VersionInfo
    supported_versions: List[SupportedVersion]
    deprecation_notices: List[DeprecationNotice]
    documentation_url: str
    changelog_url: str


class HealthVersionResponse(BaseModel):
    """Simple version for health checks"""
    version: str
    status: str


class CompatibilityResponse(BaseModel):
    """API compatibility check response"""
    compatible: bool
    current_version: Optional[str] = None
    client_version: Optional[str] = None
    status: Optional[str] = None  # "supported", "deprecated", "unsupported"
    message: Optional[str] = None
    migration_guide: Optional[str] = None
    error: Optional[str] = None
    expected_format: Optional[str] = None


@router.get("", response_model=VersionResponse)
def get_api_version():
    """
    Get full API version information.
    
    Returns detailed version information including:
    - Current API version
    - All supported API versions with their status
    - Active deprecation notices
    - Links to documentation and changelog
    
    Use this endpoint to:
    - Check API compatibility before making requests
    - Get notified of upcoming deprecations
    - Find documentation resources
    """
    deprecation_list = [
        DeprecationNotice(
            endpoint=endpoint,
            deprecated_at=info["deprecated_at"],
            sunset_at=info.get("sunset_at"),
            replacement=info.get("replacement"),
            reason=info["reason"]
        )
        for endpoint, info in DEPRECATION_NOTICES.items()
    ]
    
    return VersionResponse(
        api_version=f"v{API_VERSION_MAJOR}",
        api_version_full=VersionInfo(
            version=API_VERSION,
            version_major=API_VERSION_MAJOR,
            version_minor=API_VERSION_MINOR,
            version_patch=API_VERSION_PATCH,
            released=API_RELEASED_DATE,
            status="stable"
        ),
        supported_versions=[
            SupportedVersion(**v) for v in SUPPORTED_VERSIONS
        ],
        deprecation_notices=deprecation_list,
        documentation_url="/api/docs",
        changelog_url=CHANGELOG_URL
    )


@router.get("/check", response_model=HealthVersionResponse)
def check_version():
    """
    Quick version check endpoint.
    
    Lightweight endpoint for health checks and version verification.
    Returns minimal version info with low overhead.
    """
    return HealthVersionResponse(
        version=API_VERSION,
        status="stable"
    )


@router.get("/compatibility/{client_version}", response_model=CompatibilityResponse)
def check_compatibility(client_version: str, response: Response) -> CompatibilityResponse:
    """
    Check if a client version is compatible with this API.
    
    Args:
        client_version: Client's expected API version (e.g., "1.0.0", "v1")
        
    Returns:
        Compatibility status and any necessary migration steps.
    
    Response Headers:
        - X-API-Version: Current API version
        - X-API-Deprecated: "true" if client version is deprecated
        - X-API-Sunset-Date: Date when client version support ends
    """
    # Add version headers
    response.headers["X-API-Version"] = API_VERSION
    
    # Normalize version input
    normalized = client_version.lower().strip()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    
    # Check major version compatibility
    try:
        if "." in normalized:
            client_major = int(normalized.split(".")[0])
        else:
            client_major = int(normalized)
    except ValueError:
        return CompatibilityResponse(
            compatible=False,
            error=f"Invalid version format: {client_version}",
            expected_format="v1, 1, or 1.0.0"
        )
    
    # Check if version is supported
    if client_major == API_VERSION_MAJOR:
        return CompatibilityResponse(
            compatible=True,
            current_version=API_VERSION,
            client_version=client_version,
            status="supported",
            message="Client version is fully compatible"
        )
    elif client_major < API_VERSION_MAJOR:
        response.headers["X-API-Deprecated"] = "true"
        return CompatibilityResponse(
            compatible=False,
            current_version=API_VERSION,
            client_version=client_version,
            status="deprecated",
            message=f"API v{client_major} is deprecated. Please upgrade to v{API_VERSION_MAJOR}.",
            migration_guide=get_migration_guide_url(client_major, API_VERSION_MAJOR)
        )
    else:
        return CompatibilityResponse(
            compatible=False,
            current_version=API_VERSION,
            client_version=client_version,
            status="unsupported",
            message=f"API v{client_major} is not yet available. Current version is v{API_VERSION_MAJOR}."
        )
