# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Datacenter Inventory Management System - Main Application (OSS)
Comprehensive real-time asset tracking and management platform

This is the main FastAPI application entry point for the OSS version.
It configures:
- FastAPI application with OpenAPI/Swagger documentation
- CORS middleware for cross-origin requests
- Tenant middleware for multi-tenant isolation
- Core API route registration
- Global exception handling
- Application lifespan management

Key Features:
- Multi-tenant architecture with automatic tenant isolation
- RESTful API with comprehensive endpoints
- OpenAPI/Swagger UI documentation
- JWT-based authentication
- Background task support (Celery)

Endpoints:
- /health: Health check endpoint
- /api/docs: Swagger UI documentation
- /api/redoc: ReDoc documentation
- /api/v1/*: All API endpoints
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging
import os
import warnings

# Import API version constant from centralized module
from app.core.version import API_VERSION

# Suppress harmless bcrypt version warning from passlib
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
warnings.filterwarnings("ignore", message=".*bcrypt.*__about__.*")
warnings.filterwarnings("ignore", message=".*trapped.*error.*bcrypt.*")

# Suppress passlib logger warnings
passlib_logger = logging.getLogger("passlib.handlers.bcrypt")
passlib_logger.setLevel(logging.ERROR)

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import TenantMiddleware
from app.api.v1 import (
    assets,
    asset_types,
    locations,
    maintenance,
    workflows,
    reports,
    # netbox_sync,  # Excluded: Premium integration
    # netbox_devicetypes,  # Excluded: Premium integration

    environmental,
    storage_containers,
    network_cables,
    power_cables,
    backup,
    images,
    environments,
    auth,
    users,
    tenants,
    connections,
    stock_boxes,
    audit_logs,
    features,
    photos,
    whitelabel,
    plugins,
    capabilities,
    search,
    csv_import_export,
    vendor_skus,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting Datacenter Inventory Management System (OSS)...")

    # Initialize Dependency Injection Container
    from app.core.container import get_container
    container = get_container()
    logger.info(f"🚀 Running in {container.build_mode.upper()} mode")
    if container.is_oss_build():
        logger.info("📦 OSS build: Premium features disabled")
    else:
        logger.info("💎 Premium build detected (unexpected for OSS main.py)")

    # Create database tables
    try:
        logger.info(f"Creating tables. Registered models: {list(Base.metadata.tables.keys())}")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "already exists" in error_str:
            logger.info(f"Database schema already exists: {type(e).__name__}")
        else:
            logger.error(f"Database initialization failed: {e}")
            raise

    # Run plugin discovery at startup
    from app.plugins.registry import discover_plugins
    discover_plugins()
    
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Datacenter Inventory Management System (OSS)",
    description="AI-powered datacenter hardware and inventory management platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    redirect_slashes=False
)

# Prometheus Instrumentation
if settings.PROMETHEUS_ENABLED:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)


def custom_openapi():
    """Custom OpenAPI schema with security configuration for Swagger UI."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Datacenter Inventory Management System (OSS)",
        version="1.0.0",
        description="AI-powered datacenter hardware and inventory management platform",
        routes=app.routes,
    )
    
    # Add security scheme for Bearer token authentication
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token obtained from /api/v1/auth/login endpoint"
        }
    }
    
    public_paths = ["/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json", "/api/v1/auth/login", "/api/v1/tenants/onboard"]
    
    for path, path_item in openapi_schema.get("paths", {}).items():
        if any(path.startswith(public) for public in public_paths):
            continue
        
        for method in ["get", "post", "put", "delete", "patch"]:
            if method in path_item:
                operation = path_item[method]
                if "security" not in operation:
                    operation["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant middleware
app.add_middleware(TenantMiddleware)

# Request Context middleware
from app.core.context import RequestContextMiddleware
app.add_middleware(RequestContextMiddleware)

# Security Middleware (Headers & Trusted Hosts)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
 
class ConditionalTrustedHostMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_hosts):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)

        host = request.headers.get("host", "")
        if not host:
            return await call_next(request)
        
        host_without_port = host.split(":")[0]
        is_allowed = False
        
        for allowed in self.allowed_hosts:
            if allowed == "*" or allowed == host_without_port:
                is_allowed = True
                break
            if allowed.startswith("*."):
                suffix = allowed[1:]
                if host_without_port.endswith(suffix):
                    is_allowed = True
                    break
        
        if not is_allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"Invalid Host Header: {host_without_port}",
                    "resolution": f"Add '{host_without_port}' to ALLOWED_HOSTS"
                }
            )
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ConditionalTrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# API Versioning Middleware
from app.core.api_versioning import APIVersionMiddleware
app.add_middleware(APIVersionMiddleware)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint"""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "version": API_VERSION, "system": "Datacenter Inventory Management System (OSS)", "database": "connected"}
    except Exception as e:
        return {"status": "starting", "version": API_VERSION, "message": "Services are starting up..."}


@app.get("/", tags=["System"])
async def root():
    return {"message": "Datacenter Inventory Management System API (OSS)", "version": API_VERSION, "documentation": "/api/docs"}


# Include API routers (Core Only)
from app.api.v1 import version
app.include_router(version.router, prefix="/api/version", tags=["API Version"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenant Management"])
app.include_router(whitelabel.router, prefix="/api/v1/whitelabel", tags=["White-Label Configuration"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["Plugin Management"])
app.include_router(users.router, prefix="/api/v1/users", tags=["User Management"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(asset_types.router, prefix="/api/v1/asset-types", tags=["Asset Types"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])
app.include_router(storage_containers.router, prefix="/api/v1/storage-containers", tags=["Storage Containers"])
app.include_router(network_cables.router, prefix="/api/v1/network-cables", tags=["Network Cables"])
app.include_router(power_cables.router, prefix="/api/v1/power-cables", tags=["Power Cables"])

# Network Port Management
from app.api.v1 import network_ports, port_templates, cable_assemblies
app.include_router(network_ports.router, prefix="/api/v1/network-ports", tags=["Network Ports"])
app.include_router(port_templates.router, prefix="/api/v1/port-templates", tags=["Port Templates"])
app.include_router(cable_assemblies.router, prefix="/api/v1/cable-assemblies", tags=["Cable Assemblies"])

app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["Maintenance"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
# app.include_router(netbox_sync.router, prefix="/api/v1/netbox", tags=["NetBox Integration"])
# app.include_router(netbox_devicetypes.router, prefix="/api/v1/netbox-devicetypes", tags=["NetBox Device Types"])

app.include_router(environmental.router, prefix="/api/v1/environmental", tags=["Environmental"])
app.include_router(backup.router, prefix="/api/v1", tags=["Backup & Restore"])
app.include_router(images.router, prefix="/api/v1/images", tags=["Image Processing & OCR"])
app.include_router(photos.router, prefix="/api/v1/photos", tags=["Photo Storage"])
app.include_router(environments.router, prefix="/api/v1/environments", tags=["Environments"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["Connections"])
app.include_router(stock_boxes.router, prefix="/api/v1/stock-boxes", tags=["Stock Boxes"])
app.include_router(audit_logs.router, prefix="/api/v1", tags=["Audit Logs"])
# app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])  # Excluded in OSS
app.include_router(features.router, prefix="/api/v1/features", tags=["Features & Subscriptions"])
app.include_router(capabilities.router, prefix="/api/v1/capabilities", tags=["Capabilities"])


# Contributor Program API
from app.api.v1 import contributor
app.include_router(contributor.router, prefix="/api/v1/contributor", tags=["Contributor Program"])

app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(csv_import_export.router, prefix="/api/v1/csv", tags=["CSV Import/Export"])
app.include_router(vendor_skus.router, prefix="/api/v1/vendor-skus", tags=["Vendor SKU Catalog"])

# Catalog Submissions API
from app.api.v1 import catalog_submissions
app.include_router(catalog_submissions.router, prefix="/api/v1/catalog-submissions", tags=["Catalog Contributions"])

# Generic Order Import API (OSS version only)
from app.api.v1 import order_import
app.include_router(order_import.router, prefix="/api/v1/orders", tags=["Order Import"])



# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        raise exc
    logger.error(f"Global exception: {exc}", exc_info=True)
    error_detail = str(exc) if settings.DEBUG else "An internal server error occurred"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail}
    )
