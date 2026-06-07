"""Apollo.io client — licensed B2B data (firmographics, technographics, headcounts,
funding). Replaces Clearbit / BuiltWith / Crunchbase / people-data provider with a
single source that keeps the compliant posture (Apollo licenses its own database).

Both calls are gated on settings.apollo_api_key and return {} / None when absent,
so the app still runs offline and the test suite stays green.
"""
import httpx

from app.core.config import settings

_BASE = "https://api.apollo.io/api/v1"

# Apollo seniority buckets we treat as "leaders"
LEADER_SENIORITIES = ["owner", "founder", "c_suite", "partner", "vp", "head", "director"]


def _headers() -> dict:
    return {"x-api-key": settings.apollo_api_key or "", "Content-Type": "application/json"}


async def org_enrich(domain: str | None) -> dict:
    """Company firmographics + technographics + funding for a domain."""
    if not settings.apollo_api_key or not domain:
        return {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{_BASE}/organizations/enrich",
                params={"domain": domain}, headers=_headers(),
            )
        if resp.status_code != 200:
            return {}
        return resp.json().get("organization") or {}
    except Exception:  # noqa: BLE001
        return {}


async def people_count(
    domain: str | None, departments: list[str], seniorities: list[str] | None = None
) -> int | None:
    """Count people at a company matching department(s)/seniority via Apollo search.

    Uses the search endpoint's pagination total rather than pulling person records,
    so we get aggregate counts only — no individuals stored.
    """
    if not settings.apollo_api_key or not domain:
        return None
    body = {
        "q_organization_domains": domain,
        "person_departments": departments,
        "page": 1,
        "per_page": 1,
    }
    if seniorities:
        body["person_seniorities"] = seniorities
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_BASE}/mixed_people/search", json=body, headers=_headers()
            )
        if resp.status_code != 200:
            return None
        return (resp.json().get("pagination") or {}).get("total_entries")
    except Exception:  # noqa: BLE001
        return None
