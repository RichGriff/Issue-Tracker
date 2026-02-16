"""API route modules for FastAPI endpoints."""

from app.routes.issues import router as issues_router

__all__ = ["issues_router"]
