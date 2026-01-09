# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Application Configuration
Centralized settings management using Pydantic

This module provides application-wide configuration settings loaded from
environment variables. All settings are type-safe and validated using Pydantic.

Key Configuration Areas:
- Database connection settings
- Security (JWT, secrets)
- CORS and API settings
- Integration settings (NetBox, printers)
- Thresholds for capacity and environmental monitoring
- Feature flags

Usage:
    from app.core.config import settings
    database_url = settings.DATABASE_URL
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
import ipaddress
import os
import socket
import warnings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables or .env file.
    Settings are validated on load and provide type safety.
    
    Environment Variables:
        All settings can be set via environment variables with the same name.
        For example: DATABASE_URL=postgresql://... will override the default.
    """

    # Application
    APP_NAME: str = "RackPlane"
    """Application name displayed in API documentation"""
    APP_VERSION: str = "1.0.0"
    """Application version string"""
    DEBUG: bool = False
    """Enable debug mode (shows detailed error messages)"""

    # Database
    DATABASE_URL: str = "postgresql://dcms:dcms_password@db:5432/datacenter_inventory"
    """PostgreSQL connection string. Format: postgresql://user:password@host:port/database"""
    
    SERVICES_DATABASE_URL: str = ""
    """Global services database URL. Falls back to DATABASE_URL if not set."""
    
    @model_validator(mode='before')
    @classmethod
    def fix_database_url_scheme(cls, values):
        """Convert postgres:// to postgresql:// for SQLAlchemy 2.0 compatibility.
        
        Fly.io and some other services use the deprecated postgres:// scheme.
        SQLAlchemy 2.0 requires postgresql://
        
        Also: SERVICES_DATABASE_URL falls back to DATABASE_URL if not explicitly set.
        """
        db_url = values.get('DATABASE_URL', '')
        if db_url.startswith('postgres://'):
            values['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)
            db_url = values['DATABASE_URL']
        
        # SERVICES_DATABASE_URL falls back to DATABASE_URL if not set
        services_db_url = values.get('SERVICES_DATABASE_URL', '')
        if not services_db_url:
            services_db_url = db_url
            values['SERVICES_DATABASE_URL'] = services_db_url
        elif services_db_url.startswith('postgres://'):
            values['SERVICES_DATABASE_URL'] = services_db_url.replace('postgres://', 'postgresql://', 1)
        return values
    
    # Infrastructure
    RDS_PROXY_HOST: str = ""
    """RDS Proxy endpoint for connection pooling (optional)"""
    MULTI_AZ_ENABLED: bool = False
    """Enable Multi-AZ deployment optimizations"""
    PROMETHEUS_ENABLED: bool = True
    """Enable Prometheus metrics exposure"""

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    """Redis connection URL for caching and task queue"""

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    """Secret key for JWT token signing. MUST be changed in production!"""
    ALGORITHM: str = "HS256"
    """JWT signing algorithm"""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    """JWT token expiration time in minutes"""
    DEMO_LOGIN_ENABLED: bool = True
    """Enable demo auto-login feature. Set to True to enable demo login endpoints."""
    DEMO_LOGIN_KEY: str = ""
    """Demo login key for automatic authentication in demo environments. Only works if DEMO_LOGIN_ENABLED=True. Leave empty to disable."""

    # CORS - Restricted for security
    # When using nginx reverse proxy, CORS is not needed (same origin)
    # Only allow specific origins for direct API access if needed
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    """List of allowed CORS origins. Use nginx reverse proxy to avoid CORS issues."""

    # Trusted Host Middleware - Prevents Host header injection attacks
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    """List of allowed host/domain names. Prevents host header injection attacks.

    Security: Never use wildcard "*" as it disables protection entirely.

    Configuration:
    - Development (DEBUG=True): Host IPs are auto-detected and added automatically.
    - Production (DEBUG=False): Must explicitly set via environment variable with JSON array:
      ALLOWED_HOSTS='["api.example.com", "example.com", "www.example.com"]'

    Auto-Detection in Development (DEBUG=True):
    - HOST_IP environment variable (recommended: set in .env or docker-compose)
    - Default gateway IP (Linux only, via /proc/net/route)
    - Docker host.docker.internal DNS resolution
    - Container hostname and resolved IPs

    On macOS/Windows, set HOST_IP in .env since /proc/net/route is unavailable.

    Attacks Prevented:
    - Host header injection
    - Password reset poisoning
    - Web cache poisoning
    - SSRF via Host header manipulation

    Example production .env:
      ALLOWED_HOSTS='["api.rackplane.io", "rackplane.io"]'
    """

    # GitHub Integration (for NetBox devicetype-library)
    GITHUB_TOKEN: str = ""
    """GitHub personal access token for increased API rate limits (optional)"""
    DEVICETYPE_CACHE_DIR: str = "/tmp/devicetype_cache"
    """Directory for caching NetBox devicetype-library data"""
    DEVICETYPE_CACHE_TTL: int = 3600
    """Cache TTL in seconds for device type data (default: 1 hour)"""
    NETBOX_LIBRARY_MAX_FILE_SIZE: int = 5 * 1024 * 1024
    """Maximum YAML file size in bytes (default: 5MB)"""
    NETBOX_LIBRARY_VENDOR_NAME: str = "NetBox Library"
    """Vendor name used for imported NetBox device types"""
    
    # RackPlane Services API (Commercial Features)
    RACKPLANE_SERVICES_URL: str = "https://services.rackplane.com/api/v1"
    """RackPlane Services API URL for commercial features (OCR, vendor lookup, etc.)"""
    RACKPLANE_SERVICES_API_KEY: str = ""
    """API Key for authenticating with RackPlane Services"""
    RACKPLANE_ADMIN_SECRET: str = ""
    """Admin secret for registering customers on services.rackplane.com"""
    RACKPLANE_SYNC_SECRET: str = ""
    """Restricted secret key for catalog sync operations"""
    
    # File Storage
    UPLOAD_DIR: str = "/app/uploads"
    """Directory for uploaded files (photos, documents) - fallback if MinIO not available"""
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    """Maximum file upload size in bytes"""
    
    # MinIO Object Storage
    MINIO_ENDPOINT: str = "minio:9000"
    """MinIO server endpoint (hostname:port)"""
    MINIO_ACCESS_KEY: str = "minioadmin"
    """MinIO access key"""
    MINIO_SECRET_KEY: str = "minioadmin"
    """MinIO secret key"""
    MINIO_SECURE: bool = False
    """Use HTTPS for MinIO (False for local development)"""
    MINIO_BUCKET_NAME: str = "rackplane-photos"
    """Default bucket name for photos"""
    MINIO_USE_SSL: bool = False
    """Use SSL/TLS for MinIO connections"""

    # Demo / Seeding
    DEMO_SEED_ENABLED: bool = False
    """Allow demo seeding endpoints when DEBUG is False"""
    DEMO_MODE: bool = False
    """Enable general demo mode features (e.g. local catalog)"""

    # Audit Log Retention
    AUDIT_RETENTION_DAYS: int = 365
    """Number of days to retain audit logs."""

    # Capacity Thresholds
    RACK_SPACE_WARNING_THRESHOLD: float = 0.80  # 80%
    """Rack space utilization threshold for warnings (0.0-1.0)"""
    POWER_WARNING_THRESHOLD: float = 0.80  # 80%
    """Power capacity utilization threshold for warnings (0.0-1.0)"""
    COOLING_WARNING_THRESHOLD: float = 0.80  # 80%
    """Cooling capacity utilization threshold for warnings (0.0-1.0)"""

    # Environmental Thresholds
    TEMP_MIN_WARNING: float = 18.0  # Celsius
    """Minimum temperature threshold for warnings (Celsius)"""
    TEMP_MAX_WARNING: float = 27.0  # Celsius
    """Maximum temperature threshold for warnings (Celsius)"""
    HUMIDITY_MIN_WARNING: float = 40.0  # Percent
    """Minimum humidity threshold for warnings (percent)"""
    HUMIDITY_MAX_WARNING: float = 60.0  # Percent
    """Maximum humidity threshold for warnings (percent)"""

    # Predictive Maintenance
    ENABLE_PREDICTIVE_MAINTENANCE: bool = True
    """Enable AI-powered predictive maintenance features"""
    MAINTENANCE_CHECK_INTERVAL_HOURS: int = 24
    """Interval between maintenance checks (hours)"""

    # Asset Lifecycle
    EOL_WARNING_DAYS: int = 90
    """Days before end-of-life to show warnings"""
    WARRANTY_WARNING_DAYS: int = 30
    """Days before warranty expiration to show warnings"""

    # Email Alerts
    ENABLE_EMAIL_ALERTS: bool = True
    """Enable email alerts for low stock, maintenance, warranty"""
    LOW_STOCK_ALERT_ENABLED: bool = True
    """Enable low stock email alerts"""
    MAINTENANCE_ALERT_ENABLED: bool = True
    """Enable maintenance due email alerts"""
    WARRANTY_ALERT_ENABLED: bool = True
    """Enable warranty expiring email alerts"""

    @model_validator(mode='after')
    def validate_production_settings(self):
        """
        Validate critical settings for production environments.
        
        Security: Prevents deployment with insecure default credentials.
        In production (DEBUG=False), raises ValueError if default keys are used.
        In development (DEBUG=True), logs a warning.
        """
        # Detect cloud environment (Fly.io sets FLY_APP_NAME)
        fly_app_name = os.environ.get('FLY_APP_NAME')
        is_cloud_deployment = fly_app_name is not None
        
        # Check if ALLOWED_HOSTS is still at default localhost-only values
        default_allowed_hosts = ["localhost", "127.0.0.1"]
        has_default_allowed_hosts = set(self.ALLOWED_HOSTS) == set(default_allowed_hosts)
        
        if self.DEBUG:
            # Check for defaults and warn in DEBUG mode
            if "dcms_password" in self.DATABASE_URL:
                 warnings.warn(
                    "DATABASE_URL uses default 'dcms_password'. Change this in production!",
                    UserWarning, stacklevel=2
                )
            if self.MINIO_ACCESS_KEY == "minioadmin" or self.MINIO_SECRET_KEY == "minioadmin":
                warnings.warn(
                    "MinIO credentials use default 'minioadmin'. Change this in production!",
                    UserWarning, stacklevel=2
                )
            if self.SECRET_KEY == "your-secret-key-change-in-production":
                warnings.warn(
                    "SECRET_KEY is using default value. This is insecure in production!",
                    UserWarning, stacklevel=2
                )
            # Warn about ALLOWED_HOSTS in cloud deployment
            if is_cloud_deployment and has_default_allowed_hosts:
                warnings.warn(
                    f"ALLOWED_HOSTS is set to localhost-only defaults but running on Fly.io (app: {fly_app_name}). "
                    f"Set ALLOWED_HOSTS to include your domain, e.g., ALLOWED_HOSTS='[\"localhost\", \"127.0.0.1\", \"{fly_app_name}.fly.dev\"]'",
                    UserWarning, stacklevel=2
                )
                
        else:
            # Enforce security in Production mode
            errors = []
            
            if self.SECRET_KEY == "your-secret-key-change-in-production":
                errors.append("SECRET_KEY must be changed from default value.")
                
            if "dcms_password" in self.DATABASE_URL:
                errors.append("DATABASE_URL contains default 'dcms_password'.")
                
            if self.MINIO_ACCESS_KEY == "minioadmin" or self.MINIO_SECRET_KEY == "minioadmin":
                errors.append("MinIO credentials use default 'minioadmin'.")
            
            # Require ALLOWED_HOSTS to be configured for cloud deployments
            if is_cloud_deployment and has_default_allowed_hosts:
                errors.append(
                    f"ALLOWED_HOSTS must be configured for cloud deployment. "
                    f"Running on Fly.io (app: {fly_app_name}). "
                    f"Set: ALLOWED_HOSTS='[\"localhost\", \"127.0.0.1\", \"{fly_app_name}.fly.dev\"]'"
                )
            
            # Ensure ALLOWED_HOSTS is not empty in production
            if not self.ALLOWED_HOSTS:
                errors.append("ALLOWED_HOSTS cannot be empty in production.")
            
            if errors:
                raise ValueError(
                    "Security Check Failed (Production Mode):\n" + "\n".join(errors) +
                    "\nSet environment variables to secure values or enable DEBUG mode."
                )
        return self

    @model_validator(mode='after')
    def auto_detect_allowed_hosts(self):
        """
        Auto-detect and add host IPs to ALLOWED_HOSTS in development mode.
        In production mode, warn if detected host IP is not in ALLOWED_HOSTS.

        When DEBUG=True, automatically detects and adds:
        - HOST_IP environment variable (if set in docker-compose/.env)
        - Default gateway IP (host machine when running in Docker on Linux)
        - Docker host.docker.internal DNS resolution
        - Container hostname and its resolved IPs

        When DEBUG=False (production), detects host IP and warns if not configured.
        This helps customers understand why they can't access the system.

        Security: Only auto-adds hosts in DEBUG mode. All detected values are
        validated as proper IP addresses before being added.
        
        Platform Note: Gateway detection via /proc/net/route only works on Linux.
        On macOS/Windows, use HOST_IP environment variable or host.docker.internal.
        """
        def is_valid_ip(ip_str: str) -> bool:
            """Validate that a string is a valid IPv4 or IPv6 address."""
            try:
                ipaddress.ip_address(ip_str)
                return True
            except ValueError:
                return False

        def get_default_gateway_ip() -> str | None:
            """
            Get the default gateway IP from /proc/net/route.
            
            Note: This only works on Linux systems. On macOS/Windows, this will
            return None and the HOST_IP environment variable should be used instead.
            """
            try:
                with open('/proc/net/route', 'r') as f:
                    for line in f:
                        fields = line.strip().split()
                        if len(fields) >= 3 and fields[1] == '00000000':  # Default route
                            gateway_hex = fields[2]
                            gateway_bytes = bytes.fromhex(gateway_hex)
                            gateway_ip = '.'.join(str(b) for b in reversed(gateway_bytes))
                            if is_valid_ip(gateway_ip):
                                return gateway_ip
            except (FileNotFoundError, PermissionError, ValueError):
                # /proc/net/route not available (macOS, Windows, or restricted container)
                pass
            return None

        def detect_host_ips() -> set[str]:
            """
            Detect potential host IPs from environment.
            Only returns validated IP addresses.
            """
            detected = set()
            
            # Method 1: Check HOST_IP environment variable (most reliable, user-configured)
            host_ip_env = os.environ.get('HOST_IP')
            if host_ip_env and is_valid_ip(host_ip_env):
                detected.add(host_ip_env)

            # Method 2: Get default gateway (Linux only)
            gateway_ip = get_default_gateway_ip()
            if gateway_ip:  # Already validated in get_default_gateway_ip
                detected.add(gateway_ip)

            # Method 3: Try Docker's host.docker.internal DNS (works on Docker Desktop)
            try:
                docker_host_ip = socket.gethostbyname('host.docker.internal')
                if docker_host_ip and is_valid_ip(docker_host_ip):
                    detected.add(docker_host_ip)
            except socket.gaierror:
                pass

            return detected

        try:
            detected_ips = detect_host_ips()
            
            if self.DEBUG:
                # Development mode - auto-add detected hosts
                hosts_to_add = set(self.ALLOWED_HOSTS)
                
                # Add validated detected IPs
                hosts_to_add.update(detected_ips)
                
                # Add container hostname and its resolved IPs
                hostname = socket.gethostname()
                if hostname:
                    hosts_to_add.add(hostname)
                    try:
                        hostname_ips = socket.getaddrinfo(hostname, None)
                        for ip_info in hostname_ips:
                            ip = ip_info[4][0]
                            # Filter out IPv6 link-local and validate
                            if not ip.startswith('fe80') and not ip.startswith('::'):
                                if is_valid_ip(ip):
                                    hosts_to_add.add(ip)
                    except socket.gaierror:
                        pass

                self.ALLOWED_HOSTS = sorted(list(hosts_to_add))
            else:
                # Production mode - check if detected IPs are in ALLOWED_HOSTS and warn if not
                missing_ips = [ip for ip in detected_ips if ip not in self.ALLOWED_HOSTS]
                
                if missing_ips:
                    missing_str = ', '.join(missing_ips)
                    current_hosts = ', '.join(self.ALLOWED_HOSTS[:5])
                    if len(self.ALLOWED_HOSTS) > 5:
                        current_hosts += f" ... (+{len(self.ALLOWED_HOSTS) - 5} more)"
                    
                    warnings.warn(
                        f"ALLOWED_HOSTS Configuration Notice:\n"
                        f"  Detected host IP(s) not in ALLOWED_HOSTS: {missing_str}\n"
                        f"  If you cannot access the application from these IPs, add them to your .env:\n"
                        f"  ALLOWED_HOSTS='[\"localhost\", \"127.0.0.1\", \"{missing_ips[0]}\"]'\n"
                        f"  Current ALLOWED_HOSTS: {current_hosts}",
                        UserWarning, stacklevel=2
                    )

        except Exception as e:
            warnings.warn(
                f"Failed to auto-detect ALLOWED_HOSTS: {e}. Using defaults.",
                UserWarning, stacklevel=2
            )

        return self

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
"""Global settings instance. Import this to access configuration."""

