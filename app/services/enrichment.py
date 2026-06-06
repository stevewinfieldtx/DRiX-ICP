"""Tier 2 enrichment via OFFICIAL APIs only (Clearbit, BuiltWith).

Each adapter returns a dict of raw data; resolve_signals() maps raw data to
rubric signal points. All adapters degrade gracefully (return {}) when the
relevant API key is not configured, so the scaffold runs offline.
"""
import httpx

from app.core.config import settings


async def clearbit_company(domain: str) -> dict:
    if not settings.clearbit_api_key or not domain:
        return {}
    url = f"https://company.clearbit.com/v2/companies/find?domain={domain}"
    headers = {"Authorization": f"Bearer {settings.clearbit_api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return {}
        return resp.json()


async def builtwith(domain: str) -> dict:
    if not settings.builtwith_api_key or not domain:
        return {}
    url = (
        "https://api.builtwith.com/v21/api.json"
        f"?KEY={settings.builtwith_api_key}&LOOKUP={domain}"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {}
        return resp.json()


async def enrich(domain: str) -> dict:
    """Collect raw enrichment payloads keyed by provider."""
    return {
        "clearbit": await clearbit_company(domain),
        "builtwith": await builtwith(domain),
    }


def resolve_signals(rubric: dict, enriched: dict) -> dict:
    """Map raw enrichment data -> {signal_key: points} per rubric weights.

    This is a deterministic, rules-based mapping. The stub awards a signal's
    full weight when data is present and matches; extend per your real rubric.
    """
    signals: dict[str, float] = {}
    clearbit = enriched.get("clearbit") or {}
    metrics = clearbit.get("metrics") or {}

    for sig in rubric.get("signals", []):
        key, weight = sig.get("key"), float(sig.get("weight", 0))
        if key == "employee_count":
            emp = metrics.get("employees")
            signals[key] = weight if emp else 0.0
        elif key == "industry":
            cat = (clearbit.get("category") or {}).get("industry")
            signals[key] = weight if cat else 0.0
        elif key == "tech_stack":
            signals[key] = weight if enriched.get("builtwith") else 0.0
        else:
            signals[key] = 0.0
    return signals
