from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from .database import Base


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="Submitted")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)