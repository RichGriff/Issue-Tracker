"""Celery background tasks for asynchronous, long-running operations."""

import logging
import asyncio

from app.database import models
from app.database.config import SyncSessionLocal
from app.celery_app import app

from app.llm_service import get_llm_service, LLMServiceError

logger = logging.getLogger(__name__)

def _get_fallback_summary(title: str, description: str) -> str:
    """
    Generate fallback summary if LLM is unavailable or fails.
    
    Returns first 150 chars of description.
    """
    return f"{title}: {description[:150]}..."


def _get_fallback_tags(title: str, description: str) -> list[str]:
    """
    Generate fallback tags using simple keyword detection.
    
    Analyzes title and description for common keywords.
    """
    keywords = ["needs-review"]
    text_lower = f"{title} {description}".lower()
    
    # Bug indicators
    if any(word in text_lower for word in ["bug", "error", "broken", "crash", "issue", "fail"]):
        keywords.append("bug")
    
    # Feature indicators
    if any(word in text_lower for word in ["feature", "enhancement", "request", "new", "add"]):
        keywords.append("feature-request")
    
    # Priority indicators
    if any(word in text_lower for word in ["urgent", "critical", "asap", "immediately", "blocking"]):
        keywords.append("urgent")
    
    # Component indicators
    if any(word in text_lower for word in ["frontend", "ui", "ux", "button", "modal", "form"]):
        keywords.append("frontend")
    
    if any(word in text_lower for word in ["backend", "api", "endpoint", "database", "server"]):
        keywords.append("backend")
    
    # Performance indicators
    if any(word in text_lower for word in ["slow", "performance", "optimization", "lag", "delay"]):
        keywords.append("performance")
    
    return keywords

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_issue(self, issue_id: str):
    """
    Enrich an issue with AI-generated summary and tags using an LLM

    This is a Celery task that runs asynchronously in a worker process.
    Falls back to simple keyword-based tagging if the LLM is unavailable.

    Features: 
    - Calls configured LLM if available
    - Generates meaningful summaries and relevant tags
    - Graceful fallback to keyword detection if LLM fails
    - Comprehensive error logging

    Args: 
        issue_id: The UUID of the issue to enrich

    Raises:
        self.retry(): Retries up to 3 times with increasing delay

    Logs: 
        - INFO: Task progress and completion
        - WARNING: Fallback use or LLM failures
        - ERROR: Unexpected errors
    """
    db = SyncSessionLocal()
    
    try:
        # Fetch issue from database
        issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
        
        if not issue:
            logger.warning(f"Issue {issue_id} not found for enrichment")
            return
        
        logger.info(
            f"Starting enrichment for issue {issue_id}", extra={"issue_id": issue_id, "title": issue.title}
        )

        #  Get LLM service if configured
        llm_service = get_llm_service()

        if llm_service:
            try:
                enrichment = asyncio.run(
                    llm_service.enrich(issue.title, issue.description)
                )

                issue.ai_summary = enrichment.summary
                issue.tags = ",".join(enrichment.tags)

                logger.info(
                    f"LLM enrichment succeeded for issue {issue_id}",
                    extra={
                        "issue_id": issue_id,
                        "tags_count": len(enrichment.tags),
                        "summary_length": len(enrichment.summary)
                    }
                )
            except LLMServiceError as e:
                logger.warning(
                    f"LLM enrichment failed, using fallback: {str(e)}",
                    extra={"issue_id": issue_id}
                )
                issue.ai_summary = _get_fallback_summary(issue.title, issue.description)
                issue.tags = ",".join(_get_fallback_tags(issue.title, issue.description))
            
        else: 
            # No LLM configured, use fallback
            logger.info(
                "No LLM service configured, using fallback enrichment",
                extra={"issue_id": issue_id}
            )
            issue.ai_summary = _get_fallback_summary(issue.title, issue.description)
            issue.tags = ",".join(_get_fallback_tags(issue.title, issue.description))

        # Save enrichment issue to database
        db.commit()
        logger.info(
            f"Successfully enriched issue {issue_id}",
            extra={
                "issue_id": {issue_id}
            }
        )
    
    except Exception as exc: 
        db.rollback()
        logger.error(
            f"Error enriching issue {issue_id}: {str(exc)}",
            extra={"issue_id": issue_id},
            exc_info=True
        )

        # Rety with exponential backoff
        # Delay: 60s, 120s, 180s for retries 1, 2, 3
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exec=exc, countdown=countdown) 
    
    finally: 
        db.close()

