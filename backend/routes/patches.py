
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/patches", tags=["Patch Reviews"])


class PatchCreate(BaseModel):
    bug_id: int
    original_code: str = Field(min_length=1)
    proposed_code: str = Field(min_length=1)
    explanation: str | None = None


class PatchDecision(BaseModel):
    status: str


@router.post("", status_code=201)
def create_patch(patch: PatchCreate, db: Session = Depends(get_db)):

    bug = db.query(models.BugReport).filter(
        models.BugReport.id == patch.bug_id
    ).first()

    if bug is None:
        raise HTTPException(status_code=404, detail="Bug report not found")

    new_patch = models.PatchReview(
        bug_id=patch.bug_id,
        original_code=patch.original_code,
        proposed_code=patch.proposed_code,
        explanation=patch.explanation,
        status="Pending Review"
    )

    try:
        db.add(new_patch)
        db.commit()
        db.refresh(new_patch)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save patch"
        )

    return {
        "id": new_patch.id,
        "bug_id": new_patch.bug_id,
        "original_code": new_patch.original_code,
        "proposed_code": new_patch.proposed_code,
        "explanation": new_patch.explanation,
        "status": new_patch.status,
        "created_at": new_patch.created_at
    }


@router.get("")
def get_patches(db: Session = Depends(get_db)):

    patches = (
        db.query(models.PatchReview)
        .order_by(models.PatchReview.created_at.desc())
        .all()
    )

    return [
        {
            "id": patch.id,
            "bug_id": patch.bug_id,
            "original_code": patch.original_code,
            "proposed_code": patch.proposed_code,
            "explanation": patch.explanation,
            "status": patch.status,
            "created_at": patch.created_at,
            "reviewed_at": patch.reviewed_at
        }
        for patch in patches
    ]


@router.get("/{patch_id}")
def get_patch(patch_id: int, db: Session = Depends(get_db)):

    patch = db.query(models.PatchReview).filter(
        models.PatchReview.id == patch_id
    ).first()

    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    return {
        "id": patch.id,
        "bug_id": patch.bug_id,
        "original_code": patch.original_code,
        "proposed_code": patch.proposed_code,
        "explanation": patch.explanation,
        "status": patch.status,
        "created_at": patch.created_at,
        "reviewed_at": patch.reviewed_at
    }


@router.patch("/{patch_id}/review")
def review_patch(
    patch_id: int,
    decision: PatchDecision,
    db: Session = Depends(get_db)
):

    if decision.status not in ["Approved", "Rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be Approved or Rejected"
        )

    patch = db.query(models.PatchReview).filter(
        models.PatchReview.id == patch_id
    ).first()

    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    if patch.status != "Pending Review":
        raise HTTPException(409, "Patch already reviewed")
    patch.status = decision.status
    db.get(models.BugReport, patch.bug_id).status = "Patch " + decision.status
    patch.reviewed_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(patch)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update patch review"
        )

    return {
        "message": f"Patch {decision.status.lower()} successfully",
        "id": patch.id,
        "status": patch.status,
        "reviewed_at": patch.reviewed_at
    }
