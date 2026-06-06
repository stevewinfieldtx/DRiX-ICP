"""ARQ worker. Run with:  arq app.worker.main.WorkerSettings"""
import uuid

from arq.connections import RedisSettings

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.models.project import Project
from app.services import enrichment, scoring
from app.services.speculative import capture as spec_capture


async def enrich_and_capture(ctx, lead_id: str) -> str:
    """Tier 2: deterministic enrichment scoring + additive Section 8 capture."""
    db = SessionLocal()
    try:
        lead = db.get(Lead, uuid.UUID(lead_id))
        if not lead:
            return "lead-not-found"
        project = db.get(Project, lead.project_id)
        rubric = (project.rubric if project else None) or {}

        # --- Tier 2 deterministic scoring from official enrichment APIs ---
        lead.enriched_data = await enrichment.enrich(lead.domain or "")
        lead.signals = enrichment.resolve_signals(rubric, lead.enriched_data)
        scoring.score_lead_tier2(lead, rubric)
        db.commit()

        # --- Section 8: compliant speculative capture (additive, not scored) ---
        data, status = await spec_capture.capture(lead.company_name, lead.domain)
        lead.speculative_data = data
        lead.speculative_status = status
        db.commit()
        return f"ok:{status.value}"
    finally:
        db.close()


class WorkerSettings:
    functions = [enrich_and_capture]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
