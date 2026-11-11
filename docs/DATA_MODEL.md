# Data model and isolation map

All merchant models use UUID primary keys plus `created_at` and `updated_at`
(via `apps.common.models.UUIDModel` unless noted). Postgres table names follow
Django defaults.

## Tables

| Model (app) | Key fields | Tenant path | RLS |
|-------------|-----------|-------------|-----|
| `User` (accounts) | email (login), phone, role, consent version/time, onboarding step/completion | self | **No** — identity must resolve before a tenant is known |
| `OneTimeToken` (accounts) | user, purpose, hashed token, expiry, used_at | user | No |
| `Business` (businesses) | owner 1:1, name, sector, county, started_on, structure, employee_band, owner contacts | `owner_id` | Yes |
| `BusinessCompliance` (compliance) | business 1:1, registration, KRA PIN, TCC, county permit, per-field verification status, other permits JSON | `business.owner_id` | Yes |
| `Statement` (ingestion) | business, source, period, row count, warnings, parse metadata | `business.owner_id` | Yes |
| `PendingStatement` (ingestion) | business, normalized rows JSON, summary JSON, TTL expiry | `business.owner_id` | Yes |
| `Transaction` (financials) | business, statement, source, source_ref, occurred_at, direction, amount, balance, category, raw_details | `business.owner_id` | Yes |
| `MonthlyFinancial` (financials) | business, month (unique per business), inflow, outflow, net, txn_count | `business.owner_id` | Yes |
| `Loan` (financials) | business, lender, outstanding, monthly_repayment, ends_on | `business.owner_id` | Yes |
| `FundingNeed` (financials) | business 1:1, amount, purpose, description, timeframe, optional self-reported revenue/expenses | `business.owner_id` | Yes |
| `Document` (documents) | business, doc_type, storage_key, filename, content_type, size, expiry_date | `business.owner_id` | Yes |
| `ReadinessAssessment` (readiness) | business, total score, band, component scores JSON, gaps JSON, confidence, config version, computed_at | `business.owner_id` | Yes |
| `Opportunity` (opportunities) | global catalog: provider, type, amounts, sectors, counties, requirements, freshness | global | No (staff-curated catalog) |
| `OpportunityMatch` (opportunities) | business, opportunity, fit level, explanation JSON, state | `business.owner_id` | Yes |
| `AuditLog` (audit) | actor, business (nullable), action, entity, metadata | business or actor | Yes (owner or own actor-only event) |

## Unique constraints

- `Transaction (business, source, source_ref)` — dedupe overlapping statements.
- `MonthlyFinancial (business, month)` — one aggregate row per month.
- `OpportunityMatch (business, opportunity)` — one match row per business/opportunity.

## RLS

Migration: `apps/common/migrations/0001_rls.py` (runs after every app's initial
migration). It:

1. Creates `app_current_user_id()` returning NULL unless
   `current_setting('app.current_user_id', true)` is a UUID.
2. Enables and forces RLS on every merchant table above.
3. Adds `USING` and `WITH CHECK` policies:

```sql
-- Business
owner_id = app_current_user_id()

-- Child tables
EXISTS (
  SELECT 1 FROM businesses_business b
  WHERE b.id = <table>.business_id
    AND b.owner_id = app_current_user_id()
)

-- AuditLog
(business_id IS NOT NULL AND EXISTS (...))
OR (business_id IS NULL AND actor_id = app_current_user_id())
```

4. Grants DML on all tables and sequences to `inua_app`.

The policy fails closed: a missing tenant setting yields NULL, so no rows are
visible and `WITH CHECK` rejects writes.

## Django-level scoping

Every merchant model has `objects = OwnedManager()`. `Model.objects.for_user(user)`
filters via the model's `owner_lookup` (`owner_id` or `business__owner_id`). Views
use this manager, never `.objects.all()`/`.objects.get(pk=...)`. Detail routes return
404 for another tenant's row. Object permissions (`IsBusinessOwner`) are applied in
addition to scoping.

`apps/common/mixins.py::RLSContextMixin.initial()` executes the transaction-local
`set_config` after authentication for every merchant API view.

## Storage

Documents are stored at:

```
{user_id}/{business_id}/{doc_type}/{uuid}-{sanitized_filename}
```

The bucket is private. Production access is a presigned URL ≤300 seconds. Local
development streams through an ownership-checked Django endpoint.

## Deletion

`DELETE /api/v1/me/data` removes stored document objects, audit events, refresh
tokens, the user, and (by cascade) the business and every child record.
