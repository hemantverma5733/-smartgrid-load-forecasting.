from celery import Celery
from app.config import settings

celery_app = Celery(
    "smartgrid_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=["app.tasks.tasks"]
)

# Celery Beat Periodic Tasks Configuration
celery_app.conf.beat_schedule = {
    "monitor-grid-every-2-minutes": {
        "task": "app.tasks.tasks.monitor_grid_overloads",
        "schedule": 120.0,
    },
    "generate-daily-report-every-day": {
        "task": "app.tasks.tasks.generate_grid_reports",
        "schedule": 86400.0,  # Once a day
    }
}
