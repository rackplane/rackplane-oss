# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Logs API Endpoints
View and query audit log entries

This module provides endpoints to view and query audit logs, which track
all create, update, and delete operations in the system.

Endpoints:
- GET /api/v1/audit-logs: List audit logs with filters
- GET /api/v1/audit-logs/{id}: Get a specific audit log entry
- GET /api/v1/audit-logs/table/{table_name}: Get audit logs for a specific table
- GET /api/v1/audit-logs/record/{table_name}/{record_id}: Get audit logs for a specific record
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import io
import csv
import json

from app.core.database import get_db
from app.core.auth import get_current_tenant_admin
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.api_key import ApiKey
from app.models.user_role import UserRole
from app.schemas.audit_log import AuditLogResponse, AuditLogQuery, AuditLogListResponse
from app.services.audit_service import get_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def enrich_audit_logs_with_api_keys(logs: List[AuditLog], db: Session) -> List[AuditLogResponse]:
    """
    Enrich audit logs with API key labels for display.
    
    Args:
        logs: List of AuditLog instances
        db: Database session
        
    Returns:
        List of AuditLogResponse with api_key_label populated
    """
    # Get unique API key IDs
    api_key_ids = {log.api_key_id for log in logs if log.api_key_id}
    api_keys_map = {}
    
    if api_key_ids:
        api_keys = db.query(ApiKey).filter(ApiKey.id.in_(api_key_ids)).all()
        api_keys_map = {key.id: key.label for key in api_keys}
    
    # Convert to response format with API key labels
    log_responses = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "before_values": log.before_values,
            "after_values": log.after_values,
            "changes": log.changes,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "api_key_id": log.api_key_id,
            "api_key_label": api_keys_map.get(log.api_key_id) if log.api_key_id else None,
            "notes": log.notes,
            "tenant_id": log.tenant_id,
            "created_at": log.created_at
        }
        log_responses.append(AuditLogResponse(**log_dict))
    
    return log_responses


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    record_id: Optional[int] = Query(None, description="Filter by record ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    action: Optional[str] = Query(None, description="Filter by action type (create, update, delete)"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    List audit logs with optional filters.
    
    Returns audit log entries matching the specified filters. Results are
    ordered by timestamp (most recent first) and are tenant-scoped.
    
    Filters:
    - table_name: Filter by table name (e.g., "assets", "users")
    - record_id: Filter by specific record ID
    - user_id: Filter by user ID who performed the action
    - username: Filter by username who performed the action
    - action: Filter by action type (create, update, delete)
    - start_date: Filter by start date (ISO format)
    - end_date: Filter by end date (ISO format)
    - limit: Maximum number of results (default: 100, max: 1000)
    - offset: Offset for pagination (default: 0)
    
    Permissions:
    - TENANT_ADMIN: Can view audit logs for their own tenant only
    - SUPER_ADMIN: Can view audit logs for all tenants (uses skip_tenant_filter)
    - USER and READ_ONLY: Access denied (403 Forbidden)
    """
    from app.core.tenant_query import apply_tenant_filter
    
    # Build base query
    query = db.query(AuditLog)
    
    # Apply tenant filter unless user is super admin
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        query = apply_tenant_filter(query, AuditLog)
    # Super admins can see all tenants (no filter applied)
    
    # Apply filters
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply ordering and pagination
    query = query.order_by(AuditLog.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    logs = query.all()
    
    # Enrich with API key labels
    log_responses = enrich_audit_logs_with_api_keys(logs, db)
    
    # Return paginated response with total count
    return AuditLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        logs=log_responses
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Get a specific audit log entry by ID.
    
    Returns detailed information about a single audit log entry, including
    before/after values and changes.
    
    Permissions:
    - TENANT_ADMIN: Can view logs for their own tenant only
    - SUPER_ADMIN: Can view logs for all tenants
    - USER and READ_ONLY: Access denied (403 Forbidden)
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AuditLog).filter(AuditLog.id == log_id)
    
    # Apply tenant filter unless user is super admin
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        query = apply_tenant_filter(query, AuditLog)
    
    log = query.first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    # Enrich with API key label
    log_responses = enrich_audit_logs_with_api_keys([log], db)
    return log_responses[0]


@router.get("/table/{table_name}", response_model=List[AuditLogResponse])
async def get_audit_logs_for_table(
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Get all audit logs for a specific table.
    
    Returns all audit log entries for the specified table, ordered by
    timestamp (most recent first).
    
    Permissions:
    - TENANT_ADMIN: Can view logs for their own tenant only
    - SUPER_ADMIN: Can view logs for all tenants
    - USER and READ_ONLY: Access denied (403 Forbidden)
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AuditLog).filter(AuditLog.table_name == table_name)
    
    # Apply tenant filter unless user is super admin
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        query = apply_tenant_filter(query, AuditLog)
    
    logs = query.order_by(AuditLog.created_at.desc()).all()
    
    # Enrich with API key labels
    return enrich_audit_logs_with_api_keys(logs, db)


@router.get("/record/{table_name}/{record_id}", response_model=List[AuditLogResponse])
async def get_audit_logs_for_record(
    table_name: str,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Get all audit logs for a specific record.
    
    Returns all audit log entries for the specified table and record ID,
    ordered by timestamp (most recent first). This is useful for viewing
    the complete history of a specific asset, user, etc.
    
    Permissions:
    - TENANT_ADMIN: Can view logs for their own tenant only
    - SUPER_ADMIN: Can view logs for all tenants
    - USER and READ_ONLY: Access denied (403 Forbidden)
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AuditLog).filter(
        AuditLog.table_name == table_name,
        AuditLog.record_id == record_id
    )
    
    # Apply tenant filter unless user is super admin
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        query = apply_tenant_filter(query, AuditLog)
    
    logs = query.order_by(AuditLog.created_at.desc()).all()
    
    # Enrich with API key labels
    return enrich_audit_logs_with_api_keys(logs, db)


@router.get("/export", response_class=StreamingResponse)
async def export_audit_logs(
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    record_id: Optional[int] = Query(None, description="Filter by record ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    action: Optional[str] = Query(None, description="Filter by action type (create, update, delete)"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Export audit logs to CSV with optional filters.
    
    Permissions:
    - TENANT_ADMIN: Can export logs for their own tenant only
    - SUPER_ADMIN: Can export logs for all tenants (uses skip_tenant_filter)
    - USER and READ_ONLY: Access denied (403 Forbidden)
    """
    from app.core.tenant_query import apply_tenant_filter
    
    query = db.query(AuditLog)
    
    if current_user.effective_role != UserRole.SUPER_ADMIN:
        query = apply_tenant_filter(query, AuditLog)
    
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    logs = query.order_by(desc(AuditLog.created_at)).all()
    
    # Get API key labels for export
    api_key_ids = {log.api_key_id for log in logs if log.api_key_id}
    api_keys_map = {}
    if api_key_ids:
        api_keys = db.query(ApiKey).filter(ApiKey.id.in_(api_key_ids)).all()
        api_keys_map = {key.id: key.label for key in api_keys}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Timestamp', 'User ID', 'Username', 'Action', 'Table Name', 'Record ID',
        'Before Values', 'After Values', 'Changes', 'IP Address', 'User Agent', 
        'API Key ID', 'API Key Label', 'Notes', 'Tenant ID'
    ])
    
    # Write data rows
    for log in logs:
        writer.writerow([
            log.id,
            log.created_at.isoformat(),
            log.user_id,
            log.username,
            log.action,
            log.table_name,
            log.record_id,
            json.dumps(log.before_values) if log.before_values else '',
            json.dumps(log.after_values) if log.after_values else '',
            json.dumps(log.changes) if log.changes else '',
            log.ip_address,
            log.user_agent,
            log.api_key_id,
            api_keys_map.get(log.api_key_id) if log.api_key_id else '',
            log.notes,
            log.tenant_id
        ])
    
    output.seek(0)
    
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
