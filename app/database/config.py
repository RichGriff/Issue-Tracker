from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Use asyncpg driver for PostgreSQL
db_url = "postgresql+asyncpg://postgres:password@localhost:5432/IssueTracker"
# Synchronous (psycopg2) version for Celery tasks
sync_db_url = "postgresql://postgres:password@localhost:5432/IssueTracker"

# Create async engine
engine = create_async_engine(
    db_url,
    echo=False,  # Set to False in production
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create synchronous engine for Celery tasks
sync_engine = create_engine(sync_db_url, echo=False)

# Create synchronous session factory for Celery tasks
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
