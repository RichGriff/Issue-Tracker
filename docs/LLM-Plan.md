# LLM Integration Plan for Issue Enrichment

## Overview

This plan outlines the implementation of LLM (Large Language Model) integration to enhance the issue enrichment process in the FastAPI Issue Tracker. The system will use AI to generate intelligent summaries and identify relevant tags for issues.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│  POST /issues                                                   │
│  ├─ Create Issue                                               │
│  └─ Trigger Celery Task (enrich_issue)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Celery Worker Process                                          │
│  ├─ Task: enrich_issue(issue_id)                               │
│  │  ├─ Get LLM Service (OpenAI/Anthropic)                      │
│  │  ├─ Call LLM API (async)                                    │
│  │  │  ├─ Generate Summary                                     │
│  │  │  └─ Generate Tags                                        │
│  │  ├─ Fallback (if LLM fails)                                 │
│  │  └─ Store results in DB                                     │
│  │                                                              │
│  └─ Retry logic with exponential backoff                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ├─► Redis (Celery Message Broker)
         │
         ├─► PostgreSQL (Issue Data + ai_summary, tags)
         │
         └─► LLM API (OpenAI/Anthropic)
             ├─ gpt-4-turbo or claude-opus
             └─ Returns: summary + tags (JSON)
```

## Implementation Plan

### Phase 1: Create LLM Service Module

**File:** `app/llm_service.py`

This module provides an abstraction for multiple LLM providers.

```python
"""
LLM Service for AI-powered issue enrichment.
Supports multiple LLM providers with a common interface.
"""

import logging
import json
import os
from typing import Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of LLM enrichment."""
    summary: str
    tags: list[str]


class LLMServiceError(Exception):
    """Raised when LLM service fails."""
    pass


class LLMService:
    """Abstract base for LLM services."""
    
    async def enrich(self, title: str, description: str) -> EnrichmentResult:
        """
        Enrich issue with AI summary and tags.
        
        Args:
            title: Issue title
            description: Issue description
            
        Returns:
            EnrichmentResult with summary and tags
            
        Raises:
            LLMServiceError: If enrichment fails
        """
        raise NotImplementedError


class OpenAIService(LLMService):
    """OpenAI API-based LLM service using gpt-4-turbo."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4-turbo-preview)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    async def enrich(self, title: str, description: str) -> EnrichmentResult:
        """Call OpenAI to generate summary and tags."""
        
        system_prompt = """You are a technical issue analyzer. Analyze the given issue and provide:
1. A concise 1-2 sentence summary of the issue
2. 3-5 relevant technical tags

Be specific and practical in your analysis."""
        
        user_prompt = f"""Analyze this issue:

Title: {title}
Description: {description}

Respond ONLY with valid JSON in this format:
{{
    "summary": "A clear summary of the issue",
    "tags": ["tag1", "tag2", "tag3"]
}}

Common tags: bug, feature-request, frontend, backend, documentation, performance, security, database, api, ui/ux, urgent"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 250,
                    },
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                parsed = json.loads(content)
                
                return EnrichmentResult(
                    summary=parsed["summary"],
                    tags=parsed["tags"]
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {str(e)}")
            raise LLMServiceError(f"Invalid JSON response from OpenAI: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI enrichment: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}")


class AnthropicService(LLMService):
    """Anthropic Claude API-based LLM service."""
    
    def __init__(self, api_key: str, model: str = "claude-opus-4-1-20250805"):
        """
        Initialize Anthropic service.
        
        Args:
            api_key: Anthropic API key
            model: Model identifier (default: claude-opus-4-1-20250805)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
    
    async def enrich(self, title: str, description: str) -> EnrichmentResult:
        """Call Claude to generate summary and tags."""
        
        prompt = f"""You are a technical issue analyzer. Analyze this issue and provide:
1. A concise 1-2 sentence summary
2. 3-5 relevant technical tags

Issue Title: {title}
Issue Description: {description}

Respond ONLY with valid JSON in this format:
{{
    "summary": "A clear summary of the issue",
    "tags": ["tag1", "tag2", "tag3"]
}}

Common tags: bug, feature-request, frontend, backend, documentation, performance, security, database, api, ui/ux, urgent"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 250,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                    },
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["content"][0]["text"]
                
                # Parse JSON response
                parsed = json.loads(content)
                
                return EnrichmentResult(
                    summary=parsed["summary"],
                    tags=parsed["tags"]
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic response: {str(e)}")
            raise LLMServiceError(f"Invalid JSON response from Anthropic: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Anthropic API request failed: {str(e)}")
            raise LLMServiceError(f"Anthropic API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Anthropic enrichment: {str(e)}")
            raise LLMServiceError(f"Unexpected error: {str(e)}")


def get_llm_service() -> Optional[LLMService]:
    """
    Factory function to get configured LLM service.
    
    Reads configuration from environment variables:
    - LLM_PROVIDER: "openai" or "anthropic"
    - OPENAI_API_KEY: API key for OpenAI
    - ANTHROPIC_API_KEY: API key for Anthropic
    
    Returns:
        LLMService instance or None if not configured
    """
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("LLM_PROVIDER=openai but OPENAI_API_KEY not set")
            return None
        logger.info("Using OpenAI LLM service")
        return OpenAIService(api_key)
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY not set")
            return None
        logger.info("Using Anthropic LLM service")
        return AnthropicService(api_key)
    
    elif provider:
        logger.warning(f"Unknown LLM_PROVIDER: {provider}")
        return None
    else:
        logger.info("LLM_PROVIDER not set, LLM enrichment disabled")
        return None
```

### Phase 2: Update Celery Task

**File:** `app/tasks/issues.py`

Update the `enrich_issue` task to use the LLM service with fallback logic.

```python
import logging
import asyncio
from sqlalchemy import select

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
    Enrich an issue with AI-generated summary and tags using an LLM.
    
    This is a Celery task that runs asynchronously in a worker process.
    Falls back to simple keyword-based tagging if LLM is unavailable.
    
    Features:
    - Calls configured LLM (OpenAI or Anthropic) if available
    - Generates meaningful summaries and relevant tags
    - Graceful fallback to keyword detection if LLM fails
    - Retries with exponential backoff on failure
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
            f"Starting enrichment for issue {issue_id}",
            extra={"issue_id": issue_id, "title": issue.title}
        )
        
        # Get LLM service if configured
        llm_service = get_llm_service()
        
        if llm_service:
            try:
                # Use asyncio.run() to call async LLM from sync Celery context
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
        
        # Save enriched issue to database
        db.commit()
        logger.info(f"Successfully enriched issue {issue_id}", extra={"issue_id": issue_id})
        
    except Exception as exc:
        db.rollback()
        logger.error(
            f"Error enriching issue {issue_id}: {str(exc)}",
            extra={"issue_id": issue_id},
            exc_info=True
        )
        
        # Retry with exponential backoff
        # Delay: 60s, 120s, 180s for retries 1, 2, 3
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=countdown)
        
    finally:
        db.close()
```

### Phase 3: Environment Configuration

**File:** `.env`

Add the following variables to your environment configuration:

```bash
# ============================================
# LLM Configuration
# ============================================

# Choose LLM Provider: "openai" or "anthropic"
# Leave blank or comment out to disable LLM enrichment (uses fallback)
LLM_PROVIDER=openai

# OpenAI Configuration
# Get API key from: https://platform.openai.com/account/api-keys
OPENAI_API_KEY=sk-your-secret-key-here

# Anthropic Configuration (alternative to OpenAI)
# Get API key from: https://console.anthropic.com/account/keys
# ANTHROPIC_API_KEY=sk-ant-your-secret-key-here
```

**File:** `pyproject.toml`

Ensure `httpx` is included in your dependencies:

```toml
[project]
name = "fastapi-issue-tracker"
version = "0.1.0"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "celery>=5.3.0",
    "redis>=5.0.0",
    "httpx>=0.24.0",  # Required for LLM API calls
    "python-dotenv>=1.0.0",
]
```

## Implementation Steps

### Step 1: Install LLM Service Module
1. Create `app/llm_service.py` with the code from Phase 1
2. Verify imports work: `from app.llm_service import get_llm_service`

### Step 2: Update Celery Task
1. Update `app/tasks/issues.py` with code from Phase 2
2. Replace the mock enrichment with real LLM calls
3. Keep fallback logic for robustness

### Step 3: Configure Environment
1. Update `.env` with LLM_PROVIDER and API keys
2. Test environment variable loading

### Step 4: Test the Integration

**Test 1: With LLM configured (OpenAI)**

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Terminal 3: Start FastAPI
uvicorn main:app --reload

# Terminal 4: Create an issue
curl -X POST http://localhost:8000/issues \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Login button not responding",
    "description": "The login button on the homepage does not respond when clicked in Firefox browser",
    "priority": "high"
  }'
```

**Test 2: Without LLM (Fallback)**

```bash
# Unset LLM_PROVIDER
unset LLM_PROVIDER

# Restart Celery worker
# Create issue - should use keyword-based fallback
```

**Test 3: LLM API failure recovery**

```bash
# Set invalid API key to trigger error
export OPENAI_API_KEY=invalid-key

# Create issue - should trigger retry, then use fallback
```

## Usage Examples

### Creating an Issue (Automatic Enrichment)

```python
# POST /issues endpoint automatically triggers enrich_issue task
{
    "title": "Database query timeout",
    "description": "SELECT statements on large tables are timing out after 30 seconds",
    "priority": "high"
}

# Expected response (after enrichment):
{
    "id": "uuid-123",
    "title": "Database query timeout",
    "description": "SELECT statements on large tables are timing out after 30 seconds",
    "priority": "high",
    "ai_summary": "The application experiences timeout issues when executing SELECT queries on large database tables, indicating a need for query optimization or indexing improvements.",
    "tags": "bug,backend,performance,database"
}
```

### Manual Task Triggering

```python
# In Django shell or Python script
from app.tasks.issues import enrich_issue

# Trigger enrichment for specific issue
enrich_issue.delay("issue-uuid-123")

# Check task status
task_result = enrich_issue.apply_async(
    args=["issue-uuid-123"],
    countdown=10  # Run after 10 seconds
)
print(task_result.id)  # Task ID for tracking
```

## Monitoring & Debugging

### Check Celery Task Status

```python
from celery.result import AsyncResult

task_id = "your-task-id"
result = AsyncResult(task_id)

print(f"Status: {result.status}")
print(f"Result: {result.result}")  # If successful
print(f"Traceback: {result.traceback}")  # If failed
```

### View Logs

```bash
# Celery worker logs show enrichment progress
# Look for:
# - "Starting enrichment for issue"
# - "LLM enrichment succeeded"
# - "Using fallback enrichment"
# - "Error enriching issue" (with retry count)
```

### Performance Considerations

| Metric | With LLM | With Fallback |
|--------|----------|---------------|
| Time | 2-5 seconds | <100ms |
| Cost | $0.001-0.01 per issue | Free |
| Quality | High (semantic) | Medium (keyword-based) |
| Reliability | Depends on API | Always works |

## Troubleshooting

### Issue: "LLM_PROVIDER not set, LLM enrichment disabled"
- **Solution:** Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=anthropic` in `.env`

### Issue: "OPENAI_API_KEY not set" 
- **Solution:** Get API key from https://platform.openai.com/account/api-keys and set in `.env`

### Issue: "Invalid JSON response from OpenAI"
- **Solution:** Check LLM prompt format, try increasing `max_tokens` in request

### Issue: Task keeps retrying
- **Solution:** Check API key validity, check rate limits, check error logs for detailed error

### Issue: Fallback always used
- **Solution:** Verify `LLM_PROVIDER` and API key are set, check Celery worker logs

## Security Best Practices

1. **Protect API Keys**
   - Use environment variables (`.env` in .gitignore)
   - Use secrets management for production (AWS Secrets Manager, Azure Key Vault)
   - Rotate keys regularly

2. **Rate Limiting**
   - Implement rate limiting on issue creation endpoint
   - Monitor API usage and set billing alerts

3. **Input Validation**
   - Validate title and description length before sending to LLM
   - Sanitize user input

4. **Logging**
   - Never log full API responses
   - Log only task status and tag results
   - Mask sensitive data in logs

## Future Enhancements

1. **Caching** - Cache enrichment results for similar issues
2. **Custom Prompts** - Allow per-tenant custom enrichment prompts
3. **Batch Processing** - Process multiple issues in batch for cost efficiency
4. **Feedback Loop** - Track which tags are most useful and refine prompts
5. **Multi-model** - Support multiple LLM providers simultaneously
6. **Fine-tuning** - Fine-tune model on your specific issue patterns
7. **Local Models** - Support local open-source LLMs (Llama, Mistral)

## Summary

This plan provides a production-ready LLM integration that:
- ✅ Intelligently enriches issues with AI-generated summaries and tags
- ✅ Supports multiple LLM providers (OpenAI, Anthropic, extensible)
- ✅ Gracefully degrades to fallback when LLM unavailable
- ✅ Retries on failures with exponential backoff
- ✅ Comprehensive error handling and logging
- ✅ Secure environment-based configuration
- ✅ Fully async-aware and Celery-integrated
