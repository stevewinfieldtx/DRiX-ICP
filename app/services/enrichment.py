"""Tier 2 enrichment via Apollo.io (licensed B2B data).

enrich() collects raw Apollo payloads; resolve_signals() maps them to rubric
signal points. Degrades gracefully to {} when no Apollo key is configured.
"""
from app.services import apollo


async def enrich(domain: str) -> dict:
    """Collect raw enrichment payloads keyed by source."""
    org = await apollo.org_enrich(domain)
    return {"apollo_org": org}


def resolve_signals(rubric: dict, enriched: dict) -> dict:
    """Map raw Apollo data -> {signal_key: points} per rubric weights.

    Deterministic, rules-based. Awards a signal's full weight when the relevant
    data is present (extend the matching logic for your real rubric).
    """
    org = (enriched or {}).get("apollo_org") or {}
    employees = org.get("estimated_num_employees")
    industry = org.get("industry")
    technologies = org.get("technology_names") or org.get("technologies") or []

    signals: dict[str, float] = {}
    for sig in rubric.get("signals", []):
        key, weight = sig.get("key"), float(sig.get("weight", 0))
        if key == "employee_count":
            signals[key] = weight if employees else 0.0
        elif key == "industry":
            signals[key] = weight if industry else 0.0
        elif key == "tech_stack":
            signals[key] = weight if technologies else 0.0
        else:
            signals[key] = 0.0
    return signals
