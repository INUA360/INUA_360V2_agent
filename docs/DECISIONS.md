# Decisions log — Inua360 Milestone 1

Every assumption or conservative choice is recorded here. Dates are build dates.

## Architecture and stack

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 1 | Django 5.2 LTS, DRF 3.17, Python 3.11+ (Docker uses 3.12; local used 3.13) | Fixed by brief; 5.2 is the LTS line. |
| 2 | One Django project, focused apps exactly as specified | Keeps ingestion/scoring/matching boundaries explicit. |
| 3 | PostgreSQL only; tests require a real Postgres | RLS is not available on SQLite. |
| 4 | Two DB roles: `inua_migrator` owns tables/runs migrations; `inua_app` serves requests | The app role is `NOSUPERUSER NOBYPASSRLS`, is not the table owner, and only has DML grants. |
| 5 | Migrations run through a separate `migrator` database alias (`manage.py migrate --database=migrator`) | Lets the runtime stay on `inua_app` while schema work stays with the owner. |
| 6 | `ATOMIC_REQUESTS=True` on the default DB connection | The RLS tenant is set with `set_config(..., true)` (transaction-local), so it must run inside the request transaction. |
| 7 | `DISABLE_SERVER_SIDE_CURSORS=True` | Required when using transaction-mode poolers and harmless on direct connections. |
| 8 | Tenant setting is always transaction-local `set_config('app.current_user_id', <uuid>, true)` | Safe with connection pooling; never leaks between requests. |
| 9 | `RLSContextMixin` is the single RLS hook, run in `initial()` after DRF authentication | DRF auth is lazy; middleware cannot see the JWT user. Unauthenticated requests never set a tenant. |
| 10 | RLS policies use a SQL helper `app_current_user_id()` that returns NULL for missing/malformed values | Prevents cast errors and makes policies fail closed. |
| 11 | Auth tables (`accounts_user`, tokens) are not RLS-protected | Login/registration must resolve identity before a tenant is known. No financial data lives there. Documented exception. |
| 12 | `Opportunity` catalog is global (not tenant data); `OpportunityMatch` is tenant data and is RLS-protected | The catalog is curated staff data. Matches reveal merchant-specific eligibility. |
| 13 | RLS is enabled **and forced**; isolation tests use the app role | FORCE means even the table owner is subject, so the test harness is meaningful. |
| 14 | Test harness creates the test DB and runs migrations as `inua_migrator`, then points the default connection at `inua_app` | The entire pytest suite runs against the app role with RLS active. |
| 15 | Detail views use owner-scoped querysets and return 404, never 403 | Avoids leaking whether another tenant's resource exists. |

## Authentication

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 16 | Access token (~15 min) is returned in the JSON body; refresh token (~7 days) is an httpOnly, Secure (in prod), SameSite=Lax cookie scoped to `/api/v1/auth` | Keeps the long-lived credential out of JavaScript while letting the SPA keep the short-lived access token in memory/sessionStorage. |
| 17 | Refresh tokens rotate; the old token is blacklisted (`ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION`) | Limits replay. SimpleJWT blacklist app is installed. |
| 18 | `refresh` and `logout` are `csrf_protect`ed; `GET /auth/csrf` issues a CSRF cookie/token | Cookie-authenticated endpoints need CSRF protection. Cookies are SameSite=Lax and CORS is allow-listed. |
| 19 | Staff/superusers only via `createsuperuser` | No API/UI path can create staff. `role` is read-only in serializers. |
| 20 | Email verification/reset links use hashed, single-use tokens with expiry | Raw tokens are never stored. Dev uses console/locmem email. |
| 21 | Consent version and timestamp are captured at registration; consent is mandatory | Required by the brief. The legal wording is a TODO(owner). |
| 22 | Onboarding progress is derived from records and exposed as a percentage (25/50/75/100) | Cannot be inflated by client-side input; resumable. |

## Business and compliance

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 23 | One business per merchant in M1 (`OneToOneField`) | Simplifies onboarding and matching; changing to FK later is additive. |
| 24 | Kenya's 47 counties are a model enum; sector/structure/employee band use TextChoices | Matches the brief; stable codes for matching. |
| 25 | Compliance facts store a per-field `verification_status` (`self_reported` / `verified`) | Self-reported earns 70% of each compliance field's points; verified earns 100%. |
| 26 | County permit computed status: `valid`, `expiring_soon` (<60 days), `expired`, `none` | Threshold is a brief requirement; computed, never stored stale. |
| 27 | TCC effective status is recomputed from expiry (a "valid" TCC past expiry becomes expired) | Prevents stale self-reported TCCs from scoring. |
| 28 | GavaConnect verifier raises `NotImplementedError` and documents the three future endpoints | Interface ships now; no live KRA calls in M1. |
| 29 | KRA PIN format `^[AP]\d{9}[A-Z]$`, uppercased on save | Brief requirement; blank allowed while onboarding. |

## Statement ingestion and privacy

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 30 | Uploads use only `MemoryFileUploadHandler`; upload memory limits are 12 MB (10 MB cap + 2 MB headroom) | Prevents Django spooling the encrypted PDF to disk. |
| 31 | PDF decryption/parsing is entirely in memory (`BytesIO`), no temp files; the PDF is never stored | Core privacy promise. Tests assert the temp directory is unchanged, including >2.5 MB files. |
| 32 | Parser → normalizer → persistence; parsers return `RawTransactionRow`, know nothing about Django/HTTP | A future bank/Vooma parser is additive. |
| 33 | Parse is two-step: preview creates a `PendingStatement` with normalized rows only (30-minute TTL), then confirm persists | Merchant reviews summary first. Expired previews are purged on each parse and treated as invalid on confirm. |
| 34 | Password is accepted only in the parse request, decorated with `sensitive_post_parameters("password")`; never logged, stored, or included in errors | Wrong-password errors are generic. The logging filter redacts sensitive keys. |
| 35 | Statements dedupe on `(business, source, source_ref)`; overlapping uploads skip existing receipts | Duplicate uploads do not double-count revenue. |
| 36 | Statement deletion removes its transactions and recomputes all monthly aggregates | Keeps financial metrics consistent. |
| 37 | Categorization keywords live in `apps/financials/config/categories.yaml` | No magic strings scattered in code. First match wins; unknown → `uncategorized`. |
| 38 | Parsing is synchronous in M1, but isolated in service functions | Can move behind a worker without changing the API contract. |
| 39 | Synthetic statement generator produces two encrypted layouts; all tests use synthetic data | No real PII in the repo. TODO(owner): real redacted statements are needed before launch. |
| 40 | Revenue approximation: use customer-payment inflows when they are ≥30% of money-in; otherwise treat all inflows as revenue and surface a caveat | Classification is keyword-based. The assumption is explicit in the API/readiness caveat. |
| 41 | Self-reported average monthly revenue/expenses live on `FundingNeed` (optional) | Brief asks for fallback manual figures; avoids another model. They only affect scoring when no statement exists. |
| 42 | Monthly statements are accepted as valid; a failed/zero-row parse is rejected before a `PendingStatement` exists | Merchant must see something actionable. |

## Scoring and matching

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 43 | Scoring is a pure function over a plain snapshot; YAML owns weights/thresholds/labels | Deterministic, unit-testable, auditable. No ORM inside. |
| 44 | `readiness/services.py` builds the snapshot and persists a `ReadinessAssessment` on every explicit recompute | History is preserved. No signals. |
| 45 | Recompute is triggered by explicit service calls in profile, compliance, statement confirm/delete, loan, funding-need, and document views | Testable and traceable. Missing calls fail safe (score simply stays older). |
| 46 | Matches are persisted on recompute (`OpportunityMatch`), preserving merchant state (`saved/applied/dismissed`) | Lists load fast; state survives score changes. Hard-excluded matches are deleted. |
| 47 | Fit levels: strong = 0 soft misses; possible = 1–2 misses and score gap ≤15; stretch = more misses or score gap >15 | Directly follows the brief. |
| 48 | Staleness: opportunities verified >60 days ago show a stale badge; >120 days are excluded from merchant results | Brief requirement; constants are service-level (could move to config later). |
| 49 | Example opportunities are seeded via data migration and an idempotent management command | Merchant-facing catalog is never empty in dev/CI. Every entry is labelled `EXAMPLE —` with TODO(owner). |
| 50 | Application checklist derives from required documents, compliance flags, score, and operating months | Matches brief; each missing item links to a fix path. |

## Documents and storage

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 51 | Private S3-compatible storage via `django-storages`; MinIO in dev; no Supabase client SDK anywhere | Supabase is only managed Postgres + S3 storage. |
| 52 | Storage key `{user_id}/{business_id}/{doc_type}/{uuid}-{sanitized_filename}` | Stable tenancy prefix and collision-free names. |
| 53 | MIME is sniffed from magic bytes (`%PDF`, JPEG, PNG), not extension; max 10 MB | Prevents disguised file uploads. |
| 54 | Production download URLs are presigned and expire in 300 seconds; local filesystem dev streams through an ownership-checked endpoint | No client credentials in the browser; no public bucket. |
| 55 | Bank statements can be uploaded as documents but are not parsed in M1 | Explicitly out of scope. |

## Frontend and observability

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 56 | A small typed dictionary in `frontend/lib/i18n.ts` is the i18n layer (English only) | Satisfies translatable-copy requirement without adding a routing-heavy dependency; Swahili can be added by adding a locale key. |
| 57 | Access token is stored in `sessionStorage` plus module memory; refresh uses the httpOnly cookie | Tab-scoped, short-lived; long-lived credential stays inaccessible to JS. |
| 58 | JSON logs include request id; a filter redacts password/token/statement keys and bearer tokens | Statement content and secrets cannot reach logs. |
| 59 | Sentry is optional, `send_default_pii=False`, and scrubs request bodies/cookies | Sentry-ready without violating the privacy rules. |
| 60 | No analytics SDKs of any kind | No third-party receives financial data. |
| 61 | The UI shows the exact disclaimer: "This score is a transparent rubric based on common lending criteria. It is not a credit score and does not guarantee funding." | Positioning rule. |

## Testing and operations

| # | Decision | Why / consequence |
|---|----------|-------------------|
| 62 | pytest overrides `django_db_setup` to create the DB as migrator, migrate, then run the suite as `inua_app` | RLS is exercised throughout, not just in isolation tests. |
| 63 | Raw-SQL isolation tests use a committed transaction (`transaction=True`) and switch the tenant setting between users | Proves DB-level fail-closed behavior independent of Django scoping. |
| 64 | A query-scoping test scans merchant view modules for unscoped `.objects.all()` / `.objects.get(` | Lint-style guard for layer 2. |
| 65 | CI runs ruff, strict mypy, `check --deploy`, `makemigrations --check`, pytest against Postgres, then frontend lint/typecheck/tests | Matches the required pipeline. |
| 66 | Playwright covers one happy path only | Kept deliberately small for M1. |

## Known limitations / TODOs

- Real M-Pesa layouts are unvalidated; synthetic fixtures prove the pipeline, not
  Safaricom's full variability. **TODO(owner): 3–5 redacted real statements.**
- Real opportunity data is required. **TODO(owner): replace EXAMPLE seeds.**
- Scoring weights have not been reviewed by a credit/lending expert.
  **TODO(owner): confirm weights.**
- Legal consent/privacy wording is placeholder. **TODO(owner): counsel review.**
- Real Supabase Postgres/Storage credentials and production domain are required.
