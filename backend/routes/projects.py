
import os
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSION = ".zip"


@router.post("/upload")
async def upload_project(
    project_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not project_name.strip():
        raise HTTPException(status_code=400, detail="Project name is required")

    if not file.filename or Path(file.filename).suffix.lower() != ALLOWED_EXTENSION:
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    unique_id = str(uuid.uuid4())
    project_folder = UPLOAD_DIR / unique_id
    zip_path = UPLOAD_DIR / f"{unique_id}.zip"

    try:
        contents = await file.read(MAX_FILE_SIZE + 1)

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="ZIP file exceeds 50 MB")

        zip_path.write_bytes(contents)

        if not zipfile.is_zipfile(zip_path):
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

        project_folder.mkdir(parents=True, exist_ok=False)

        with zipfile.ZipFile(zip_path, "r") as archive:
            total_size = 0

            for info in archive.infolist():
                member_path = Path(info.filename)

                if member_path.is_absolute() or ".." in member_path.parts:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP contains an unsafe file path"
                    )

                if info.file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP contains an oversized file"
                    )

                total_size += info.file_size

                if total_size > 200 * 1024 * 1024:
                    raise HTTPException(
                        status_code=400,
                        detail="Extracted project exceeds 200 MB"
                    )

                if info.flag_bits & 0x1:
                    raise HTTPException(
                        status_code=400,
                        detail="Encrypted ZIP files are not supported"
                    )

            archive.extractall(project_folder)

        new_project = models.Project(
            project_name=project_name.strip(),
            original_filename=file.filename,
            extracted_path=str(project_folder),
            status="Uploaded"
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return {
            "message": "Project uploaded successfully",
            "id": new_project.id,
            "project_name": new_project.project_name,
            "original_filename": new_project.original_filename,
            "status": new_project.status,
            "created_at": new_project.created_at
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Project upload failed"
        ) from error

    finally:
        await file.close()
        if zip_path.exists():
            zip_path.unlink(missing_ok=True)


@router.get("")
def get_projects(db: Session = Depends(get_db)):
    projects = (
        db.query(models.Project)
        .order_by(models.Project.created_at.desc())
        .all()
    )

    return [
        {
            "id": project.id,
            "project_name": project.project_name,
            "original_filename": project.original_filename,
            "status": project.status,
            "created_at": project.created_at
        }
        for project in projects
    ]


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(
        models.Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "project_name": project.project_name,
        "original_filename": project.original_filename,
        "status": project.status,
        "created_at": project.created_at
    }
