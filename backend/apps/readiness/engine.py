"""Pure, deterministic readiness scoring.

No ORM calls, network calls, randomness, or clock reads happen in this module.
Callers pass a plain snapshot; the result is reproducible for a given config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "scoring_config.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle)
    return data


@dataclass(frozen=True)
class ComplianceSnapshot:
    pin_valid: bool = False
    pin_verified: bool = False
    tcc_valid: bool = False
    tcc_verified: bool = False
    permit_valid: bool = False
    permit_verified: bool = False
    registration_valid: bool = False
    registration_verified: bool = False
    pin_present: bool = False
    tcc_status: str = "none"
    permit_status: str = "none"


@dataclass(frozen=True)
class FinancialSnapshot:
    has_statement: bool
    months_of_data: int
    average_monthly_inflow: float
    average_monthly_revenue: float
    average_monthly_outflow: float
    revenue_consistency_cv: float
    net_cash_flow_positive_ratio: float
    debt_service_ratio: float | None
    has_loans: bool
    data_confidence: str
    categorisation_confidence: float = 0.0


@dataclass(frozen=True)
class BusinessSnapshot:
    months_operating: int
    compliance: ComplianceSnapshot
    financials: FinancialSnapshot
    documents_present: frozenset[str] = field(default_factory=frozenset)
    profile_fields_complete: int = 0
    profile_fields_total: int = 0


@dataclass(frozen=True)
class ComponentScore:
    key: str
    label: str
    points: float
    max_points: float
    explanation: str


@dataclass(frozen=True)
class Gap:
    key: str
    component: str
    message: str
    points_gain: float
    action: str


@dataclass(frozen=True)
class ReadinessResult:
    total_score: int
    band: str
    band_label: str
    component_scores: list[ComponentScore]
    gaps: list[Gap]
    data_confidence: str
    config_version: str
    low_data_confidence: bool
    disclaimer: str


def _band_points(value: float, bands: list[dict[str, Any]], key: str) -> float:
    for band in bands:
        limit = band.get(key)
        if limit is None or value <= limit:
            return float(band["points"])
    return 0.0


def _at_least_points(value: float, bands: list[dict[str, Any]], key: str) -> float:
    for band in bands:
        limit = band.get(key)
        if limit is None or value >= limit:
            return float(band["points"])
    return 0.0


def score_business_stability(months: int, config: dict[str, Any]) -> ComponentScore:
    spec = config["components"]["business_stability"]
    points = _band_points(months, spec["bands"], "max_months")
    explanation = f"Operating for {months} month(s)."
    return ComponentScore(
        key="business_stability",
        label=spec["label"],
        points=points,
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def score_revenue_consistency(
    financials: FinancialSnapshot, config: dict[str, Any]
) -> ComponentScore:
    spec = config["components"]["revenue_consistency"]
    months_points = _at_least_points(
        financials.months_of_data, spec["months_points"]["bands"], "min_months"
    )
    cv_points = _band_points(
        financials.revenue_consistency_cv, spec["cv_points"]["bands"], "max_cv"
    )
    raw = months_points + cv_points
    # Self-reported data receives reduced credit.
    if not financials.has_statement:
        raw *= config["thresholds"]["no_statement_credit"]
    points = round(min(raw, float(spec["weight"])), 1)
    if financials.has_statement:
        explanation = (
            f"{financials.months_of_data} month(s) of data; monthly money-in "
            f"variation (CV) {financials.revenue_consistency_cv:.2f}."
        )
    else:
        explanation = "No statement yet; self-reported revenue receives half credit."
    return ComponentScore(
        key="revenue_consistency",
        label=spec["label"],
        points=points,
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def score_cash_flow_health(financials: FinancialSnapshot, config: dict[str, Any]) -> ComponentScore:
    spec = config["components"]["cash_flow_health"]
    if financials.has_statement:
        ratio_points = _at_least_points(
            financials.net_cash_flow_positive_ratio,
            spec["positive_ratio_points"]["bands"],
            "min_ratio",
        )
    else:
        # No statement: no observed positive-month history.
        ratio_points = 0.0

    inflow = financials.average_monthly_inflow
    if inflow > 0:
        margin = (inflow - financials.average_monthly_outflow) / inflow
    else:
        margin = -1.0
    margin_points = _at_least_points(margin, spec["net_margin_points"]["bands"], "min_margin")
    raw = ratio_points + margin_points
    if not financials.has_statement:
        raw *= config["thresholds"]["no_statement_credit"]
    points = round(min(raw, float(spec["weight"])), 1)
    explanation = (
        f"{financials.net_cash_flow_positive_ratio:.0%} of months had net cash flow "
        f"at or above zero; average net margin {margin:.0%}."
    )
    return ComponentScore(
        key="cash_flow_health",
        label=spec["label"],
        points=points,
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def _compliance_field_points(valid: bool, verified: bool, spec: dict[str, Any]) -> float:
    if not valid:
        return 0.0
    multiplier = (
        float(spec["verified_multiplier"]) if verified else float(spec["self_reported_multiplier"])
    )
    return float(spec["field_points"]) * multiplier


def score_compliance(compliance: ComplianceSnapshot, config: dict[str, Any]) -> ComponentScore:
    spec = config["components"]["compliance"]
    fields = [
        ("KRA PIN", compliance.pin_valid, compliance.pin_verified),
        ("valid TCC", compliance.tcc_valid, compliance.tcc_verified),
        ("valid county permit", compliance.permit_valid, compliance.permit_verified),
        ("business registration", compliance.registration_valid, compliance.registration_verified),
    ]
    points = sum(_compliance_field_points(valid, verified, spec) for _, valid, verified in fields)
    met = [name for name, valid, _ in fields if valid]
    missing = [name for name, valid, _ in fields if not valid]
    explanation = f"Provided: {', '.join(met) if met else 'none'}."
    if missing:
        explanation += f" Missing: {', '.join(missing)}."
    return ComponentScore(
        key="compliance",
        label=spec["label"],
        points=round(min(points, float(spec["weight"])), 1),
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def score_debt_load(financials: FinancialSnapshot, config: dict[str, Any]) -> ComponentScore:
    spec = config["components"]["debt_load"]
    if not financials.has_loans and financials.debt_service_ratio is None:
        points = float(spec["no_debt_points"])
        explanation = "No debts recorded."
    elif financials.debt_service_ratio is None:
        points = 0.0
        explanation = "Loan repayments recorded but no money-in data to compare against."
    else:
        points = _band_points(financials.debt_service_ratio, spec["dsr_bands"], "max_dsr")
        explanation = (
            f"Estimated debt service uses {financials.debt_service_ratio:.0%} of "
            "average monthly money-in."
        )
    return ComponentScore(
        key="debt_load",
        label=spec["label"],
        points=round(points, 1),
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def score_documentation(
    documents_present: frozenset[str], config: dict[str, Any]
) -> ComponentScore:
    spec = config["components"]["documentation"]
    required = set(config["document_checklist"])
    present = documents_present & required
    share = len(present) / len(required) if required else 0.0
    points = round(share * float(spec["weight"]), 1)
    explanation = f"{len(present)} of {len(required)} standard documents uploaded."
    return ComponentScore(
        key="documentation",
        label=spec["label"],
        points=points,
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def score_profile_completeness(
    fields_complete: int, fields_total: int, config: dict[str, Any]
) -> ComponentScore:
    spec = config["components"]["profile_completeness"]
    share = (fields_complete / fields_total) if fields_total else 0.0
    points = round(share * float(spec["weight"]), 1)
    explanation = f"{fields_complete} of {fields_total} required profile fields complete."
    return ComponentScore(
        key="profile_completeness",
        label=spec["label"],
        points=points,
        max_points=float(spec["weight"]),
        explanation=explanation,
    )


def _band_for(score: int, config: dict[str, Any]) -> tuple[str, str]:
    for band in config["thresholds"]["bands"]:
        if score >= band["min_score"]:
            return str(band["key"]), str(band["label"])
    return "not_yet_ready", "Not yet ready"


def _build_gaps(
    snapshot: BusinessSnapshot, components: dict[str, ComponentScore], config: dict[str, Any]
) -> list[Gap]:
    gaps: list[Gap] = []
    compliance = snapshot.compliance
    financials = snapshot.financials

    def add(key: str, component: str, message: str, points_gain: float, action: str) -> None:
        if points_gain > 0.01:
            gaps.append(
                Gap(
                    key=key,
                    component=component,
                    message=message,
                    points_gain=round(points_gain, 1),
                    action=action,
                )
            )

    stability = components["business_stability"]
    if stability.points < stability.max_points:
        add(
            "operating_history",
            "business_stability",
            "Your operating history is shorter than three years.",
            stability.max_points - stability.points,
            "Keep the business profile start date accurate; this component improves with time.",
        )

    revenue = components["revenue_consistency"]
    if not financials.has_statement:
        add(
            "upload_statement",
            "revenue_consistency",
            "No M-Pesa statement has been confirmed, so revenue is low-confidence.",
            round(revenue.max_points * 0.75 - revenue.points, 1),
            "Upload and confirm an M-Pesa statement to replace self-reported figures.",
        )
    elif financials.months_of_data < 6:
        add(
            "more_months",
            "revenue_consistency",
            f"Only {financials.months_of_data} month(s) of statement data are available.",
            round(revenue.max_points - revenue.points, 1),
            "Upload a statement covering at least six months if you have one.",
        )
    elif financials.revenue_consistency_cv > 0.5:
        add(
            "revenue_variation",
            "revenue_consistency",
            "Monthly money-in varies widely across the statement period.",
            round(revenue.max_points - revenue.points, 1),
            "A longer period of statements may show your normal seasonal pattern.",
        )

    cash = components["cash_flow_health"]
    if financials.has_statement and cash.points < cash.max_points:
        add(
            "cash_flow",
            "cash_flow_health",
            "Some months had more money out than in.",
            round(cash.max_points - cash.points, 1),
            "Review the months where outflow exceeded inflow and the transactions behind them.",
        )
    elif not financials.has_statement:
        add(
            "cash_flow_self_reported",
            "cash_flow_health",
            "Cash flow is self-reported and receives reduced credit.",
            round(cash.max_points - cash.points, 1),
            "Upload an M-Pesa statement to support the cash-flow figures.",
        )

    comp_spec = config["components"]["compliance"]
    compliance_fields = [
        (
            "kra_pin",
            compliance.pin_valid,
            compliance.pin_verified,
            compliance.pin_present,
            "Add your KRA PIN and mark the PIN status as active.",
            "KRA PIN",
        ),
        (
            "tcc",
            compliance.tcc_valid,
            compliance.tcc_verified,
            compliance.tcc_status != "none",
            "Add a valid Tax Compliance Certificate and its expiry date.",
            "valid TCC",
        ),
        (
            "county_permit",
            compliance.permit_valid,
            compliance.permit_verified,
            compliance.permit_status != "none",
            "Add a current county business permit and expiry date.",
            "valid county permit",
        ),
        (
            "registration",
            compliance.registration_valid,
            compliance.registration_verified,
            compliance.registration_valid,
            "Add your business registration number.",
            "business registration",
        ),
    ]
    for key, valid, verified, present, action, label in compliance_fields:
        full = float(comp_spec["field_points"])
        current = (
            full
            * (
                float(comp_spec["verified_multiplier"])
                if verified
                else float(comp_spec["self_reported_multiplier"])
            )
            if valid
            else 0.0
        )
        if not valid:
            add(
                key,
                "compliance",
                f"{label.capitalize()} is missing or not current.",
                round(full - current, 1),
                action,
            )
        elif not verified and present:
            add(
                f"{key}_verify",
                "compliance",
                f"{label.capitalize()} is self-reported.",
                round(full - current, 1),
                "Independent verification is not available yet; this will improve "
                "in a later release.",
            )

    debt = components["debt_load"]
    if financials.has_loans and debt.points < debt.max_points:
        add(
            "debt_load",
            "debt_load",
            "Recorded loan repayments take a large share of monthly money-in.",
            round(debt.max_points - debt.points, 1),
            "Review existing loan repayments in the loans section.",
        )

    doc_spec = config["components"]["documentation"]
    required_docs = set(config["document_checklist"])
    missing_docs = required_docs - set(snapshot.documents_present)
    per_doc = float(doc_spec["weight"]) / len(required_docs) if required_docs else 0
    for doc_type in sorted(missing_docs):
        add(
            f"document_{doc_type}",
            "documentation",
            f"Missing document: {doc_type.replace('_', ' ')}.",
            round(per_doc, 1),
            f"Upload your {doc_type.replace('_', ' ')} in the Documents section.",
        )

    profile = components["profile_completeness"]
    if snapshot.profile_fields_complete < snapshot.profile_fields_total:
        missing = snapshot.profile_fields_total - snapshot.profile_fields_complete
        add(
            "profile_completeness",
            "profile_completeness",
            f"{missing} required business profile field(s) are incomplete.",
            round(profile.max_points - profile.points, 1),
            "Complete the remaining fields in your business profile.",
        )

    gaps.sort(key=lambda gap: (-gap.points_gain, gap.key))
    return gaps


def compute_readiness(
    snapshot: BusinessSnapshot, config: dict[str, Any] | None = None
) -> ReadinessResult:
    config = config or load_config()
    financials = snapshot.financials

    components = {
        "business_stability": score_business_stability(snapshot.months_operating, config),
        "revenue_consistency": score_revenue_consistency(financials, config),
        "cash_flow_health": score_cash_flow_health(financials, config),
        "compliance": score_compliance(snapshot.compliance, config),
        "debt_load": score_debt_load(financials, config),
        "documentation": score_documentation(snapshot.documents_present, config),
        "profile_completeness": score_profile_completeness(
            snapshot.profile_fields_complete, snapshot.profile_fields_total, config
        ),
    }
    total = int(round(sum(component.points for component in components.values())))
    total = max(0, min(total, 100))
    band, band_label = _band_for(total, config)
    gaps = _build_gaps(snapshot, components, config)

    confidence = financials.data_confidence
    if not financials.has_statement:
        confidence = "low"
    low_data = confidence == "low"
    return ReadinessResult(
        total_score=total,
        band=band,
        band_label=band_label,
        component_scores=list(components.values()),
        gaps=gaps,
        data_confidence=confidence,
        config_version=str(config["version"]),
        low_data_confidence=low_data,
        disclaimer=str(config["notes"]["disclaimer"]).strip(),
    )
