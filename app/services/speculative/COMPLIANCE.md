# Section 8 — Compliant Data Capture (design note)

The original brief (v1.1) called for scraping LinkedIn, Glassdoor, G2/Capterra,
and Crunchbase using rotating user-agents. That approach is **not implemented**
because it would:

- Violate those sites' Terms of Service (LinkedIn, Glassdoor, G2 explicitly
  prohibit scraping; LinkedIn actively pursues scrapers).
- Use rotating user-agents specifically to evade anti-bot controls — i.e.
  circumventing technical access controls.
- Create GDPR/CCPA exposure by harvesting and indefinitely storing data about
  named individuals.

## What we do instead (same payoff, defensible foundation)

1. **First-party website capture** (`site_scraper.py`): fetch only the target
   company's *own* public website. We honor `robots.txt`, use a single honest,
   identifiable User-Agent, rate-limit, cap pages per domain, and cache results.
   No evasion. This yields most of Section 8.1 (case studies, blog, careers,
   pricing, partner program, social links, tech mentions, etc.).

2. **Licensed/official APIs** (`api_sources.py`): everything that the brief
   wanted from LinkedIn / news / funding / reviews is sourced from official or
   licensed APIs (e.g. a People-Data provider, a News API, Crunchbase API).
   Each adapter is gated behind its own API key and returns `{}` when not
   configured, so the system runs without them.

The resulting `speculative_data` JSONB keeps the exact nested shape from the
brief, so future pattern-mining (Section 9) is unaffected.
