
from datetime import datetime


from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from sqlalchemy import Column, DateTime, Integer, String, Text

from .database import Base

from sqlalchemy import ForeignKey


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
        String(100),
        nullable=False,
        default="Uploaded"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class PatchReview(Base):
    __tablename__ = "patch_reviews"

    id = Column(Integer, primary_key=True, index=True)

    bug_id = Column(
        Integer,
        ForeignKey("bug_reports.id"),
        nullable=False
    )

    original_code = Column(Text, nullable=False)
    proposed_code = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)

    status = Column(
        String(100),
        nullable=False,
        default="Pending Review"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    reviewed_at = Column(DateTime, nullable=True)


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(Integer, primary_key=True, index=True)

    bug_id = Column(
        Integer,
        ForeignKey("bug_reports.id"),
        nullable=False
    )

    patch_id = Column(
        Integer,
        ForeignKey("patch_reviews.id"),
        nullable=False
    )

    status = Column(String(50), default="Pending")

    test_results = Column(Text, nullable=True)

    verification_details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

