import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import Tier
from app.models.lead import Lead
from app.models.project import Project
from app.models.user import User
from app.schemas.lead import LeadAssign, LeadCreate, LeadOut
from app.services import scoring
from app.worker.queue import enqueue

router = APIRouter(prefix="/projects/{project_id}/leads", tags=["leads"])


def _project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=LeadOut)
async def create_lead(
    project_id: uuid.UUID,
    payload: LeadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project(db, project_id, user)
    if not project.rubric:
        raise HTTPException(status_code=400, detail="Generate a rubric before scoring leads")

    lead = Lead(project_id=project_id, company_name=payload.company_name, domain=payload.domain)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Tier 1 (LLM-only) scoring runs inline; Tier 2 enrichment + Section 8 capture go to the worker.
    await scoring.score_lead_tier1(db, lead, project.rubric)
    db.commit()
    if project.tier == Tier.deep:
        await enqueue("enrich_and_capture", str(lead.id))

    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.get("", response_model=list[LeadOut])
def list_leads(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _project(db, project_id, user)
    rows = db.execute(select(Lead).where(Lead.project_id == project_id)).scalars().all()
    return [LeadOut.model_validate(r) for r in rows]


@router.patch("/{lead_id}", response_model=LeadOut)
def assign_lead(
    project_id: uuid.UUID,
    lead_id: uuid.UUID,
    payload: LeadAssign,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _project(db, project_id, user)
    lead = db.get(Lead, lead_id)
    if not lead or lead.project_id != project_id:
        raise HTTPException(status_code=404, detail="Lead not found")
    if payload.assigned_to is not None:
        lead.assigned_to = uuid.UUID(payload.assigned_to)
    if payload.status is not None:
        lead.status = payload.status
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.get("/{lead_id}/speculative")
def get_speculative_data(
    project_id: uuid.UUID,
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Powers the frontend 'Spec Data' modal (Section 10)."""
    _project(db, project_id, user)
    lead = db.get(Lead, lead_id)
    if not lead or lead.project_id != project_id:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": lead.speculative_status.value, "data": lead.speculative_data or {}}
