import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.services import rubric_generation

router = APIRouter(prefix="/projects/{project_id}/rubric", tags=["rubric"])


@router.post("/generate")
async def generate_rubric(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = db.execute(
        select(Document).where(Document.project_id == project_id)
    ).scalars().all()
    corpus = "\n\n".join(d.extracted_text or "" for d in docs).strip()
    if not corpus:
        raise HTTPException(status_code=400, detail="No extracted document text to build rubric")

    rubric = await rubric_generation.generate(corpus)
    project.rubric = rubric
    db.commit()
    return rubric


@router.get("")
def get_rubric(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.rubric or {}
