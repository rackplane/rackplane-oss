# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Logging Service
Automatically logs all create, update, and delete operations

This service provides functions to log database changes to the audit_log
table. It can be called manually or integrated with SQLAlchemy event listeners
for automatic logging.

Key Features:
- Log create, update, and delete operations
- Capture before/after values
- Track user, timestamp, IP address
- Support for filtering and querying audit logs
"""

from sqlalchemy.orm import Session
from sqlalchemy import inspect, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.models.audit_log import AuditLog
from app.core.tenant import get_current_tenant_id
from app.core.context import get_ip_address, get_user_agent

logger = logging.getLogger(__name__)


def get_model_dict(instance) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model instance to a dictionary.
    
    Excludes internal SQLAlchemy attributes and relationships.
    
    Args:
        instance: SQLAlchemy model instance
        
    Returns:
        Dictionary of column values
    """
    result = {}
    mapper = inspect(instance.__class__)
    
    for column in mapper.columns:
        value = getattr(instance, column.key, None)
        # Convert datetime to ISO format for JSON serialization
        if isinstance(value, datetime):
            value = value.isoformat()
        # Convert enums to their values
        elif hasattr(value, 'value'):
            value = value.value
        result[column.key] = value
    
    return result


def log_create(
    db: Session,
    instance: Any,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    api_key_id: Optional[int] = None,
    notes: Optional[str] = None
) -> AuditLog:
    """
    Log a create operation.
    
    Args:
        db: Database session
        instance: The newly created model instance
        user_id: ID of user who created the record
        username: Username of user who created the record
        ip_address: IP address of the client
        user_agent: User agent string
        api_key_id: ID of API key used (if authenticated via API key)
        notes: Additional notes
        
    Returns:
        Created AuditLog entry
    """
    try:
        # Get current user if not provided
        # Note: get_current_user is async and requires FastAPI context, so we can't call it here
        # User info must be provided by the caller
        if user_id is None and username is None:
            logger.warning("log_create called without user_id or username - audit entry may be incomplete")
        
        # Get tenant_id from instance or context
        tenant_id = getattr(instance, 'tenant_id', None) or get_current_tenant_id()
        
        # Get table name
        table_name = instance.__tablename__
        
        # Get record ID
        record_id = getattr(instance, 'id', None)
        
        # Get after values (all current values)
        after_values = get_model_dict(instance)
        
        # Check for existing duplicate before creating (mitigation for constraint violations)
        # This prevents duplicate logs even if the unique constraint fails
        # Check for any existing log with the same key fields within the last 5 seconds
        # Use a wider window to catch rapid-fire duplicates
        from sqlalchemy import and_
        now = datetime.utcnow()
        five_seconds_ago = now - timedelta(seconds=5)
        
        existing = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "create",
                AuditLog.user_id == user_id,
                AuditLog.username == username,
                AuditLog.table_name == table_name,
                AuditLog.record_id == record_id,
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at >= five_seconds_ago
            )
        ).order_by(AuditLog.created_at.desc()).first()
        
        if existing:
            # Duplicate detected - skip logging to prevent constraint violation
            logger.warning(
                f"Skipping duplicate audit log: create on {table_name}.{record_id} by {username} "
                f"(existing log ID: {existing.id}, created_at: {existing.created_at})"
            )
            return existing
        
        # Create audit log entry
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action="create",
            table_name=table_name,
            record_id=record_id,
            before_values=None,  # No before values for creates
            after_values=after_values,
            changes=None,  # No changes for creates
            ip_address=ip_address or get_ip_address(),
            user_agent=user_agent or get_user_agent(),
            api_key_id=api_key_id,
            notes=notes,
            tenant_id=tenant_id
        )
        
        try:
            db.add(audit_entry)
            # Use flush instead of commit to avoid expiring the instance
            # The main transaction will commit both the audit log and the create
            db.flush()
        except Exception as flush_error:
            # If flush fails due to unique constraint violation, check for existing and return it
            # PostgreSQL error code 23505 is unique_violation
            error_str = str(flush_error).lower()
            is_unique_violation = (
                'unique' in error_str or 
                'duplicate' in error_str or 
                '23505' in error_str or
                hasattr(flush_error, 'orig') and hasattr(flush_error.orig, 'pgcode') and flush_error.orig.pgcode == '23505'
            )
            
            if is_unique_violation:
                logger.warning(f"Unique constraint violation on audit log, checking for existing entry: {flush_error}")
                db.rollback()
                # Look for existing log within last 10 seconds (wider window for safety)
                ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)
                existing = db.query(AuditLog).filter(
                    and_(
                        AuditLog.action == "create",
                        AuditLog.user_id == user_id,
                        AuditLog.username == username,
                        AuditLog.table_name == table_name,
                        AuditLog.record_id == record_id,
                        AuditLog.tenant_id == tenant_id,
                        AuditLog.created_at >= ten_seconds_ago
                    )
                ).order_by(AuditLog.created_at.desc()).first()
                if existing:
                    logger.info(f"Found existing audit log (ID: {existing.id}), returning it instead of creating duplicate")
                    return existing
            # Re-raise if it's not a constraint violation
            raise
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"Failed to log create operation: {e}", exc_info=True)
        # Don't raise - audit logging should not break the main operation
        return None


def log_update(
    db: Session,
    instance: Any,
    old_values: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    tenant_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    api_key_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[AuditLog]:
    """
    Log an update operation.
    
    Args:
        db: Database session
        instance: The updated model instance
        old_values: Dictionary of values before the update (if not provided, will try to get from history)
        user_id: ID of user who updated the record
        username: Username of user who updated the record
        ip_address: IP address of the client
        user_agent: User agent string
        notes: Additional notes
        
    Returns:
        Created AuditLog entry
    """
    try:
        # Get tenant_id from instance or context
        tenant_id = getattr(instance, 'tenant_id', None) or get_current_tenant_id()
        
        # Get table name
        table_name = instance.__tablename__
        
        # Get record ID
        record_id = getattr(instance, 'id', None)
        
        # Get after values (all current values)
        after_values = get_model_dict(instance)
        
        # Get before values if not provided
        if old_values is None:
            # Try to get from SQLAlchemy history if available
            from sqlalchemy.orm.attributes import get_history
            old_values = {}
            for key in after_values.keys():
                hist = get_history(instance, key)
                if hist.has_changes():
                    old_values[key] = hist.deleted[0] if hist.deleted else None
        
        # Calculate changes (only fields that actually changed)
        changes = {}
        if old_values:
            for key, new_value in after_values.items():
                old_value = old_values.get(key)
                if old_value != new_value:
                    changes[key] = {"old": old_value, "new": new_value}
        
        # Check for existing duplicate before creating (mitigation for constraint violations)
        # This prevents duplicate logs even if the unique constraint fails
        # Check for any existing log with the same key fields within the last 2 seconds
        from sqlalchemy import and_, func
        now = datetime.utcnow()
        two_seconds_ago = now - timedelta(seconds=2)
        
        existing = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "update",
                AuditLog.user_id == user_id,
                AuditLog.username == username,
                AuditLog.table_name == table_name,
                AuditLog.record_id == record_id,
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at >= two_seconds_ago
            )
        ).order_by(AuditLog.created_at.desc()).first()
        
        if existing:
            # Duplicate detected - skip logging to prevent constraint violation
            logger.warning(
                f"Skipping duplicate audit log: update on {table_name}.{record_id} by {username} "
                f"(existing log ID: {existing.id}, created_at: {existing.created_at})"
            )
            return existing
        
        # Create audit log entry
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action="update",
            table_name=table_name,
            record_id=record_id,
            before_values=old_values if old_values else None,
            after_values=after_values,
            changes=changes if changes else None,
            ip_address=ip_address or get_ip_address(),
            user_agent=user_agent or get_user_agent(),
            api_key_id=api_key_id,
            notes=notes,
            tenant_id=tenant_id
        )
        
        try:
            db.add(audit_entry)
            # Use flush instead of commit to avoid expiring the instance
            # The main transaction will commit both the audit log and the update
            db.flush()
        except Exception as flush_error:
            # If flush fails due to unique constraint violation, check for existing and return it
            # PostgreSQL error code 23505 is unique_violation
            error_str = str(flush_error).lower()
            is_unique_violation = (
                'unique' in error_str or 
                'duplicate' in error_str or 
                '23505' in error_str or
                hasattr(flush_error, 'orig') and hasattr(flush_error.orig, 'pgcode') and flush_error.orig.pgcode == '23505'
            )
            
            if is_unique_violation:
                logger.warning(f"Unique constraint violation on audit log, checking for existing entry: {flush_error}")
                db.rollback()
                # Look for existing log within last 10 seconds (wider window for safety)
                ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)
                existing = db.query(AuditLog).filter(
                    and_(
                        AuditLog.action == "update",
                        AuditLog.user_id == user_id,
                        AuditLog.username == username,
                        AuditLog.table_name == table_name,
                        AuditLog.record_id == record_id,
                        AuditLog.tenant_id == tenant_id,
                        AuditLog.created_at >= ten_seconds_ago
                    )
                ).order_by(AuditLog.created_at.desc()).first()
                if existing:
                    logger.info(f"Found existing audit log (ID: {existing.id}), returning it instead of creating duplicate")
                    return existing
            # Re-raise if it's not a constraint violation
            raise
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"Failed to log update operation: {e}", exc_info=True)
        # Don't raise - audit logging should not break the main operation
        return None


def log_delete(
    db: Session,
    instance: Any,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    tenant_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    api_key_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[AuditLog]:
    """
    Log a delete operation.
    
    Args:
        db: Database session
        instance: The deleted model instance (should be accessed before deletion)
        user_id: ID of user who deleted the record
        username: Username of user who deleted the record
        ip_address: IP address of the client
        user_agent: User agent string
        notes: Additional notes
        
    Returns:
        Created AuditLog entry
    """
    try:
        # IMPORTANT: Get all data from instance BEFORE any commits
        # After db.commit(), the instance becomes expired and accessing attributes
        # may trigger a reload that fails if the instance is in a deleted state
        
        # Get tenant_id from instance or context
        tenant_id = getattr(instance, 'tenant_id', None) or get_current_tenant_id()
        
        # Get table name
        table_name = instance.__tablename__
        
        # Get record ID
        record_id = getattr(instance, 'id', None)
        
        # Get before values (all values before deletion)
        # Do this BEFORE any commits to avoid expired instance issues
        before_values = get_model_dict(instance)
        
        # Create audit log entry
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action="delete",
            table_name=table_name,
            record_id=record_id,
            before_values=before_values,
            after_values=None,  # No after values for deletes
            changes=None,  # No changes for deletes
            ip_address=ip_address or get_ip_address(),
            user_agent=user_agent or get_user_agent(),
            api_key_id=api_key_id,
            notes=notes,
            tenant_id=tenant_id
        )
        
        db.add(audit_entry)
        # Use flush instead of commit to avoid expiring the instance
        # The main transaction will commit both the audit log and the delete
        db.flush()
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"Failed to log delete operation: {e}", exc_info=True)
        # Don't raise - audit logging should not break the main operation
        return None

def log_security_event(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    tenant_id: int = 0,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> Optional[AuditLog]:
    """
    Log a security event (e.g. login, logout, failed attempt).
    
    Args:
        db: Database session
        action: Action name (e.g. "login_success", "login_failed")
        user_id: ID of user (if known)
        username: Username (if known)
        tenant_id: Tenant ID (0 for system/unknown)
        ip_address: IP address
        user_agent: User agent
        details: Additional details to store in after_values
        notes: Description of the event
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            table_name="auth",  # Virtual table name for auth events
            record_id=user_id,
            before_values=None,
            after_values=details,
            changes=None,
            ip_address=ip_address or get_ip_address(),
            user_agent=user_agent or get_user_agent(),
            notes=notes,
            tenant_id=tenant_id
        )
        
        # Capture ID before commit (it's generated on flush)
        db.add(audit_entry)
        db.flush()
        audit_id = audit_entry.id
        
        db.commit() # Commit immediately for security events
        
        # Re-query with skip_tenant_filter to avoid Security Violation if tenant context is missing
        # We use the captured ID to avoid accessing audit_entry.id which would trigger a reload
        if audit_id:
            refreshed = db.query(AuditLog).execution_options(skip_tenant_filter=True).filter(AuditLog.id == audit_id).first()
            if refreshed:
                return refreshed
        
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to log security event: {e}", exc_info=True)
        return None



def get_audit_logs(
    db: Session,
    table_name: Optional[str] = None,
    record_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Query audit logs with filters.
    
    Args:
        db: Database session
        table_name: Filter by table name
        record_id: Filter by record ID
        user_id: Filter by user ID
        action: Filter by action type (create, update, delete)
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of AuditLog entries
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AuditLog)
    query = apply_tenant_filter(query, AuditLog)
    
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    query = query.order_by(AuditLog.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    return query.all()

