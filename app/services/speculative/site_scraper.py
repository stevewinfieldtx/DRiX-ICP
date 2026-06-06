"""Polite, first-party website capture for Section 8.1 (extended).

Only fetches the target company's OWN site. Honors robots.txt, uses one honest
identifiable User-Agent (no rotation), rate-limits, caps pages per domain.
Every field is fault-tolerant: missing -> null. Nothing here evades bot defenses.

Captures (point-in-time, no personal data):
  - open_roles classified by department AND seniority (leader vs IC)
  - roles_summary: counts by dept, by seniority, by dept+seniority
  - hiring_for_new_function flags (department hiring with little prior presence)
  - last_blog_date / last_press_date  (dormancy signal)
  - pain_language: self-identified terms on the company's own site
  - pricing_model, partner_page, social_links, tech_mentions, copyright_year,
    leadership_count, team_mentions
"""
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from app.core.config import settings
from app.services.speculative import robots

_CANDIDATE_PATHS = [
    "", "about", "about-us", "company", "team", "careers", "jobs",
    "blog", "resources", "pricing", "customers", "case-studies",
    "partners", "contact", "news", "press", "security", "trust", "compliance",
]
_DEPT_KEYWORDS = {
    "sales": ["sales", "account executive", " ae ", "sdr", "bdr", "business development",
              "revenue", "account manager"],
    "marketing": ["marketing", "growth", "content", "demand gen", "brand", "seo"],
    "engineering": ["engineer", "developer", "software", "devops", "sre", "data scientist",
                    "architect", "qa", "platform"],
    "support": ["support", "customer success", "customer service", "onboarding"],
}
# seniority: leaders set budget / are buying committee
_LEADER_TOKENS = ["chief", "ceo", "cto", "cfo", "coo", "cmo", "ciso", "vp ", "vice president",
                  "head of", "director", "manager", "principal", "lead "]
_IC_TOKENS = ["representative", "associate", "executive", "specialist", "coordinator",
              "junior", "analyst", "sdr", "bdr", " ae", "engineer i", "engineer ii"]
_SOCIAL = {
    "twitter": r"(twitter\.com|x\.com)/",
    "linkedin": r"linkedin\.com/",
    "facebook": r"facebook\.com/",
    "youtube": r"youtube\.com/",
}
# self-identified pain / posture language (tune per ICP)
_PAIN_LEXICON = [
    "compliance", "hipaa", "soc 2", "soc2", "iso 27001", "gdpr", "pci",
    "audit", "encryption", "secure", "confidential", "data loss", "phishing",
    "ransomware", "email security", "dlp", "regulated",
]
_DATE_RE = re.compile(
    r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+(20\d{2})",
    re.I,
)


async def _fetch(url: str) -> str | None:
    if not await robots.allowed(url):
        return None
    await robots.polite_delay(url)
    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True,
            headers={"User-Agent": settings.scraper_user_agent},
        ) as client:
            resp = await client.get(url)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:  # noqa: BLE001
        return None
    return None


def _norm(domain: str) -> str:
    if not domain.startswith("http"):
        domain = "https://" + domain
    return domain.rstrip("/")


def classify_role(title: str) -> tuple[str | None, str]:
    """Return (department, seniority) for a role title. seniority in {leader, ic}."""
    low = f" {title.lower()} "
    dept = None
    for d, kws in _DEPT_KEYWORDS.items():
        if any(k in low for k in kws):
            dept = d
            break
    seniority = "leader" if any(t in low for t in _LEADER_TOKENS) else "ic"
    # "account executive" / "sales executive" are ICs despite 'executive'
    if "executive" in low and ("account" in low or "sales" in low):
        seniority = "ic"
    return dept, seniority


async def capture_site(domain: str | None) -> dict:
    out: dict = {
        "has_case_studies": None, "case_study_count": None,
        "has_blog": None, "blog_article_count": None, "last_blog_date": None,
        "has_press": None, "last_press_date": None,
        "team_mentions": {}, "open_roles": [], "roles_summary": {},
        "hiring_for_new_function": [],
        "leadership_count": None, "partner_page": None,
        "has_security_page": None, "has_pricing_page": None, "pricing_model": None,
        "pain_language": [], "social_links": {}, "tech_mentions": [],
        "copyright_year": None, "pages_fetched": [],
        "_captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if not domain:
        return out

    base = _norm(domain)
    fetched_text: list[str] = []
    pages = 0

    for path in _CANDIDATE_PATHS:
        if pages >= settings.scraper_max_pages_per_domain:
            break
        url = urljoin(base + "/", path)
        html = await _fetch(url)
        if not html:
            continue
        pages += 1
        out["pages_fetched"].append(path or "/")
        tree = HTMLParser(html)
        text = tree.text(separator=" ", strip=True).lower()
        fetched_text.append(text)

        if path in {"case-studies", "customers"}:
            out["has_case_studies"] = True
        if path in {"blog", "resources"}:
            out["has_blog"] = True
            out["blog_article_count"] = len(tree.css("article")) or None
            out["last_blog_date"] = _latest_date(text)
        if path in {"news", "press"}:
            out["has_press"] = True
            out["last_press_date"] = _latest_date(text)
        if path in {"careers", "jobs"}:
            out["open_roles"] = _extract_roles(tree)
        if path == "pricing":
            out["has_pricing_page"] = True
            out["pricing_model"] = (
                "contact_sales" if "contact sales" in text or "contact us" in text
                else "self_serve"
            )
        if path in {"security", "trust", "compliance"}:
            out["has_security_page"] = True
        if path == "partners":
            out["partner_page"] = True

        for name, pat in _SOCIAL.items():
            if name in out["social_links"]:
                continue
            for a in tree.css("a"):
                if re.search(pat, a.attributes.get("href", "") or ""):
                    out["social_links"][name] = a.attributes.get("href")
                    break

    blob = " ".join(fetched_text)
    out["team_mentions"] = _dept_counts(blob)
    out["leadership_count"] = _count_leaders(blob)
    out["copyright_year"] = _copyright_year(blob)
    out["tech_mentions"] = _tech_mentions(blob)
    out["pain_language"] = sorted({p for p in _PAIN_LEXICON if p in blob})
    out["roles_summary"] = _summarize_roles(out["open_roles"])
    out["hiring_for_new_function"] = _new_function_flags(out["roles_summary"], out["team_mentions"])

    # default false (not null) when we successfully fetched pages but section absent
    if pages:
        for k in ("has_case_studies", "has_blog", "has_security_page",
                  "has_pricing_page", "partner_page", "has_press"):
            if out[k] is None:
                out[k] = False
    return out


def _extract_roles(tree: HTMLParser) -> list[dict]:
    roles, seen = [], set()
    for node in tree.css("a, li, h3, h2"):
        title = (node.text() or "").strip()
        if not (3 < len(title) < 80):
            continue
        dept, seniority = classify_role(title)
        if dept and title not in seen:
            seen.add(title)
            roles.append({"title": title, "department": dept, "seniority": seniority})
    return roles[:60]


def _summarize_roles(roles: list[dict]) -> dict:
    by_dept: dict[str, int] = {}
    by_seniority: dict[str, int] = {"leader": 0, "ic": 0}
    by_dept_sen: dict[str, int] = {}
    for r in roles:
        d, s = r["department"], r["seniority"]
        by_dept[d] = by_dept.get(d, 0) + 1
        by_seniority[s] += 1
        by_dept_sen[f"{d}_{s}"] = by_dept_sen.get(f"{d}_{s}", 0) + 1
    return {
        "open_roles_total": len(roles),
        "by_department": by_dept,
        "by_seniority": by_seniority,
        "by_department_seniority": by_dept_sen,
    }


def _new_function_flags(summary: dict, team_mentions: dict) -> list[str]:
    """Hiring into a department with little/no existing presence => possible 'first hire'."""
    flags = []
    for dept, n in (summary.get("by_department") or {}).items():
        existing = team_mentions.get(f"{dept}_mentions")
        if n and not existing:
            flags.append(f"possible_first_{dept}_hire")
    return flags


def _latest_date(text: str) -> str | None:
    years = []
    for m in _DATE_RE.finditer(text):
        y = m.group(1) or m.group(5)
        if y:
            years.append(int(y))
    return str(max(years)) if years else None


def _dept_counts(text: str) -> dict:
    return {f"{d}_mentions": (sum(text.count(k) for k in kws) or None)
            for d, kws in _DEPT_KEYWORDS.items()}


def _count_leaders(text: str) -> int | None:
    total = sum(text.count(t) for t in ["ceo", "cto", "cfo", "coo", "cmo", "ciso",
                                        "vp ", "vice president", "chief"])
    return total or None


def _copyright_year(text: str) -> int | None:
    m = re.findall(r"(?:©|copyright)\s*(20\d{2})", text)
    return int(m[0]) if m else None


def _tech_mentions(text: str) -> list[str]:
    known = ["salesforce", "hubspot", "stripe", "aws", "azure", "snowflake", "segment",
             "marketo", "zendesk", "intercom", "shopify", "microsoft 365", "office 365",
             "google workspace", "proofpoint", "mimecast"]
    return [t for t in known if t in text]
