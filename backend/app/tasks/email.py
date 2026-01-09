# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Email Background Tasks
Handles actual email sending via Celery to avoid blocking API
"""

from typing import Optional
from app.celery_app import celery_app
from app.services.email_service import get_sync_email_service
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='send_email', bind=True, default_retry_delay=60, max_retries=3)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
):
    """
    Background task to send an email.
    Retries up to 3 times on failure.
    """
    try:
        service = get_sync_email_service()
        success = service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        if not success:
            raise Exception("Email service returned False")
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        # Retry logic handled by Celery
        raise self.retry(exc=e)
