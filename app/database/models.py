from sqlalchemy import Column, Enum, String
from app.database.config import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    status = Column(Enum("open", "closed", name="issue_status"))
    priority = Column(Enum("low", "medium", "high", name="issue_priority"))

    ai_summary = Column(String, nullable=True)
    tags = Column(String, nullable=True)