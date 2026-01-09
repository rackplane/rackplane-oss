# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Audit Logging Helper Functions

Reduces boilerplate code for audit logging from 15+ lines to a single line.

Usage:
    from app.utils.audit_helpers import audit_create, audit_update, audit_delete
    from fastapi import Request

    # In your endpoint:
    audit_create(db, created_instance, current_user, request)
    audit_update(db, updated_instance, current_user, request, old_values)
    audit_delete(db, deleted_instance, current_user, request)

Features:
- Automatically extracts IP address and user agent from request
- Gracefully handles audit logging failures without breaking main request
- Works seamlessly with FastAPI dependency injection
- Follows existing audit_service.py patterns
"""

from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
import logging

from app.services.audit_service import log_create, log_update, log_delete
from app.models.user import User
from app.core.auth import get_current_api_key_id

logger = logging.getLogger(__name__)


def audit_create(
    db: Session,
    instance: Any,
    user: User,
    request: Optional[Request] = None
) -> None:
    """
    One-liner to audit a create operation.

    Args:
        db: Database session
        instance: The newly created model instance
        user: Current user performing the action
        request: FastAPI request object (for IP and user agent)

    Example:
        new_asset = Asset(...)
        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)
        audit_create(db, new_asset, current_user, request)
    """
    try:
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        log_create(
            db=db,
            instance=instance,
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            api_key_id=get_current_api_key_id()
        )
    except Exception as e:
        # Log error but don't fail the main request
        logger.error(f"Audit logging failed for create operation: {e}")


def audit_update(
    db: Session,
    instance: Any,
    user: User,
    request: Optional[Request] = None,
    old_values: Optional[Dict[str, Any]] = None
) -> None:
    """
    One-liner to audit an update operation.

    Args:
        db: Database session
        instance: The updated model instance
        user: Current user performing the action
        request: FastAPI request object (for IP and user agent)
        old_values: Dictionary of values before update (use get_model_dict)

    Example:
        from app.services.audit_service import get_model_dict

        old_values = get_model_dict(asset)
        asset.name = "New Name"
        db.commit()
        db.refresh(asset)
        audit_update(db, asset, current_user, request, old_values)
    """
    try:
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        log_update(
            db=db,
            instance=instance,
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            api_key_id=get_current_api_key_id(),
            old_values=old_values
        )
    except Exception as e:
        # Log error but don't fail the main request
        logger.error(f"Audit logging failed for update operation: {e}")


def audit_delete(
    db: Session,
    instance: Any,
    user: User,
    request: Optional[Request] = None
) -> None:
    """
    One-liner to audit a delete operation.

    Call this BEFORE deleting the instance from the database.

    Args:
        db: Database session
        instance: The model instance to be deleted
        user: Current user performing the action
        request: FastAPI request object (for IP and user agent)

    Example:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        audit_delete(db, asset, current_user, request)  # BEFORE delete
        db.delete(asset)
        db.commit()
    """
    try:
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        log_delete(
            db=db,
            instance=instance,
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            api_key_id=get_current_api_key_id()
        )
    except Exception as e:
        # Log error but don't fail the main request
        logger.error(f"Audit logging failed for delete operation: {e}")
