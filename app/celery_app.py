"""
Celery application initialization and configuration.
This module sets up Celery to use Redis as the message broker.
"""

from celery import Celery
from kombu import Exchange, Queue

# Initialize Celery app
app = Celery(
    "fastapi_issue_tracker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

# Configure task settings
app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,  # Track when task starts
    task_time_limit=30 * 60,  # Kill task after 30 minutes
    task_soft_time_limit=25 * 60,  # Soft limit 25 minutes (allows graceful cleanup)
    
    # Retry behavior
    task_acks_late=True,  # Task acknowledged after execution
    worker_prefetch_multiplier=1,  # Prefetch one task at a time
    
    # Task routes and queues
    task_routes={
        "app.tasks.issues.enrich_issue": {"queue": "issues"},
    },
    task_queues=[
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("issues", Exchange("issues"), routing_key="issues"),
    ],
)

# Auto-discover tasks from all registered apps
app.autodiscover_tasks(["app"])

# Explicitly import task modules to ensure they're registered
# This is necessary for Celery to discover tasks with @app.task decorators
from app.tasks import issues  # noqa: E402, F401


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
