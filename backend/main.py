
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .schemas import BugCreate, BugResponse
from .routes import projects

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FixProof API",
    description="Agentic Software Bug Investigation and Fix Verification Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register project routes
app.include_router(projects.router)


@app.get("/")
def home():
    return {
        "message": "Welcome to FixProof API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/bugs", response_model=BugResponse, status_code=201)
def create_bug(bug: BugCreate, db: Session = Depends(get_db)):
    new_bug = models.BugReport(
        title=bug.title,
        description=bug.description
    )

    db.add(new_bug)
    db.commit()
    db.refresh(new_bug)

    return new_bug


@app.get("/bugs", response_model=list[BugResponse])
def get_bugs(db: Session = Depends(get_db)):
    return (
        db.query(models.BugReport)
        .order_by(models.BugReport.created_at.desc())
        .all()
    )


@app.get("/bugs/{bug_id}", response_model=BugResponse)
def get_bug(bug_id: int, db: Session = Depends(get_db)):
    bug = (
        db.query(models.BugReport)
        .filter(models.BugReport.id == bug_id)
        .first()
    )

    if bug is None:
        raise HTTPException(
            status_code=404,
            detail="Bug report not found"
        )

    return bug
