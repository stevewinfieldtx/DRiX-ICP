"""Section 8.2 / 8.3 via licensed APIs (no scraping of 3rd-party sites).

  - firmographics(): headcount by department/seniority + company profile via Apollo
  - news():          recent news via Serper (Google News)
  - funding():       funding fields from Apollo's organization record

Every adapter is gated on its key and returns {} / [] / None when unconfigured.
Counts only — no individuals are stored.
"""
import httpx

from app.core.config import settings
from app.services import apollo


async def firmographics(domain: str | None) -> dict:
    """LinkedIn-style headcounts + company profile, sourced compliantly via Apollo.

    Keeps the 'linkedin'-shaped object the rest of the system (derived.py,
    SCHEMA.md) expects, for schema continuity.
    """
    if not settings.apollo_api_key or not domain:
        return {}
    org = await apollo.org_enrich(domain)
    sales = await apollo.people_count(domain, ["sales"])
    marketing = await apollo.people_count(domain, ["marketing"])
    sales_leaders = await apollo.people_count(domain, ["sales"], apollo.LEADER_SENIORITIES)
    marketing_leaders = await apollo.people_count(domain, ["marketing"], apollo.LEADER_SENIORITIES)

    if not (org or sales or marketing):
        return {}
    return {
        "company_size": org.get("estimated_num_employees"),
        "sales_titles_count": sales,
        "marketing_titles_count": marketing,
        "sales_leaders_count": sales_leaders,
        "marketing_leaders_count": marketing_leaders,
        "specialties": org.get("keywords"),
        "description": org.get("short_description") or org.get("seo_description"),
        "_source": "apollo",
    }


async def news(company_name: str) -> list[dict]:
    if not settings.serper_api_key or not company_name:
        return []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://google.serper.dev/news",
                json={"q": company_name, "num": 5},
                headers={"X-API-KEY": settings.serper_api_key,
                         "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            return []
        items = resp.json().get("news", [])
    except Exception:  # noqa: BLE001
        return []
    return [
        {"headline": i.get("title"), "date": i.get("date"),
         "source": i.get("source"), "link": i.get("link")}
        for i in items
    ]


async def funding(domain: str | None) -> dict:
    """Funding fields from Apollo's organization record (replaces Crunchbase)."""
    if not settings.apollo_api_key or not domain:
        return {}
    org = await apollo.org_enrich(domain)
    if not org:
        return {}
    out = {
        "total_funding": org.get("total_funding"),
        "latest_funding_stage": org.get("latest_funding_stage"),
        "latest_funding_round_date": org.get("latest_funding_round_date"),
    }
    return out if any(v is not None for v in out.values()) else {}
