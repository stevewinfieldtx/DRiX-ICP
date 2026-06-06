"""Derived metrics computed across captured sources (pure functions, testable).

These are the 'interaction' and 'absence' signals that single fields miss.
Nothing here makes network calls. All ratios are None-safe (return None on
missing data or divide-by-zero) so the pattern miner can distinguish 'unknown'
from a real value.
"""
from __future__ import annotations


def _safe_ratio(numerator, denominator) -> float | None:
    try:
        n, d = float(numerator), float(denominator)
    except (TypeError, ValueError):
        return None
    if d == 0:
        return None
    return round(n / d, 2)


def _headcounts(linkedin: dict | None, website: dict | None) -> dict:
    """Best-available headcount per function. Prefer licensed firmographics,
    fall back to website open-role / mention signals."""
    li = linkedin or {}
    web = website or {}
    summary = (web.get("roles_summary") or {}).get("by_department", {})
    mentions = web.get("team_mentions") or {}

    def pick(*vals):
        for v in vals:
            if isinstance(v, (int, float)) and v:
                return v
        return None

    return {
        "sales": pick(li.get("sales_titles_count"), summary.get("sales"),
                      mentions.get("sales_mentions")),
        "marketing": pick(li.get("marketing_titles_count"), summary.get("marketing"),
                          mentions.get("marketing_mentions")),
        "engineering": pick(summary.get("engineering"), mentions.get("engineering_mentions")),
        "sales_leaders": pick(li.get("sales_leaders_count")),
        "marketing_leaders": pick(li.get("marketing_leaders_count")),
    }


def compute_ratios(linkedin: dict | None, website: dict | None) -> dict:
    hc = _headcounts(linkedin, website)
    sales, mkt, eng = hc["sales"], hc["marketing"], hc["engineering"]
    gtm = (sales or 0) + (mkt or 0)

    role_sum = ((website or {}).get("roles_summary") or {}).get("by_department_seniority", {})
    sales_leader = (hc["sales_leaders"]
                    if hc["sales_leaders"] is not None else role_sum.get("sales_leader"))
    sales_ic = role_sum.get("sales_ic")

    return {
        "gtm_to_build_ratio": _safe_ratio(gtm, eng) if (sales or mkt) and eng else None,
        "technical_to_sales_ratio": _safe_ratio(eng, sales),
        "sales_to_marketing_ratio": _safe_ratio(sales, mkt),
        "sales_leader_to_ic_ratio": _safe_ratio(sales_leader, sales_ic),
        "_headcounts_used": hc,
    }


def compute_absence(website: dict | None, dns: dict | None) -> dict:
    """What a company that SHOULD have something doesn't. Often more predictive
    than presence. None where we couldn't determine."""
    web = website or {}
    d = dns or {}
    return {
        "missing_security_page": (not web["has_security_page"]
                                  if web.get("has_security_page") is not None else None),
        "missing_pricing_page": (not web["has_pricing_page"]
                                 if web.get("has_pricing_page") is not None else None),
        "missing_dmarc": (not d["dmarc_present"]
                          if d.get("dmarc_present") is not None else None),
        "weak_dmarc_policy": (d.get("dmarc_policy") in (None, "none", "unspecified")
                              if d.get("dmarc_present") is not None else None),
        "missing_spf": (not d["spf_present"]
                        if d.get("spf_present") is not None else None),
        "no_security_txt": (not d["security_txt_present"]
                            if d.get("security_txt_present") is not None else None),
    }


def compute_triggers(website: dict | None, funding: dict | None, current_year: int) -> dict:
    """Point-in-time 'why now' signals. Delta-based ones (hiring velocity,
    exec changes) require comparing against a prior capture — the raw snapshot
    plus _captured_at make that diff possible later."""
    web = website or {}
    last_blog = web.get("last_blog_date")
    copyright_year = web.get("copyright_year")

    dormant = None
    if last_blog:
        try:
            dormant = (current_year - int(last_blog)) >= 1
        except ValueError:
            dormant = None

    return {
        "hiring_for_new_function": web.get("hiring_for_new_function") or [],
        "open_roles_total": (web.get("roles_summary") or {}).get("open_roles_total"),
        "dormant_blog": dormant,
        "stale_copyright": (copyright_year is not None and copyright_year < current_year - 1),
        "recent_funding": _recent_funding(funding, current_year),
    }


def _recent_funding(funding: dict | None, current_year: int) -> bool | None:
    if not funding:
        return None
    # provider-shape-tolerant: look for any 4-digit year >= current_year-1 in the payload
    blob = str(funding)
    import re
    years = [int(y) for y in re.findall(r"20\d{2}", blob)]
    if not years:
        return None
    return max(years) >= current_year - 1


def derive(data: dict, current_year: int) -> dict:
    """Top-level: assemble the 'derived' sub-object from captured sources."""
    website = data.get("website")
    linkedin = data.get("linkedin")
    dns = data.get("dns")
    funding = data.get("funding")
    return {
        "ratios": compute_ratios(linkedin, website),
        "absence": compute_absence(website, dns),
        "triggers": compute_triggers(website, funding, current_year),
    }
