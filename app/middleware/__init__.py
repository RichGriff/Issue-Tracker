"""Custom middleware for request processing and inspection."""

from app.middleware.timing import timing_middleware

__all__ = ["timing_middleware"]
