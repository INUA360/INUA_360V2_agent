# Funding Readiness rubric

> This score is a transparent rubric based on common lending criteria. It is not a
> credit score and does not guarantee funding.

The engine lives in `backend/apps/readiness/engine.py` as pure functions. Every
weight, band, label, and threshold is in
`backend/apps/readiness/scoring_config.yaml` (version `1.0.0`). The score is
deterministic: the same snapshot and config always produce the same result.

## Components (100 points)

| Component | Max | What it measures |
|-----------|-----|------------------|
| Business stability | 15 | Months operating |
| Revenue consistency | 20 | Months of data (10) + coefficient of variation of monthly money-in (10) |
| Cash flow health | 15 | Share of months with net ≥ 0 (8) + average net margin (7) |
| Compliance | 20 | KRA PIN, valid TCC, valid county permit, business registration (5 each) |
| Debt load | 10 | Estimated debt-service ratio |
| Documentation | 15 | Share of six standard documents uploaded |
| Profile completeness | 5 | Share of required business profile fields complete |

Total = sum of component points, rounded to the nearest integer, clamped to 0–100.

### Business stability (15)

| Months operating | Points |
|------------------|--------|
| 0–5 | 0 |
| 6–11 | 5 |
| 12–23 | 9 |
| 24–35 | 12 |
| 36+ | 15 |

### Revenue consistency (20)

Months of data:

| Months | Points |
|--------|--------|
| ≥6 | 10 |
| 4–5 | 7 |
| 3 | 4 |
| 1–2 | 2 |
| 0 | 0 |

Monthly money-in variation (CV = population standard deviation ÷ mean of monthly
inflows over the statement period):

| CV | Points |
|----|--------|
| ≤0.20 | 10 |
| ≤0.35 | 8 |
| ≤0.50 | 5 |
| ≤0.75 | 2 |
| >0.75 | 0 |

With no confirmed statement, this component is computed from self-reported figures
and then multiplied by **0.5** (the `no_statement_credit` threshold).

### Cash flow health (15)

Share of months where `net ≥ 0`:

| Ratio | Points |
|-------|--------|
| ≥0.80 | 8 |
| ≥0.60 | 6 |
| ≥0.40 | 4 |
| ≥0.20 | 2 |
| <0.20 | 0 |

Average net margin = `(average monthly inflow − average monthly outflow) ÷ average
monthly inflow`:

| Margin | Points |
|--------|--------|
| ≥0.20 | 7 |
| ≥0.10 | 5 |
| ≥0.05 | 3 |
| ≥0 | 1 |
| <0 | 0 |

With no statement, the observed positive-month ratio is 0 and the whole component is
multiplied by **0.5**.

### Compliance (20)

Each of the four facts is worth 5 points when valid:

- KRA PIN present and marked active
- TCC effective status is valid (expiry not passed)
- County permit is valid (not expired; `expiring_soon` is still valid but highlighted)
- Registration status is registered with a registration number

**Verification multiplier:** self-reported facts earn **70%** of the field points;
independently verified facts earn **100%**. In Milestone 1 every implementation is
self-reported, so the practical maximum is 14/20 until a live verifier exists.

### Debt load (10)

Debt-service ratio estimate:

```
(monthly repayments from the loans table
 + average monthly outflows categorised as loan/fuliza repayments)
÷ average monthly money-in
```

| DSR | Points |
|-----|--------|
| No recorded debt / no DSR | 10 |
| ≤0.10 | 10 |
| ≤0.20 | 8 |
| ≤0.30 | 6 |
| ≤0.40 | 3 |
| >0.40 | 0 |

If loans exist but there is no money-in data to compute a ratio, the component scores 0.

### Documentation (15)

15 × (number of standard documents present ÷ 6). The standard list:

1. Business registration certificate
2. KRA PIN certificate
3. Tax Compliance Certificate
4. County business permit
5. Owner ID
6. Bank statement

### Profile completeness (5)

5 × (completed required fields ÷ 10). Required fields: name, sector, what they sell,
county, town, started date, structure, employee band, owner name, owner phone.

## Bands

| Score | Band key | Label |
|-------|----------|-------|
| 80–100 | `strong` | Strong |
| 60–79 | `fundable_with_preparation` | Fundable with preparation |
| 40–59 | `getting_there` | Getting there |
| 0–39 | `not_yet_ready` | Not yet ready |

## Data confidence

- **low:** no confirmed statement (self-reported figures only), or fewer than 3 months
- **medium:** 3–5 months, or low categorization confidence
- **high:** ≥6 months with customer-payment categorization share ≥30%

The assessment exposes `data_confidence` and `low_data_confidence`. The UI must show
a visible low-confidence flag when present.

## Gaps / "How to improve"

Each gap has:

- `key`, `component`, `message`
- `points_gain` — points available if the gap is closed
- `action` — a concrete, descriptive next step

Gaps are sorted by `points_gain` (descending). For self-reported compliance facts
there is an explicit "verification not available yet" gap; we do not pretend
verification exists.

## Revenue assumption and caveat

Customer payments are identified by keyword rules. If they make up **at least 30%**
of total money-in, average revenue = customer-payment total ÷ months. Otherwise all
money-in is used as a revenue approximation and the API returns a caveat that this
may overstate revenue. This is surfaced in `/financials/summary` and in the score UI.

## History and recomputation

A `ReadinessAssessment` is stored on every recompute, preserving history so merchants
can see improvement. Recompute is triggered explicitly by service calls after profile,
compliance, statement, loan, funding-need, and document changes. Matching is refreshed
in the same service call.

## Rules we deliberately avoid

- No credit bureau data, no prediction, no ML, no black-box weighting.
- No claims that a score guarantees approval.
- No financial advice; actions describe what would change the rubric, not what the
  merchant "should" do with their money.

## TODO(owner)

Confirm these weights and bands with a practitioner who has SME lending/credit
experience before launch. Adjust only `scoring_config.yaml`; bump the config version
so stored assessments remain explainable.
