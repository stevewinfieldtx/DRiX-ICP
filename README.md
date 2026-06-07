# FitScore — ICP Scoring Engine (MVP scaffold)

SaaS that turns a vendor's solution materials into an Ideal Customer Profile (ICP)
rubric and scores prospects against it.

- **Light (Tier 1)** — LLM-only scoring.
- **Deep (Tier 2)** — deterministic scoring from Apollo enrichment, plus
  **compliant** speculative data capture (Section 8) for future pattern mining.

## Architecture

```
app/
  main.py              FastAPI entrypoint (+ /health)
  core/                settings + security (JWT, password + API-key hashing)
  db/                  SQLAlchemy base, session
  models/              users, projects, documents, leads, api_keys
  schemas/             Pydantic request/response models
  api/routes/          auth, projects, documents, rubric, leads,
                       api_keys, external (public API), billing (Stripe)
  services/
    text_extraction    PDF / DOCX / text -> plain text
    llm                OpenRouter client (rubric gen + Tier 1 scoring)
    rubric_generation  ICP rubric from corpus
    scoring            Tier 1 (LLM) + Tier 2 (deterministic) + colour mapping
    apollo             Apollo.io client (org enrich + departmental headcounts)
    enrichment         Tier 2 signal resolution from Apollo data
    speculative/
      site_scraper       first-party site (Firecrawl or httpx): roles, dates, pain language
      dns_signals        SPF / DMARC policy / MX provider / security.txt (public DNS)
      api_sources        firmographics+funding via Apollo, news via Serper
      derived            ratios + absence flags + 'why now' triggers (pure, tested)
      capture            assembles speculative_data (see SCHEMA.md / COMPLIANCE.md)
  services/
    analytics/         Section 9 pattern miner
      flatten          nested speculative_data -> typed features
      stats            two-proportion test, Cohen's d (dependency-free)
      patterns         cohort compare, ranked findings, suggestions, hidden gems
      narrate          optional LLM phrasing (real numbers only; deterministic fallback)
  worker/              ARQ queue + enrich_and_capture job
alembic/               migrations (0001_init creates the full schema)
Dockerfile, docker-compose.yml, railway.json, Procfile
```

## Section 8 — what changed and why

The brief asked for LinkedIn / Glassdoor / G2 scraping with rotating user-agents.
That is **not implemented** — it violates those sites' ToS, the rotating UA is an
evasion technique, and storing data on named individuals indefinitely creates
GDPR/CCPA exposure. Instead we keep the same goal and JSONB shape via:

1. **First-party site capture** (`services/speculative/site_scraper.py`): fetches
   only the company's *own* site, honors robots.txt, single honest User-Agent,
   rate-limited, page-capped, fault-tolerant.
2. **Licensed APIs** (`services/speculative/api_sources.py`): firmographics, departmental
   headcounts and funding via **Apollo**; news via **Serper**. Counts only — no individuals
   stored. Each gated on its key.

See `app/services/speculative/COMPLIANCE.md` for the full rationale.

## Signals captured (Section 8)

Beyond raw firmographics, the capture pipeline records the non-obvious, **interaction**
and **absence** signals that single fields miss — and stamps every snapshot with
`_captured_at` so later runs can diff for velocity/change triggers:

- **Email/domain hygiene (DNS):** SPF, DMARC presence + policy strength, MX provider
  (M365 / Google / Proofpoint / etc.), `security.txt`. For an email-security ICP this
  is close to a direct read on the pain — all public DNS, zero PII.
- **Org structure & ratios:** GTM-to-build, technical-to-sales, sales-to-marketing,
  and sales leader-to-IC ratios; open roles classified by department **and** seniority.
- **Absence (negative space):** missing security/pricing page, missing/weak DMARC,
  no `security.txt` — often more predictive than presence.
- **"Why now" triggers:** hiring into a brand-new function (possible first hire),
  dormant blog, stale copyright, recent funding.
- **Self-identified posture:** compliance/security language on the company's own site;
  partner/reseller program flag (reverse-ICP for channel discovery).

See `app/services/speculative/SCHEMA.md` for the full JSONB shape.

## Section 9 — pattern mining (dynamic ICP discovery)

Once enough leads are scored, the miner compares a **top** cohort
(dark_green + green) against a **bottom** cohort (yellow + unqualified) across
every flattened `speculative_data` feature and returns:

- **findings** — each discriminating signal with *real* statistics
  (prevalence in each cohort, percentage-point gap, lift, p-value, or Cohen's d
  for numerics). Evidence thresholds (min cohort size, support, significance)
  prevent crowing about noise.
- **suggested_signals** — the strongest winner-associated traits, packaged as
  proposed rubric signals with a suggested weight and the supporting evidence.
- **hidden_gems** — low-scoring leads that share the winning traits (worth a
  second look).

```bash
# run analysis
POST /api/v1/projects/{id}/analytics/analyze
# accept suggestions -> appends them to the project rubric
POST /api/v1/projects/{id}/analytics/suggestions/apply   {"keys": ["dns_dmarc_policy_none"]}
```

All figures are computed deterministically in `analytics/stats.py`; the optional
LLM layer only rephrases findings that already contain the numbers — it never
invents them.

## Run locally

```bash
cp .env.example .env          # fill in keys (all optional; app runs without them)
docker compose up --build     # api on :8000, worker, postgres, redis
# OR, without Docker:
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
arq app.worker.main.WorkerSettings   # in a second terminal
```

Interactive API docs: http://localhost:8000/docs

## Typical flow

1. `POST /api/v1/auth/register` then `/auth/login` → bearer token.
2. `POST /api/v1/projects` (tier `light` or `deep`).
3. `POST /api/v1/projects/{id}/documents` (upload solution material).
4. `POST /api/v1/projects/{id}/rubric/generate`.
5. `POST /api/v1/projects/{id}/leads` → Tier 1 score returns inline; for `deep`
   projects, Tier 2 enrichment + Section 8 capture run in the worker.
6. `GET /api/v1/projects/{id}/leads/{lead_id}/speculative` → spec-data modal.
7. `POST /api/v1/api-keys` → external API key; score via `POST /api/v1/external/...`.

## Deploy to Railway

1. Push this repo to GitHub and create a Railway project from it.
2. Add **PostgreSQL** and **Redis** plugins (they inject `DATABASE_URL` /
   `REDIS_URL`). Ensure `DATABASE_URL` uses the `postgresql+psycopg://` scheme.
3. Set env vars from `.env.example` (`SECRET_KEY`, `OPENROUTER_API_KEY`, etc.).
4. Web service uses the Dockerfile start command (runs `alembic upgrade head`).
5. Add a second service from the same repo with start command
   `arq app.worker.main.WorkerSettings` for background jobs.

## Status / next steps

Scaffold = runnable skeleton. Stubbed for you to flesh out: real document storage
(S3/Railway volume), richer `resolve_signals` mapping, Stripe checkout + tier
gating in the webhook, the dashboard frontend (Section 10), and the pattern-mining
analytics endpoint (Section 9).
