import logging
import random
import time
import httpx
import os

from sqlalchemy import select

from app.database import models
from app.database.config import SyncSessionLocal
from app.celery_app import app

logger = logging.getLogger(__name__)

def notify_issue_creation(issue: models.Issue) -> None:
    """Send a Slack notification when a new issue is created."""
    
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set, skipping notification")
        return

    logger.info("Issue created", extra={"issue_id": issue.id})

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🆕 New Issue Created",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:*\n{issue.priority}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{issue.description or '_No description provided_'}",
                },
            },
        ]
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(slack_webhook_url, json=payload)
            response.raise_for_status()

        logger.info(
            "Slack notification sent successfully",
            extra={"issue_id": issue.id},
        )

    except httpx.HTTPError:
        logger.exception(
            "Failed to send Slack notification",
            extra={"issue_id": issue.id},
        )


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_issue(self, issue_id: str):
    """
    Enrich an issue with AI-generated summary and tags.
    
    This is a Celery task that runs asynchronously in a worker process.
    
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


