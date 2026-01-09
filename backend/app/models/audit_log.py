# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Log Model
Comprehensive audit trail for all database changes

This model tracks every create, update, and delete operation in the system,
providing a complete audit trail for compliance and troubleshooting.

Key Features:
- Tracks user who performed the action
- Records timestamp of the action
- Stores before/after values for updates
- Supports filtering by table, user, tenant, date range
- JSON storage for flexible schema support
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.tenant_mixin import TenantMixin


class AuditLog(Base, TenantMixin):
    """
    Audit log entry for tracking all database changes.
    
    This model provides a comprehensive audit trail of all create, update,
    and delete operations in the system. Each entry records:
    - Who performed the action (user_id, username)
    - When it happened (timestamp)
    - What was changed (table_name, record_id, action)
    - What changed (before_values, after_values)
    
    Attributes:
        id: Primary key
        user_id: ID of user who performed the action
        username: Username of user who performed the action (denormalized for performance)
        action: Type of action (create, update, delete)
        table_name: Name of the table that was modified
        record_id: ID of the record that was modified
        before_values: JSON object with values before the change (for updates/deletes)
        after_values: JSON object with values after the change (for creates/updates)
        changes: JSON object with only the fields that changed (for updates)
        ip_address: IP address of the client (optional)
        user_agent: User agent string (optional)
        api_key_id: ID of API key used for authentication (optional, for "via Relay Token #4" display)
        notes: Additional notes about the action (optional)
        tenant_id: Foreign key to tenants table (from TenantMixin)
        created_at: Timestamp when the audit log entry was created
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint('action', 'user_id', 'username', 'table_name', 'record_id', 'created_at', name='idx_audit_logs_unique_action'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True, comment="ID of user who performed the action")
    username = Column(String(100), nullable=True, index=True, comment="Username (denormalized for performance)")
    action = Column(String(20), nullable=False, index=True, comment="Action type: create, update, delete")
    table_name = Column(String(100), nullable=False, index=True, comment="Name of the table that was modified")
    record_id = Column(Integer, nullable=True, index=True, comment="ID of the record that was modified")
    before_values = Column(JSON, nullable=True, comment="Values before the change (JSON)")
    after_values = Column(JSON, nullable=True, comment="Values after the change (JSON)")
    changes = Column(JSON, nullable=True, comment="Only the fields that changed (for updates, JSON)")
    ip_address = Column(String(45), nullable=True, comment="IP address of the client")
    user_agent = Column(String(500), nullable=True, comment="User agent string")
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True, index=True, comment="ID of API key used (if authenticated via API key)")
    notes = Column(Text, nullable=True, comment="Additional notes about the action")
    # tenant_id is inherited from TenantMixin
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True, comment="Timestamp when the action occurred")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', table='{self.table_name}', record_id={self.record_id}, user='{self.username}')>"

