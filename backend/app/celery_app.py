# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Celery Application Configuration
Background task processing for DCMS
"""

from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "datacenter_inventory",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Auto-discover tasks from all installed apps
celery_app.autodiscover_tasks(['app.tasks'])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'
