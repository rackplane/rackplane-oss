# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

# Optional premium bridges (may not exist in OSS builds)
try:
    from app.bridges.fs_client import FSService
    from app.bridges.fs_rate_limiter import FSRateLimiter
except ImportError:
    FSService = None
    FSRateLimiter = None

from app.services.product_parser import ProductParserService
from app.services.catalog_service import CatalogService

# Services Layer
