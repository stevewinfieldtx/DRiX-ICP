"""Section 9 — pattern mining & dynamic ICP discovery (the monetization hook)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.lead import Lead
from app.models.project import Project
from app.models.user import User
from app.schemas.analytics import AnalyzeRequest, ApplySuggestionsRequest
from app.services.analytics import narrate as narrate_svc
from app.services.analytics import patterns

router = APIRouter(prefix="/projects/{project_id}/analytics", tags=["analytics"])


def _project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/analyze")
async def analyze(
    project_id: uuid.UUID,
    payload: AnalyzeRequest = AnalyzeRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _project(db, project_id, user)
    leads = db.execute(select(Lead).where(Lead.project_id == project_id)).scalars().all()

    result = patterns.mine(
        leads,
        top_colours=set(payload.top_colours) if payload.top_colours else None,
        bottom_colours=set(payload.bottom_colours) if payload.bottom_colours else None,
    )
    summary = (
        await narrate_svc.narrate(result) if payload.narrate
        else narrate_svc.deterministic_summary(result)
    )
    return {
        "cohorts": {"top_n": result.top_n, "bottom_n": result.bottom_n},
        "summary": summary,
        "findings": [
            {"feature": f.feature, "kind": f.kind, "direction": f.direction,
             "effect": f.effect, "headline": f.headline, "detail": f.detail}
            for f in result.findings
        ],
        "suggested_signals": result.suggested_signals,
        "hidden_gems": result.hidden_gems,
        "notes": result.notes,
    }


@router.post("/suggestions/apply")
async def apply_suggestions(
    project_id: uuid.UUID,
    payload: ApplySuggestionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Append accepted suggested signals to the project rubric (closing the loop)."""
    project = _project(db, project_id, user)
    if not project.rubric:
        raise HTTPException(status_code=400, detail="Project has no rubric to extend")

    leads = db.execute(select(Lead).where(Lead.project_id == project_id)).scalars().all()
    result = patterns.mine(leads)
    by_key = {s["key"]: s for s in result.suggested_signals}

    rubric = dict(project.rubric)
    existing = {s.get("key") for s in rubric.get("signals", [])}
    added = []
    for key in payload.keys:
        s = by_key.get(key)
        if not s or key in existing:
            continue
        rubric.setdefault("signals", []).append({
            "key": s["key"], "label": s["label"], "weight": s["suggested_weight"],
            "type": s["type"], "description": s["rationale"], "source": "pattern_miner",
        })
        added.append(key)

    project.rubric = rubric
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(project, "rubric")
    db.commit()
    return {"added": added, "rubric": project.rubric}
