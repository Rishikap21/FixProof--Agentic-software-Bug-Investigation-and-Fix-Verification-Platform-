
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


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    project_name = Column(String(200), nullable=False)

    original_filename = Column(String(255), nullable=False)

    extracted_path = Column(String(1000), nullable=False)

    status = Column(
        String(50),
        nullable=False,
        default="Uploaded"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
