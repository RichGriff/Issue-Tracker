"""Background tasks module.

This module contains both Celery tasks (long-running, async jobs) and 
FastAPI BackgroundTasks (quick, fire-and-forget operations).

Celery tasks: Use for operations that take significant time
- Long API calls
- Database processing
- Machine learning/LLM calls
- File processing

BackgroundTasks: Use for quick operations that don't block the request
- Notifications
- Logging
- Cache invalidation

IMPORTANT: Import notifications directly here, but import celery_tasks
explicitly when needed to avoid circular imports with Celery initialization.
"""

from app.tasks.notifications import notify_issue_creation

# Celery tasks are available but not imported here to prevent circular imports
# Use: from app.tasks.celery_tasks import enrich_issue

__all__ = ["notify_issue_creation"]
