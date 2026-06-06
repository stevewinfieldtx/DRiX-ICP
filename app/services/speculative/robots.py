"""robots.txt fetching/caching and a simple per-domain rate limiter."""
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

from app.core.config import settings

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_hit: dict[str, float] = {}


def _domain(url: str) -> str:
    return urlparse(url).netloc


async def allowed(url: str) -> bool:
    if not settings.scraper_respect_robots:
        return True
    domain = _domain(url)
    rp = _robots_cache.get(domain)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    robots_url, headers={"User-Agent": settings.scraper_user_agent}
                )
            rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except Exception:  # noqa: BLE001
            rp.parse([])  # on error, default to permissive for own-site fetch
        _robots_cache[domain] = rp
    return rp.can_fetch(settings.scraper_user_agent, url)


async def polite_delay(url: str) -> None:
    domain = _domain(url)
    delay = settings.scraper_request_delay_seconds
    elapsed = time.monotonic() - _last_hit.get(domain, 0.0)
    if elapsed < delay:
        import asyncio

        await asyncio.sleep(delay - elapsed)
    _last_hit[domain] = time.monotonic()
