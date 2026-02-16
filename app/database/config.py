import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Get database URLs from environment or use defaults
ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/IssueTracker"
)
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/IssueTracker"
)

# Create async engine for FastAPI
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set to False in production
    future=True
)

# Create async session factory for FastAPI
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create synchronous engine for Celery tasks
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)

# Create synchronous session factory for Celery tasks
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
