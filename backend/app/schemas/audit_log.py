# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Log Schemas
Pydantic models for audit log API responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AuditLogResponse(BaseModel):
    """
    Schema for audit log API responses.
    
    Used in GET /api/v1/audit-logs endpoints. Includes all audit log
    information including before/after values and changes.
    """
    id: int = Field(..., description="Audit log entry ID")
    user_id: Optional[int] = Field(None, description="ID of user who performed the action")
    username: Optional[str] = Field(None, description="Username of user who performed the action")
    action: str = Field(..., description="Action type: create, update, delete")
    table_name: str = Field(..., description="Name of the table that was modified")
    record_id: Optional[int] = Field(None, description="ID of the record that was modified")
    before_values: Optional[Dict[str, Any]] = Field(None, description="Values before the change (JSON)")
    after_values: Optional[Dict[str, Any]] = Field(None, description="Values after the change (JSON)")
    changes: Optional[Dict[str, Any]] = Field(None, description="Only the fields that changed (for updates, JSON)")
    ip_address: Optional[str] = Field(None, description="IP address of the client")
    user_agent: Optional[str] = Field(None, description="User agent string")
    api_key_id: Optional[int] = Field(None, description="ID of API key used (if authenticated via API key)")
    api_key_label: Optional[str] = Field(None, description="Label of API key used (for display)")
    notes: Optional[str] = Field(None, description="Additional notes about the action")
    tenant_id: Optional[int] = Field(None, description="Tenant ID")
    created_at: datetime = Field(..., description="Timestamp when the action occurred")

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """
    Schema for audit log query parameters.
    
    Used for filtering audit logs by various criteria.
    """
    table_name: Optional[str] = Field(None, description="Filter by table name")
    record_id: Optional[int] = Field(None, description="Filter by record ID")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action type (create, update, delete)")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class AuditLogListResponse(BaseModel):
    """
    Schema for paginated audit log list responses.
    
    Includes total count for pagination UI.
    """
    total: int = Field(..., description="Total number of audit log entries matching filters")
    limit: int = Field(..., description="Maximum number of results per page")
    offset: int = Field(..., description="Current offset/pagination offset")
    logs: List[AuditLogResponse] = Field(..., description="List of audit log entries")

