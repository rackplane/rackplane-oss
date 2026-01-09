# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Log Cleanup Task
Automated maintenance for audit logs
"""

from datetime import datetime, timedelta
import logging
from sqlalchemy import delete

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

@celery_app.task(name="cleanup_old_audit_logs")
def cleanup_old_audit_logs():
    """
    Delete audit logs older than the configured retention period.
    
    This task should run daily to ensure compliance with data retention policies
    and prevent unlimited database growth.
    
    Configuration:
    - settings.AUDIT_RETENTION_DAYS: Number of days to keep logs (default: 365)
    """
    days = settings.AUDIT_RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    logger.info(f"Starting audit log cleanup. Retention: {days} days (cutoff: {cutoff_date})")
    
    db = SessionLocal()
    try:
        # Bypassing tenant filter to clean up all old logs globally
        # This is a system maintenance task
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        stmt = stmt.execution_options(skip_tenant_filter=True)
        
        result = db.execute(stmt)
        deleted_count = result.rowcount
        
        db.commit()
        logger.info(f"Audit log cleanup complete. Deleted {deleted_count} records older than {cutoff_date}")
        
        return {"deleted_count": deleted_count, "cutoff_date": str(cutoff_date)}
        
    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
