"""Scoring engine.

Tier 1 (Light): LLM-only score from company name/domain against the rubric.
Tier 2 (Deep): deterministic score from resolved enrichment signals.

Both map a 0-100 score to a colour using the rubric thresholds. The speculative
data captured in Section 8 is intentionally NOT used here (additive, future use).
"""
from sqlalchemy.orm import Session

from app.models.enums import LeadColour
from app.models.lead import Lead
from app.services.llm import chat_json

_T1_SYSTEM = (
    "You are scoring a sales lead against an Ideal Customer Profile rubric. "
    "Given the rubric signals and the company name/domain, estimate a fit score. "
    "Return JSON: {'score': 0-100, 'signals': {<signal_key>: <points>}, 'rationale': str}. "
    "Be conservative when you lack information."
)


def colour_for(score: float, thresholds: dict) -> LeadColour:
    if score >= thresholds.get("dark_green", 80):
        return LeadColour.dark_green
    if score >= thresholds.get("green", 60):
        return LeadColour.green
    if score >= thresholds.get("yellow", 40):
        return LeadColour.yellow
    return LeadColour.unqualified


async def score_lead_tier1(db: Session, lead: Lead, rubric: dict) -> None:
    user = (
        f"Rubric: {rubric}\n\n"
        f"Company: {lead.company_name}\nDomain: {lead.domain or 'unknown'}"
    )
    result = await chat_json(_T1_SYSTEM, user)
    score = float(result.get("score", 0)) if result else 0.0
    lead.signals = result.get("signals") if result else None
    lead.score = round(score, 2)
    lead.colour = colour_for(score, rubric.get("thresholds", {}))


def score_lead_tier2(lead: Lead, rubric: dict) -> None:
    """Deterministic scoring from resolved signals in lead.signals.

    Expects lead.signals to hold {signal_key: points} already resolved from
    enrichment. Sums points, clamps to 0-100, assigns colour.
    """
    signals = lead.signals or {}
    total = sum(float(v) for v in signals.values() if isinstance(v, (int, float)))
    total = max(0.0, min(100.0, total))
    lead.score = round(total, 2)
    lead.colour = colour_for(total, rubric.get("thresholds", {}))
