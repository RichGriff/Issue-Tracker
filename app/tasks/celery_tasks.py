"""Celery background tasks for asynchronous, long-running operations."""

import logging
import random
import time

from app.database import models
from app.database.config import SyncSessionLocal
from app.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_issue(self, issue_id: str):
    """
    Enrich an issue with AI-generated summary and tags.
    
    This is a Celery task that runs asynchronously in a worker process.
    Use this for long-running operations like API calls, LLM processing, etc.
    
    Args:
        issue_id: The UUID of the issue to enrich
        
    Retries:
        - Max 3 retries on failure
        - 60-second delay between retries
    """
    db = SyncSessionLocal()
    
    try:
        # Fetch issue from database
        issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
        
        if not issue:
            logger.warning(f"Issue {issue_id} not found for enrichment")
            return
        
        logger.info(f"Starting enrichment for issue {issue_id}")
        
        # Simulate slow work (LLM call, external API, etc.)
        # In production, this would be a real API call
        time.sleep(5)
        
        # Mock AI Summary and Tags
        issue.ai_summary = f"AI Summary: {issue.description[:100]}..."
        issue.tags = ",".join(random.sample(
            ["bug", "frontend", "backend", "urgent", "low-priority"], 2
        ))
        
        db.commit()
        logger.info(f"Successfully enriched issue {issue_id}")
        
    except Exception as exc:
        db.rollback()
        logger.error(f"Error enriching issue {issue_id}: {str(exc)}")
        
        # Retry with exponential backoff
        # self.retry() will re-queue the task with increasing delay
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
    finally:
        db.close()
