"""External/public scoring API, authenticated via X-API-Key (Section 5)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_api_key_owner
from app.db.session import get_db
from app.models.enums import Tier
from app.models.lead import Lead
from app.models.project import Project
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadOut
from app.services import scoring
from app.worker.queue import enqueue

router = APIRouter(prefix="/external", tags=["external-api"])


@router.post("/projects/{project_id}/score", response_model=LeadOut)
async def score(
    project_id: uuid.UUID,
    payload: LeadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_api_key_owner),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.rubric:
        raise HTTPException(status_code=400, detail="Project has no rubric")

    lead = Lead(project_id=project_id, company_name=payload.company_name, domain=payload.domain)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    await scoring.score_lead_tier1(db, lead, project.rubric)
    db.commit()
    if project.tier == Tier.deep:
        await enqueue("enrich_and_capture", str(lead.id))
    db.refresh(lead)
    return LeadOut.model_validate(lead)
