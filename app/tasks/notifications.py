"""Non-Celery background tasks for notifications and outbound communications."""

import logging
import os

import httpx

from app.database import models

logger = logging.getLogger(__name__)


def notify_issue_creation(issue: models.Issue) -> None:
    """Send a Slack notification when a new issue is created.
    
    This is a FastAPI BackgroundTask (not Celery), suitable for quick,
    synchronous operations that should not block the main request.
    
    Args:
        issue: The Issue model instance to notify about
    """
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
