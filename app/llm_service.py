import logging
import json
import os
from typing import Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """
    Result of LLM enrichment process.
    """

    summary: str
    tags: list[str]


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""

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
    """
    Implementation of LLMService using OpenAI API.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Intialize OpenAI Service
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def enrich(self, title: str, description: str) -> EnrichmentResult:
        """Call OpenAI to generate summary and tags"""

        system_prompt = """You are a technical issue analyser. Analyse the given issue and provide a response.
        
DO NOT use markdown formatting. Return ONLY a raw JSON object with no code blocks, no backticks, and no additional text."""

        user_prompt = f"""Analyse this issue and respond with ONLY valid JSON (no markdown):

Title: {title}
Description: {description}

Respond with this exact JSON format:
{{
  "summary": "A clear 1-2 sentence summary of the issue.",
  "tags": ["tag1", "tag2", "tag3"]
}}

Common tags: bug, feature-request, frontend, backend, documentation, performance, security, database, api, ui/ux, urgent, needs-review"""

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
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 250,
                    },
                )
                response.raise_for_status()

                result = response.json()
                logger.debug(f"OpenAI response: {result}")
                
                if not result.get("choices") or not result["choices"][0].get("message"):
                    logger.error(f"Unexpected OpenAI response structure: {result}")
                    raise LLMServiceError("Invalid response structure from OpenAI")
                
                content = result["choices"][0]["message"]["content"]
                
                if not content:
                    logger.error("Empty content in OpenAI response")
                    raise LLMServiceError("Empty content returned from OpenAI")

                # Strip markdown code blocks if present
                content = content.strip()
                if content.startswith("```"):
                    # Remove markdown code block markers
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]  # Remove 'json' language identifier
                    content = content.strip()

                # Parse JSON response
                parsed = json.loads(content)

                return EnrichmentResult(summary=parsed["summary"], tags=parsed["tags"])

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {str(e)}, raw content was: {content if 'content' in locals() else 'N/A'}")
            raise LLMServiceError(f"Invalid JSON response from OpenAI: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI enrichment: {str(e)}")
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
    
    # elif provider == "anthropic":
    #     api_key = os.getenv("ANTHROPIC_API_KEY")
    #     if not api_key:
    #         logger.warning("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY not set")
    #         return None
    #     logger.info("Using Anthropic LLM service")
    #     return AnthropicService(api_key)
    
    elif provider:
        logger.warning(f"Unknown LLM_PROVIDER: {provider}")
        return None
    else:
        logger.info("LLM_PROVIDER not set, LLM enrichment disabled")
        return None
