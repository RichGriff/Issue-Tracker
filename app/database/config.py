from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base

db_url = "postgresql://postgres:password@localhost:5432/IssueTracker"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create all tables on startup
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
