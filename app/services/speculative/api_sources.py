"""Section 8.2 / 8.3 via OFFICIAL or LICENSED APIs (no scraping of 3rd-party sites).

Every adapter is gated on its API key and returns {} when unconfigured, so the
capture pipeline runs without them. Swap the placeholder endpoints for whichever
licensed provider you contract with (the response is normalized either way).
"""
import httpx

from app.core.config import settings


async def firmographics(domain: str | None) -> dict:
    """LinkedIn-style headcount / titles / leaders via a LICENSED people-data API.

    Returns the 'linkedin'-shaped sub-object expected by the brief, sourced
    compliantly. Replace the endpoint with your contracted provider.
    """
    if not settings.people_data_api_key or not domain:
        return {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.your-people-data-provider.example/v1/company",
                params={"domain": domain},
                headers={"Authorization": f"Bearer {settings.people_data_api_key}"},
            )
        if resp.status_code != 200:
            return {}
        d = resp.json()
    except Exception:  # noqa: BLE001
        return {}

    return {
        "company_size": d.get("employee_count_range"),
        "sales_titles_count": d.get("sales_headcount"),
        "marketing_titles_count": d.get("marketing_headcount"),
        "sales_leaders_count": d.get("sales_leaders"),
        "marketing_leaders_count": d.get("marketing_leaders"),
        "followers": d.get("followers"),
        "specialties": d.get("specialties"),
        "description": d.get("description"),
        "_source": "licensed_people_data_api",
    }


async def news(company_name: str) -> list[dict]:
    if not settings.news_api_key or not company_name:
        return []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={"q": company_name, "pageSize": 5, "sortBy": "publishedAt"},
                headers={"X-Api-Key": settings.news_api_key},
            )
        if resp.status_code != 200:
            return []
        arts = resp.json().get("articles", [])
    except Exception:  # noqa: BLE001
        return []
    return [
        {"headline": a.get("title"), "date": a.get("publishedAt"),
         "source": (a.get("source") or {}).get("name")}
        for a in arts
    ]


async def funding(company_name: str) -> dict:
    """Crunchbase via its OFFICIAL API (key required)."""
    if not settings.crunchbase_api_key or not company_name:
        return {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.crunchbase.com/api/v4/searches/organizations",
                params={"user_key": settings.crunchbase_api_key, "query": company_name},
            )
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:  # noqa: BLE001
        return {}
