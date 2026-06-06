"""Assemble the speculative_data JSONB (Section 8) from compliant sources.

Runs AFTER scoring; purely additive and never feeds the current score.
Output shape (all sections null/empty-safe):

{
  "website":  {... first-party site capture, incl. roles_summary, pain_language},
  "linkedin": {... firmographics via LICENSED api ...} | null,
  "dns":      {... spf / dmarc / mx_provider / security_txt ...},
  "news":     [ {headline, date, source}, ... ],
  "funding":  {...} | null,
  "derived":  {
     "ratios":   {gtm_to_build_ratio, technical_to_sales_ratio,
                  sales_to_marketing_ratio, sales_leader_to_ic_ratio, ...},
     "absence":  {missing_security_page, missing_dmarc, weak_dmarc_policy, ...},
     "triggers": {hiring_for_new_function, dormant_blog, stale_copyright,
                  recent_funding, open_roles_total}
  },
  "_captured_at": "<iso8601>"
}
"""
from datetime import datetime, timezone

from app.models.enums import SpeculativeStatus
from app.services.speculative import api_sources, derived, dns_signals, site_scraper


async def capture(company_name: str, domain: str | None) -> tuple[dict, SpeculativeStatus]:
    data: dict = {}
    errors = 0

    async def _try(key, coro, default):
        nonlocal errors
        try:
            data[key] = await coro
        except Exception:  # noqa: BLE001
            data[key] = default
            errors += 1

    await _try("website", site_scraper.capture_site(domain), None)
    await _try("dns", dns_signals.capture_dns(domain), {})
    # key kept as 'linkedin' for schema continuity; sourced via LICENSED api.
    await _try("linkedin", api_sources.firmographics(domain), None)
    await _try("news", api_sources.news(company_name), [])
    await _try("funding", api_sources.funding(company_name), None)

    # derived metrics are local/pure; never count toward source errors
    try:
        data["derived"] = derived.derive(data, datetime.now(timezone.utc).year)
    except Exception:  # noqa: BLE001
        data["derived"] = None

    data["_captured_at"] = datetime.now(timezone.utc).isoformat()

    status = (
        SpeculativeStatus.failed if errors >= 5
        else SpeculativeStatus.partial if errors
        else SpeculativeStatus.complete
    )
    return data, status
