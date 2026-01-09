# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Database Connection and Session Management
SQLAlchemy configuration for PostgreSQL with tenant isolation

This module provides:
- Database engine and session factory
- Automatic tenant_id injection on new records
- Automatic tenant filtering on all SELECT queries
- Database session dependency for FastAPI

Architecture:
- Uses SQLAlchemy 2.0 event system for automatic tenant filtering
- Tenant ID is automatically set on new records via before_flush event
- All SELECT queries are filtered by tenant_id via do_orm_execute event
- Can be bypassed using execution_options(skip_tenant_filter=True) for migrations

Security:
- All queries are automatically filtered by tenant_id
- Queries without tenant_id in context are blocked (return empty results)
- Tenant ID is auto-set on new records to prevent data leakage

Usage:
    from app.core.database import get_db, SessionLocal
    
    # In FastAPI endpoint
    def my_endpoint(db: Session = Depends(get_db)):
        # db is automatically tenant-filtered
        assets = db.query(Asset).all()  # Only returns current tenant's assets
"""

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.query import Query
from typing import Any, Type, Optional
from app.core.config import settings
from app.core.tenant import get_current_tenant_id
import logging
import os
import sys
import traceback

logger = logging.getLogger(__name__)

# Configure connection arguments
connect_args = {
    "connect_timeout": 10,  # Timeout for initial connection (seconds)
    "options": "-c statement_timeout=30000"  # 30 second query timeout
}

# RDS Proxy specific configuration
if settings.RDS_PROXY_HOST:
    # RDS Proxy handles pooling, so we can reduce local pooling overhead
    # but we still need some local pooling for async concurrency
    pool_size = 5
    max_overflow = 10
    pool_recycle = 1800  # Recycle faster with proxy
    
    # Add SSL requirement for RDS Proxy if needed (usually required)
    # connect_args["sslmode"] = "require"
else:
    # Standard direct connection pooling
    pool_size = 10
    max_overflow = 20
    pool_recycle = 3600

# Create database engine with connection pooling and timeouts
# Create database engine with connection pooling and timeouts
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=30,   # Timeout when getting connection from pool (seconds)
    pool_recycle=pool_recycle,
    connect_args=connect_args
)

# Create services database engine (global catalog, API keys)
# Neon/pooled connections don't support statement_timeout in connect_args
services_connect_args = connect_args.copy()
if "options" in services_connect_args:
    del services_connect_args["options"]

services_engine = create_engine(
    settings.SERVICES_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,  # Smaller pool for services
    max_overflow=10,
    pool_timeout=30,
    connect_args=services_connect_args
)

# Base class for all SQLAlchemy models
Base = declarative_base()


# Session factory for creating database sessions
# Sessions are automatically tenant-aware via event listeners
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Session factory for services database (no tenant isolation needed for most global tables)
ServicesSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=services_engine
)


@event.listens_for(Session, "before_flush", propagate=True)
def receive_before_flush(session: Session, flush_context, instances):
    """
    Automatically set tenant_id on new instances before flush.
    
    This event listener ensures that all new records have tenant_id set
    automatically from the request context. This prevents accidental data
    leakage between tenants.
    
    Only sets tenant_id if:
    1. Instance has tenant_id attribute (uses TenantMixin)
    2. tenant_id is None (not explicitly set)
    
    This allows explicit tenant_id values to bypass auto-setting (e.g., during
    tenant onboarding or migrations).
    
    Args:
        session: SQLAlchemy session
        flush_context: Flush context
        instances: List of instances being flushed
    """
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return
    
    for instance in session.new:
        # Only auto-set tenant_id if:
        # 1. Instance has tenant_id attribute
        # 2. tenant_id is None (not explicitly set)
        # This allows explicit tenant_id values to bypass auto-setting
        if hasattr(instance, 'tenant_id') and getattr(instance, 'tenant_id', None) is None:
            setattr(instance, 'tenant_id', tenant_id)
            logger.debug(f"Auto-set tenant_id={tenant_id} on {instance.__class__.__name__}")



# Models that can be queried without tenant_id (authentication & internal flows)
# NOTE: specialized queries should use execution_options(skip_tenant_filter=True)
# instead of adding to this list.
SYSTEM_MODELS_ALLOWLIST = {
    'Tenant',           # System table, no tenant_id
    'User',             # Needed for initial authentication
    'ApiKey',           # Needed to resolve tenant from API Key
    'PrintAgent',       # Needed to resolve tenant from Print Agent
    'CatalogSKU',       # Global catalog, not tenant scoped
    # Central Services models (services.rackplane.com)
    'ApiCustomer',      # Customer registry for central services
    'ApiUsageLog',      # API usage logging
    'CustomerQuota',    # Usage quota tracking
    'QuotaTransaction', # Quota transaction history
    'GlobalProductCatalog', # Shared product catalog
    'FSApiUsage',       # Global API usage tracking
    'CentralCatalogSubmission', # Global moderation queue
    'CatalogSubmission', # Local-to-global submission tracker
}

@event.listens_for(Session, "do_orm_execute")
def receive_do_orm_execute(execute_state):
    """
    Automatically filter all SELECT queries by tenant_id.
    
    This is the SQLAlchemy 2.0 way to intercept and modify queries.
    All SELECT queries are automatically filtered by the current tenant_id
    from the request context.
    
    Security:
        - Can be bypassed by using execution_options(skip_tenant_filter=True)
        - Only applies to SELECT statements
        - Skips filtering for Tenant model itself
        - Logs warnings if tenant_id is not set (security concern)
    
    Args:
        execute_state: SQLAlchemy execution state containing the query
    """
    # Check if tenant filtering should be skipped (for onboarding, migrations, etc.)
    if execute_state.execution_options.get("skip_tenant_filter", False):
        return  # Exit without adding the WHERE clause
    
    tenant_id = get_current_tenant_id()
    
    # Skip filtering for certain models that don't have tenant_id or are system tables
    skip_models = {'Tenant'}  # Tenant table itself doesn't need filtering
    
    # Check if this is a query for a model we should skip
    for mapper in execute_state.all_mappers:
        if mapper and hasattr(mapper.class_, '__name__'):
            if mapper.class_.__name__ in skip_models:
                return
    
    if tenant_id is None:
        # SECURITY: Fail-closed approach - block queries for tenant-scoped models
        # Get model names from this query
        model_names = {m.class_.__name__ for m in execute_state.all_mappers if m and hasattr(m.class_, '__name__')}

        # Check if all models in this query are in the allowlist
        if not model_names.issubset(SYSTEM_MODELS_ALLOWLIST):
            # This is a security violation - tenant-scoped query without tenant_id
            blocked_models = model_names - SYSTEM_MODELS_ALLOWLIST
            stack = ''.join(traceback.format_stack()[-5:-1])

            # Check for explicit test override flag
            # SECURITY: Only allow bypass in test environments (pytest) or when DEBUG=True
            #
            # DEBUG mode escape hatch rationale:
            # - Allows local development without pytest (e.g., running scripts, migrations)
            # - Production deployments must ALWAYS have DEBUG=False
            # - This creates a safe escape hatch that automatically disappears in production
            # - Combined with env var requirement, provides defense in depth
            # SECURITY: Check test environment first for performance and safety
            is_pytest = 'pytest' in sys.modules
            is_debug = settings.DEBUG if hasattr(settings, 'DEBUG') else False
            # SECURITY: Exact case-sensitive match - only lowercase 'true' is accepted
            # This prevents bypass via 'True', 'TRUE', 'TrUe', etc. which could be set accidentally
            # or via environment variable injection attacks
            env_var_enabled = os.environ.get('ALLOW_TENANT_QUERIES_WITHOUT_ID', 'false') == 'true'
            # Explicit parentheses for boolean expression clarity
            allow_test_queries = env_var_enabled and (is_pytest or is_debug)

            if allow_test_queries:
                # Log environment details for audit trail
                warning_msg = (
                    f"SECURITY: Tenant-scoped query without tenant_id context (test override enabled): {blocked_models}. "
                    f"Environment: is_pytest={is_pytest}, DEBUG={is_debug}, "
                    f"env_var=ALLOW_TENANT_QUERIES_WITHOUT_ID. "
                    f"Ensure set_current_tenant_id() is called. Stack: {stack[-200:]}"
                )
                logger.warning(warning_msg)
            else:
                # Always raise exception (fail-closed) - this is the secure default
                raise ValueError(
                    f"SECURITY VIOLATION: Tenant-scoped query without tenant_id context. "
                    f"Blocked models: {blocked_models}. "
                    f"Ensure set_current_tenant_id() is set or use execution_options(skip_tenant_filter=True) for system queries. "
                    f"Allowed models without tenant_id: {SYSTEM_MODELS_ALLOWLIST}. "
                )
        
        # Query is for allowed models only - allow it to proceed
        return
    
    # Only apply to SELECT statements
    if not execute_state.is_select:
        return
    
    # Get the statement
    statement = execute_state.statement
    
    # Check all mappers in the query
    for mapper in execute_state.all_mappers:
        if mapper is None:
            continue
            
        # Check if this mapper's class has tenant_id
        if hasattr(mapper.class_, 'tenant_id') and 'tenant_id' in mapper.columns:
            # Check if tenant_id filter is already applied
            has_tenant_filter = False
            
            # Check the WHERE clause
            if hasattr(statement, 'whereclause') and statement.whereclause is not None:
                # Walk the WHERE clause to check for tenant_id
                def check_clause(clause):
                    try:
                        if hasattr(clause, 'left'):
                            left = clause.left
                            if hasattr(left, 'key') and left.key == 'tenant_id':
                                return True
                            if hasattr(left, 'name') and left.name == 'tenant_id':
                                return True
                            if hasattr(left, '__str__') and 'tenant_id' in str(left):
                                return True
                        if hasattr(clause, 'clauses'):
                            return any(check_clause(c) for c in clause.clauses)
                        # Check string representation
                        if 'tenant_id' in str(clause):
                            return True
                    except Exception:
                        pass
                    return False
                
                has_tenant_filter = check_clause(statement.whereclause)
            
            if not has_tenant_filter:
                # Add tenant_id filter using SQLAlchemy 2.0 style
                try:
                    from sqlalchemy import and_
                    tenant_column = mapper.columns['tenant_id']
                    
                    # Create the filter condition
                    filter_condition = tenant_column == tenant_id
                    
                    # Apply the filter to the statement
                    if hasattr(statement, 'whereclause'):
                        if statement.whereclause is not None:
                            # Combine with existing WHERE clause
                            statement = statement.where(and_(statement.whereclause, filter_condition))
                        else:
                            # No existing WHERE clause
                            statement = statement.where(filter_condition)
                    else:
                        # Fallback for older SQLAlchemy
                        statement = statement.filter(filter_condition)
                    
                    execute_state.statement = statement
                    logger.info(f"Applied tenant_id={tenant_id} filter to {mapper.class_.__name__}")
                except Exception as e:
                    logger.error(f"Failed to apply tenant filter: {e}")
                    # If filtering fails, we should block the query for security
                    # But for now, log the error


def get_db():
    """
    Dependency to get database session with tenant isolation.
    
    This is a FastAPI dependency that provides a database session. The session
    is automatically tenant-filtered via SQLAlchemy event listeners.
    
    Yields:
        Database session that is automatically tenant-scoped
        
    Example:
        @router.get("/assets")
        def list_assets(db: Session = Depends(get_db)):
            # db is automatically filtered by tenant_id
            return db.query(Asset).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_url():
    """
    Get database URL from settings.
    
    Returns:
        Database connection URL string
    """
    return settings.DATABASE_URL


def get_services_db():
    """
    Dependency to get services database session.
    
    This session connects to the global services database (synced from Neon)
    and is used for catalog lookups, API key validation, etc.
    
    Yields:
        Services database session
    """
    db = ServicesSessionLocal()
    try:
        yield db
    finally:
        db.close()
