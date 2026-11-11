"""Pure matching and eligibility explanations.

Hard filters remove an opportunity entirely. Soft requirements produce a fit
level and a concrete explanation of what is met, what is missing, and what
would move the match to Strong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class MatchSnapshot:
    sector: str
    county: str
    structure: str
    months_operating: int
    requested_amount: Decimal | None
    readiness_score: int
    pin_valid: bool = False
    tcc_valid: bool = False
    permit_valid: bool = False
    registration_valid: bool = False
    tcc_status: str = "none"
    permit_status: str = "none"
    documents_present: frozenset[str] = field(default_factory=frozenset)
    today: date = field(default_factory=date.today)


@dataclass(frozen=True)
class OpportunityData:
    id: str
    name: str
    provider: str
    provider_type: str
    type: str
    min_amount: Decimal
    max_amount: Decimal
    allowed_sectors: tuple[str, ...] = ()
    counties: tuple[str, ...] = ()
    min_months_operating: int = 0
    min_readiness_score: int = 0
    required_compliance: tuple[str, ...] = ()
    required_documents: tuple[str, ...] = ()
    accepts_informal: bool = True
    application_url: str = ""
    deadline: date | None = None
    status: str = "active"
    description: str = ""


@dataclass(frozen=True)
class CriterionResult:
    key: str
    label: str
    met: bool
    detail: str


@dataclass(frozen=True)
class Match:
    opportunity_id: str
    opportunity_name: str
    provider: str
    fit_level: str
    met: list[CriterionResult]
    missing: list[CriterionResult]
    moves_to_strong: list[str]
    explanation: dict[str, Any]
    amount_distance: float
    deadline_sort: str


COMPLIANCE_LABELS = {
    "pin": "KRA PIN",
    "tcc": "valid TCC",
    "permit": "valid county permit",
    "registration": "business registration",
}

DOCUMENT_LABELS = {
    "business_registration_certificate": "Business registration certificate",
    "kra_pin_certificate": "KRA PIN certificate",
    "tcc": "Tax Compliance Certificate",
    "county_permit": "County business permit",
    "id_owner": "Owner ID",
    "business_plan": "Business plan",
    "bank_statement": "Bank statement",
    "lease_premises": "Lease / premises proof",
    "other": "Other supporting document",
}

FIT_ORDER = {"strong": 0, "possible": 1, "stretch": 2}


def _amount_overlaps(requested: Decimal | None, minimum: Decimal, maximum: Decimal) -> bool:
    if requested is None:
        return True
    return minimum <= requested <= maximum


def _hard_filter(snapshot: MatchSnapshot, opportunity: OpportunityData) -> bool:
    if opportunity.status != "active":
        return False
    if opportunity.deadline and opportunity.deadline < snapshot.today:
        return False
    if opportunity.allowed_sectors and snapshot.sector not in opportunity.allowed_sectors:
        return False
    if opportunity.counties and snapshot.county not in opportunity.counties:
        return False
    if not _amount_overlaps(
        snapshot.requested_amount, opportunity.min_amount, opportunity.max_amount
    ):
        return False
    return True


def _compliance_check(snapshot: MatchSnapshot, flag: str) -> CriterionResult:
    label = COMPLIANCE_LABELS.get(flag, flag)
    if flag == "pin":
        met = snapshot.pin_valid
        detail = "KRA PIN is active." if met else "Add an active KRA PIN."
    elif flag == "tcc":
        met = snapshot.tcc_valid
        if met:
            detail = "TCC is valid."
        elif snapshot.tcc_status == "expired":
            detail = "Needs a valid TCC; you've marked yours as expired."
        else:
            detail = "Needs a valid TCC; none is recorded."
    elif flag == "permit":
        met = snapshot.permit_valid
        if met:
            detail = "County permit is valid."
        elif snapshot.permit_status == "expiring_soon":
            detail = "County permit expires soon; renew it before applying."
        elif snapshot.permit_status == "expired":
            detail = "County permit is expired."
        else:
            detail = "No county permit is recorded."
    elif flag == "registration":
        met = snapshot.registration_valid
        detail = (
            "Business registration number is recorded."
            if met
            else ("Business registration is required.")
        )
    else:
        met = False
        detail = f"Unknown requirement: {flag}."
    return CriterionResult(key=f"compliance:{flag}", label=label, met=met, detail=detail)


def _document_check(snapshot: MatchSnapshot, doc_type: str) -> CriterionResult:
    label = DOCUMENT_LABELS.get(doc_type, doc_type.replace("_", " ").title())
    met = doc_type in snapshot.documents_present
    detail = "Uploaded." if met else f"Upload your {label.lower()}."
    return CriterionResult(key=f"document:{doc_type}", label=label, met=met, detail=detail)


def evaluate_match(snapshot: MatchSnapshot, opportunity: OpportunityData) -> Match | None:
    if not _hard_filter(snapshot, opportunity):
        return None

    met: list[CriterionResult] = []
    missing: list[CriterionResult] = []
    score_gap = max(opportunity.min_readiness_score - snapshot.readiness_score, 0)

    def add(result: CriterionResult) -> None:
        (met if result.met else missing).append(result)

    if opportunity.min_readiness_score:
        add(
            CriterionResult(
                key="readiness_score",
                label="Readiness score",
                met=score_gap == 0,
                detail=(
                    f"Score {snapshot.readiness_score} meets the minimum "
                    f"{opportunity.min_readiness_score}."
                    if score_gap == 0
                    else (
                        f"Needs {opportunity.min_readiness_score}; "
                        f"you are {score_gap} points short."
                    )
                ),
            )
        )
    if opportunity.min_months_operating:
        add(
            CriterionResult(
                key="operating_months",
                label="Operating history",
                met=snapshot.months_operating >= opportunity.min_months_operating,
                detail=(
                    f"{snapshot.months_operating} months operating meets the "
                    f"{opportunity.min_months_operating}-month minimum."
                    if snapshot.months_operating >= opportunity.min_months_operating
                    else f"Needs {opportunity.min_months_operating} months operating; "
                    f"you have {snapshot.months_operating}."
                ),
            )
        )
    for flag in opportunity.required_compliance:
        add(_compliance_check(snapshot, flag))
    for doc_type in opportunity.required_documents:
        add(_document_check(snapshot, doc_type))

    informal_structures = {"sole_proprietor", "sacco_group", "other"}
    if opportunity.accepts_informal and snapshot.structure in informal_structures:
        met.append(
            CriterionResult(
                key="informal_accepted",
                label="Informal business structure",
                met=True,
                detail="This provider accepts informal businesses.",
            )
        )
    elif not opportunity.accepts_informal and snapshot.structure in informal_structures:
        missing.append(
            CriterionResult(
                key="formal_structure",
                label="Formal business structure",
                met=False,
                detail="This provider requires a registered company or partnership.",
            )
        )

    missing_count = len(missing)
    if missing_count == 0:
        fit = "strong"
    elif missing_count <= 2 and score_gap <= 15:
        fit = "possible"
    else:
        fit = "stretch"

    moves = [f"{item.label}: {item.detail}" for item in missing[:5]]
    if fit == "possible":
        moves.append("Close the remaining gaps to move this match to Strong.")

    midpoint = (opportunity.min_amount + opportunity.max_amount) / Decimal("2")
    requested = snapshot.requested_amount or midpoint
    distance = abs(requested - midpoint)
    explanation = {
        "summary": (
            "Meets all listed requirements."
            if fit == "strong"
            else f"Meets the basic filters but misses {missing_count} requirement(s)."
        ),
        "met": [{"key": item.key, "label": item.label, "detail": item.detail} for item in met],
        "missing": [
            {"key": item.key, "label": item.label, "detail": item.detail} for item in missing
        ],
        "moves_to_strong": moves,
        "score_gap": score_gap,
    }
    return Match(
        opportunity_id=opportunity.id,
        opportunity_name=opportunity.name,
        provider=opportunity.provider,
        fit_level=fit,
        met=met,
        missing=missing,
        moves_to_strong=moves,
        explanation=explanation,
        amount_distance=float(distance),
        deadline_sort=opportunity.deadline.isoformat() if opportunity.deadline else "9999-12-31",
    )


def match(snapshot: MatchSnapshot, opportunities: list[OpportunityData]) -> list[Match]:
    results = [
        result
        for opportunity in opportunities
        if (result := evaluate_match(snapshot, opportunity)) is not None
    ]
    results.sort(
        key=lambda item: (
            FIT_ORDER[item.fit_level],
            item.amount_distance,
            item.deadline_sort,
            item.opportunity_name,
        )
    )
    return results
