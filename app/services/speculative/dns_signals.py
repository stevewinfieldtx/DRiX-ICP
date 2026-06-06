"""DNS / email-hygiene capture (Section 8 'aha' module).

For an email-security/compliance vendor this is close to a direct read on the
pain the product solves. All data here is PUBLIC DNS + a public well-known file:
no scraping of third-party sites, no personal data, no ToS issues.

Captured:
  - spf_present / spf_record
  - dmarc_present / dmarc_policy (none|quarantine|reject) / dmarc_record
  - mx_provider (google|microsoft|proofpoint|mimecast|self_hosted|other) + raw hosts
  - security_txt_present

Every field is fault-tolerant: on any lookup failure it returns null.
"""
import re
from urllib.parse import urlparse

import httpx

from app.core.config import settings

try:
    import dns.resolver  # dnspython
    _HAS_DNS = True
except Exception:  # noqa: BLE001
    _HAS_DNS = False

_MX_PROVIDERS = {
    "google": ["google.com", "googlemail.com"],
    "microsoft": ["outlook.com", "protection.outlook.com", "microsoft.com"],
    "proofpoint": ["pphosted.com", "proofpoint.com"],
    "mimecast": ["mimecast.com"],
    "barracuda": ["barracudanetworks.com", "cudamail.com"],
    "zoho": ["zoho.com", "zoho.eu"],
}


def _bare_domain(domain: str) -> str:
    netloc = urlparse(domain if domain.startswith("http") else "//" + domain).netloc
    return (netloc or domain).split(":")[0].lstrip("www.")


def _txt(name: str) -> list[str]:
    if not _HAS_DNS:
        return []
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=5)
        return ["".join(s.decode() if isinstance(s, bytes) else s for s in r.strings)
                for r in answers]
    except Exception:  # noqa: BLE001
        return []


def _mx_hosts(name: str) -> list[str]:
    if not _HAS_DNS:
        return []
    try:
        answers = dns.resolver.resolve(name, "MX", lifetime=5)
        return [str(r.exchange).rstrip(".").lower() for r in answers]
    except Exception:  # noqa: BLE001
        return []


def classify_mx(hosts: list[str]) -> str | None:
    if not hosts:
        return None
    joined = " ".join(hosts)
    for provider, needles in _MX_PROVIDERS.items():
        if any(n in joined for n in needles):
            return provider
    return "self_hosted_or_other"


def parse_dmarc_policy(records: list[str]) -> str | None:
    for rec in records:
        if "v=dmarc1" in rec.lower():
            m = re.search(r"\bp\s*=\s*(none|quarantine|reject)", rec, re.I)
            return m.group(1).lower() if m else "unspecified"
    return None


async def _security_txt(domain: str) -> bool | None:
    base = domain if domain.startswith("http") else "https://" + domain
    base = base.rstrip("/")
    for path in ("/.well-known/security.txt", "/security.txt"):
        try:
            async with httpx.AsyncClient(
                timeout=10, follow_redirects=True,
                headers={"User-Agent": settings.scraper_user_agent},
            ) as client:
                resp = await client.get(base + path)
            if resp.status_code == 200 and "contact" in resp.text.lower():
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def capture_dns(domain: str | None) -> dict:
    out: dict = {
        "spf_present": None, "spf_record": None,
        "dmarc_present": None, "dmarc_policy": None, "dmarc_record": None,
        "mx_provider": None, "mx_hosts": None,
        "security_txt_present": None,
    }
    if not domain:
        return out
    bare = _bare_domain(domain)

    root_txt = _txt(bare)
    spf = next((r for r in root_txt if r.lower().startswith("v=spf1")), None)
    out["spf_present"] = bool(spf)
    out["spf_record"] = spf

    dmarc_txt = _txt(f"_dmarc.{bare}")
    policy = parse_dmarc_policy(dmarc_txt)
    out["dmarc_present"] = policy is not None
    out["dmarc_policy"] = policy
    out["dmarc_record"] = dmarc_txt[0] if dmarc_txt else None

    hosts = _mx_hosts(bare)
    out["mx_hosts"] = hosts or None
    out["mx_provider"] = classify_mx(hosts)

    out["security_txt_present"] = await _security_txt(domain)
    return out
