# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Report Generation Background Tasks
Heavy report generation operations
"""

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.report_service import ReportService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='generate_capacity_report')
def generate_capacity_report(datacenter_id=None):
    """
    Generate comprehensive capacity report
    """
    logger.info(f"Generating capacity report for datacenter_id={datacenter_id}")

    db = SessionLocal()
    try:
        service = ReportService(db)
        result = service.capacity_summary(datacenter_id)
        logger.info(f"Capacity report generated: {result}")
        return result
    except Exception as e:
        logger.error(f"Error generating capacity report: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='generate_daily_reports')
def generate_daily_reports():
    """
    Generate daily summary reports
    """
    logger.info("Generating daily reports")

    db = SessionLocal()
    try:
        service = ReportService(db)
        # Generate various daily reports
        summary = service.dashboard_summary()
        logger.info(f"Daily reports generated")
        return {"status": "completed", "summary": summary}
    except Exception as e:
        logger.error(f"Error generating daily reports: {e}")
        raise
    finally:
        db.close()
