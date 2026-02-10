from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Use asyncpg driver for PostgreSQL
db_url = "postgresql+asyncpg://postgres:password@localhost:5432/IssueTracker"

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

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
