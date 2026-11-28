
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db


router = APIRouter(
    prefix="/verification-reports",
    tags=["Verification Reports"]
)


class VerificationCreate(BaseModel):
    patch_id: int
    status: Literal["Passed", "Failed"]
    test_results: str = Field(min_length=1)
    verification_details: str | None = None


def report_to_dict(report):
    return {
        "id": report.id,
        "bug_id": report.bug_id,
        "patch_id": report.patch_id,
        "status": report.status,
        "test_results": report.test_results,
        "verification_details": report.verification_details,
        "created_at": (
            report.created_at.isoformat()
            if report.created_at else None
        )
    }


# Manual report creation intentionally not exposed.
def create_verification_report(
    report: VerificationCreate,
    db: Session = Depends(get_db)
):

    patch = db.query(models.PatchReview).filter(
        models.PatchReview.id == report.patch_id
    ).first()

    if patch is None:
        raise HTTPException(
            status_code=404,
            detail="Patch not found"
        )

    if patch.status != "Approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved patches can be verified"
        )

    new_report = models.VerificationReport(
        bug_id=patch.bug_id,
        patch_id=report.patch_id,
        status=report.status,
        test_results=report.test_results,
        verification_details=report.verification_details
    )

    try:
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

    except Exception as e:
        db.rollback()
        print("Verification report error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="Could not save verification report"
        )

    return report_to_dict(new_report)


@router.get("")
def get_verification_reports(
    db: Session = Depends(get_db)
):

    reports = (
        db.query(models.VerificationReport)
        .order_by(
            models.VerificationReport.created_at.desc()
        )
        .all()
    )

    return [
        report_to_dict(report)
        for report in reports
    ]


@router.get("/{report_id}")
def get_verification_report(
    report_id: int,
    db: Session = Depends(get_db)
):

    report = db.query(models.VerificationReport).filter(
        models.VerificationReport.id == report_id
    ).first()

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Verification report not found"
        )

    return report_to_dict(report)
