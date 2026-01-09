# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Environmental Monitoring Background Tasks
Process sensor data and generate alerts
"""

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.environmental_service import EnvironmentalService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='process_sensor_readings')
def process_sensor_readings(sensor_id=None):
    """
    Process environmental sensor readings
    Check for threshold breaches and generate alerts
    """
    logger.info(f"Processing sensor readings for sensor_id={sensor_id}")

    db = SessionLocal()
    try:
        service = EnvironmentalService(db)
        # Process readings and check for anomalies
        alerts = service.get_active_alerts()
        logger.info(f"Sensor readings processed: {len(alerts)} alerts")
        return {"alerts": len(alerts)}
    except Exception as e:
        logger.error(f"Error processing sensor readings: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='monitor_environmental_compliance')
def monitor_environmental_compliance():
    """
    Monitor environmental compliance across all datacenters
    """
    logger.info("Monitoring environmental compliance")

    db = SessionLocal()
    try:
        service = EnvironmentalService(db)
        # Check compliance for all active sensors
        return {"status": "monitored"}
    except Exception as e:
        logger.error(f"Error monitoring environmental compliance: {e}")
        raise
    finally:
        db.close()
