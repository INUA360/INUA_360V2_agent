# Engineering conventions — Inua360

## Non-negotiables

- Inua360 is not a lender/credit-scoring API. Never describe the readiness score as
  a credit score, prediction, or guarantee.
- Financial copy is descriptive, never advice ("you should take a loan" is banned).
- Never store or log statement PDFs, passwords, National ID numbers, or decrypted
  statement bytes. Uploads and parsing are memory-only.
- Merchant owns their data. No third-party sharing in Milestone 1.
- Merchant financial models are never registered in Django admin.
- Never query merchant data with an unscoped `.objects.all()` / `.objects.get(pk=...)`;
  use `Model.objects.for_user(user)` and object permissions. RLS is the backstop,
  not a replacement for Django scoping.
- No LLM/agent calls, scrapers, schedulers, billing, notifications, or live Daraja /
  GavaConnect calls in Milestone 1.

## Backend

- Django 5.2 + DRF, Python 3.11+, PostgreSQL only (no SQLite).
- UUID PKs, `created_at`, `updated_at` on every model.
- API routes under `/api/v1`, no trailing slashes (the frontend always uses the
  exact path).
- Every request/response has a serializer; errors use the envelope in
  `apps/common/exceptions.py`.
- All weights/thresholds/rules live in YAML config, not Python magic numbers.
- Recompute readiness via explicit service calls after mutations; do not use signals.
- Pure functions for scoring and matching (no ORM/HTTP/clock inside).
- Parsers must not import Django models or touch HTTP. Parsers return
  `RawTransactionRow`; the generic normalizer produces canonical rows.
- Run `ruff check`, `mypy`, `pytest`, and `manage.py check --deploy` before finishing.
- `mypy` is strict for `apps/` and `config/`; migrations/tests are excluded.

## Database isolation

- Two roles: `inua_migrator` owns tables/runs migrations; `inua_app` serves requests.
- RLS is enabled **and forced** on every merchant-data table, fail-closed.
- The tenant setting is transaction-local:
  `SELECT set_config('app.current_user_id', '<uuid>', true)`.
- `RLSContextMixin` sets it after authentication in every merchant view.
- Detail routes return 404 (not 403) for another tenant's resources.

## Frontend

- Next.js App Router, React, TypeScript, Tailwind.
- The frontend talks only to the Django API; never import Supabase client libraries.
- Mobile-first, plain English, no jargon, keyboard accessible, labelled inputs.
- All user-facing strings go through `lib/i18n.ts` so Swahili can be added later.
- API client stores the short-lived access token only in memory/sessionStorage and
  refreshes via the httpOnly cookie.

## Tests

- Real Postgres in all environments (RLS cannot be tested on SQLite).
- Synthetic statements only; never commit real PII.
- Isolation tests must cover raw SQL with the app role, API 404s, and document URLs.
