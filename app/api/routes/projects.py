import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_owned(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = Project(owner_id=user.id, name=payload.name, tier=payload.tier)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(Project).where(Project.owner_id == user.id)).scalars().all()
    return [_to_out(p) for p in rows]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _to_out(_get_owned(db, project_id, user))


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    db.delete(_get_owned(db, project_id, user))
    db.commit()


def _to_out(p: Project) -> ProjectOut:
    return ProjectOut(id=str(p.id), name=p.name, tier=p.tier, rubric=p.rubric)
