# Inua360 — Milestone 1 (Core MVP)

Inua360 is a financial passport and funding-readiness platform for Kenyan SMEs.
Merchants build a business profile, upload an M-Pesa statement, see a transparent
Funding Readiness score, and get a ranked list of funding opportunities with an
explanation of what they meet and what is missing.

**Positioning:** Inua360 is the layer between the SME and capital providers. We are
not a lender and not a credit-scoring API. The merchant owns their data. The
readiness score is a transparent, rule-based rubric — **not a credit score and not
a guarantee of funding**. Financial insights are descriptive, not advice.

## What is implemented

- Django 5.2 + DRF API at `/api/v1`, JWT auth with an httpOnly rotating refresh cookie
- Onboarding: business profile, self-reported compliance, M-Pesa statement, documents
- Memory-only encrypted M-Pesa PDF parsing (pikepdf + pdfplumber), parser/normalizer
  separation, parse preview → confirm, dedupe, monthly aggregates
- Transparent readiness rubric (pure function + YAML config), history, improvement gaps
- Curated opportunity catalog (EXAMPLE placeholders), pure matching/checklist engine
- Document uploads to a private S3-compatible bucket (MinIO in dev) with owner checks
- Postgres Row-Level Security backstop **and** Django-level owner scoping
- Delete-my-data, audit log, request ids, redacted structured logs
- Next.js (App Router) + TypeScript + Tailwind frontend
- pytest, Vitest/RTL, and one Playwright happy-path spec; GitHub Actions CI

## Not in this milestone

No LLM/agents, scrapers, cron, billing, notifications, direct application submission,
bank/Vooma ingestion, OCR, ML models, live Daraja, or live GavaConnect calls.

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
# API:      http://localhost:8000/api/v1/
# If port 5432 is taken, set POSTGRES_PORT=55432 in .env before starting.
# If port 3000 is taken, set FRONTEND_PORT and FRONTEND_ORIGIN in .env.
# Swagger:  http://localhost:8000/api/v1/schema/swagger-ui/
# Frontend: http://localhost:3000
# MinIO:    http://localhost:9001 (minioadmin / minioadmin)
```

The backend container runs migrations as `inua_migrator`, seeds the EXAMPLE
catalog, then serves requests as `inua_app`. The app role is not a superuser, has
no `BYPASSRLS`, and does not own tables.

Create a staff user (never through the API):

```bash
docker compose exec backend python manage.py createsuperuser
# Django admin: http://localhost:8000/admin/  (opportunities only)
```

## Local (without Docker)

Requirements: Python 3.11+, Node 20+, a real PostgreSQL 15+ server.

```bash
# 1. Roles and database
psql -d postgres -f backend/scripts/bootstrap_roles.sql
createdb -O inua_migrator inua360

# 2. Python
python3 -m venv .venv
.venv/bin/pip install -e 'backend[dev]'

# 3. Migrate as the owner role
cd backend
DB_USER=inua_migrator ../.venv/bin/python manage.py migrate --database=migrator
DB_USER=inua_app ../.venv/bin/python manage.py seed_opportunities
DB_USER=inua_app ../.venv/bin/python manage.py runserver
```

For local file storage without MinIO, set `STORAGE_BACKEND=filesystem`. Documents
are then served through the ownership-checked Django stream endpoint.

## Tests and checks

```bash
make test          # backend pytest (real Postgres, RLS enabled)
make lint          # ruff
make typecheck     # mypy strict on project apps
make check-deploy  # python manage.py check --deploy with prod settings
make frontend-test # eslint, tsc, vitest
make frontend-e2e  # Playwright happy path (mocked API; no backend needed)
# first time only: cd frontend && npx playwright install chromium
```

The pytest harness creates a test database as `inua_migrator`, runs all migrations,
then connects the application as `inua_app`. RLS is therefore active even for the
test suite. See `backend/tests/conftest.py`.

## Structure

```
backend/
  config/            settings base/dev/test/prod, urls, wsgi/asgi
  apps/
    accounts/        custom UUID User, JWT cookie auth, delete-my-data
    businesses/      Business profile + onboarding progress
    compliance/      ComplianceVerifier protocol + self-reported implementation
    ingestion/       parser vs normalizer, synthetic generator, pending/confirm
    financials/      transactions, monthly aggregates, metrics, loans, funding need
    documents/       private storage, content sniffing, signed URLs
    readiness/       pure scoring engine + YAML rubric + assessments
    opportunities/   catalog, pure matching, checklists, Django admin
    audit/           append-only audit events
    common/          RLS plumbing, scoped managers, errors, logging
  tests/             unit/API/parser/isolation tests, synthetic fixtures
frontend/            Next.js App Router app
docs/                DECISIONS, SCORING, DATA_MODEL
```

## Privacy and security notes

- Statement PDFs and passwords are never written to disk, logs, database, or error
  reports. Django upload handlers are configured memory-only, with limits just above
  the 10 MB cap. Only normalized transaction rows and statement metadata are kept.
- Uploaded documents live in a private bucket. Every access is ownership-checked;
  production returns short-lived signed URLs (≤ 5 minutes).
- `DEBUG=False` outside local dev. Production settings enable secure cookies, HSTS,
  SSL redirect, and set `ALLOWED_HOSTS` from the environment.
- No third-party analytics receive financial data. Sentry is optional, PII-disabled,
  and scrubs request bodies/cookies.
- Merchant financial models are deliberately not registered in Django admin.

## TODO(owner) — required before launch

1. **Real M-Pesa statements:** provide 3–5 redacted personal and till/paybill PDFs
   to validate the parser. The current tests use synthetic statements only.
2. **Real opportunities:** replace all `EXAMPLE —` seed entries in
   `backend/apps/opportunities/seed_data.py` with verified products and terms.
3. **Infrastructure credentials:** Supabase Postgres connection strings, Supabase
   Storage S3 keys, production domain for CORS/cookies/CSRF.
4. **Scoring weights:** confirm the rubric in `docs/SCORING.md` with a lending/credit
   reviewer.
5. **Legal copy:** confirm consent text/version and the privacy notice with counsel.

## Docs

- [docs/DECISIONS.md](docs/DECISIONS.md) — every assumption made
- [docs/SCORING.md](docs/SCORING.md) — human-readable scoring rubric
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — model/table overview and isolation map
