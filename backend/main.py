
import shutil
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .schemas import BugCreate, BugResponse, ProjectResponse
from .services.project_upload import (
    ProjectUploadError,
    extract_project,
)

# Create database tables.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FixProof API",
    description="Agentic Software Bug Investigation and Fix Verification Platform",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to FixProof API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------------- BUG REPORT ENDPOINTS ----------------

@app.post("/bugs", response_model=BugResponse, status_code=201)
def create_bug(bug: BugCreate, db: Session = Depends(get_db)):
    new_bug = models.BugReport(
        title=bug.title,
        description=bug.description,
    )

    db.add(new_bug)
    db.commit()
    db.refresh(new_bug)

    return new_bug


@app.get("/bugs", response_model=list[BugResponse])
def get_bugs(db: Session = Depends(get_db)):
    return db.query(models.BugReport).order_by(
        models.BugReport.created_at.desc()
    ).all()


@app.get("/bugs/{bug_id}", response_model=BugResponse)
def get_bug(bug_id: int, db: Session = Depends(get_db)):
    bug = db.query(models.BugReport).filter(
        models.BugReport.id == bug_id
    ).first()

    if bug is None:
        raise HTTPException(
            status_code=404,
            detail="Bug report not found"
        )

    return bug


# ---------------- PROJECT UPLOAD ENDPOINTS ----------------

@app.post(
    "/projects/upload",
    response_model=ProjectResponse,
    status_code=201
)
def upload_project(
    file: UploadFile = File(...),
    project_name: str = Form(default="Uploaded Project", max_length=200),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    # Handle both Windows and Unix filename separators.
    original_filename = file.filename.replace("\\", "/").split("/")[-1]

    if not original_filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported."
        )

    if not project_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Project name cannot be empty."
        )

    extracted_path = None

    try:
        extracted_path = extract_project(file)

        new_project = models.Project(
            project_name=project_name.strip(),
            original_filename=original_filename[:255],
            extracted_path=extracted_path,
            status="Uploaded",
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return new_project

    except ProjectUploadError as exc:
        if extracted_path:
            shutil.rmtree(extracted_path, ignore_errors=True)

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:
        db.rollback()

        if extracted_path:
            shutil.rmtree(extracted_path, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail="Project upload failed. Please try again."
        )

    finally:
        file.file.close()


@app.get("/projects", response_model=list[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(
        models.Project.created_at.desc()
    ).all()


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(
        models.Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return project
