# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Alert Background Tasks
Periodic tasks to check and send email alerts
"""

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.alert_service import AlertService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='check_low_stock_alerts')
def check_low_stock_alerts(container_id=None):
    """
    Check for low stock and send email alerts
    """
    logger.info(f"Checking low stock alerts (container_id={container_id})")
    
    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        results = alert_service.check_and_send_low_stock_alerts(container_id=container_id)
        logger.info(f"Low stock check complete: {results}")
        return results
    except Exception as e:
        logger.error(f"Error checking low stock alerts: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='check_maintenance_alerts')
def check_maintenance_alerts():
    """
    Check for upcoming maintenance and send email alerts
    """
    logger.info("Checking maintenance alerts")
    
    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        results = alert_service.check_and_send_maintenance_alerts()
        logger.info(f"Maintenance check complete: {results}")
        return results
    except Exception as e:
        logger.error(f"Error checking maintenance alerts: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='check_warranty_alerts')
def check_warranty_alerts():
    """
    Check for expiring warranties and send email alerts
    """
    logger.info("Checking warranty alerts")
    
    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        results = alert_service.check_and_send_warranty_alerts()
        logger.info(f"Warranty check complete: {results}")
        return results
    except Exception as e:
        logger.error(f"Error checking warranty alerts: {e}")
        raise
    finally:
        db.close()

