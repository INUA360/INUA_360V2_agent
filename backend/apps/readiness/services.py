"""Build a plain snapshot and persist the rule-based readiness result."""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

from django.utils import timezone

from apps.businesses.models import Business
from apps.compliance.models import BusinessCompliance, VerificationStatus
from apps.documents.models import Document
from apps.financials.models import Loan
from apps.financials.services import compute_metrics
from apps.readiness.engine import (
    BusinessSnapshot,
    ComplianceSnapshot,
    FinancialSnapshot,
    ReadinessResult,
    compute_readiness,
    load_config,
)
from apps.readiness.models import ReadinessAssessment


def build_snapshot(business: Business) -> BusinessSnapshot:
    compliance = BusinessCompliance.objects.filter(business=business).first()
    metrics = compute_metrics(business)
    has_loans = Loan.objects.filter(business=business).exists()

    if compliance is None:
        compliance_snapshot = ComplianceSnapshot()
    else:
        compliance_snapshot = ComplianceSnapshot(
            pin_valid=compliance.has_valid_pin(),
            pin_verified=compliance.kra_pin_verification == VerificationStatus.VERIFIED,
            tcc_valid=compliance.has_valid_tcc(),
            tcc_verified=compliance.tcc_verification == VerificationStatus.VERIFIED,
            permit_valid=compliance.has_valid_permit(),
            permit_verified=compliance.permit_verification == VerificationStatus.VERIFIED,
            registration_valid=compliance.is_registered(),
            registration_verified=(
                compliance.registration_verification == VerificationStatus.VERIFIED
            ),
            pin_present=bool(compliance.kra_pin),
            tcc_status=compliance.tcc_effective_status,
            permit_status=compliance.permit_effective_status,
        )

    financial_snapshot = FinancialSnapshot(
        has_statement=metrics.has_statement,
        months_of_data=metrics.months_of_data,
        average_monthly_inflow=float(metrics.average_monthly_inflow),
        average_monthly_revenue=float(metrics.average_monthly_revenue),
        average_monthly_outflow=float(metrics.average_monthly_outflow),
        revenue_consistency_cv=metrics.revenue_consistency_cv,
        net_cash_flow_positive_ratio=metrics.net_cash_flow_positive_ratio,
        debt_service_ratio=metrics.debt_service_ratio,
        has_loans=has_loans,
        data_confidence=metrics.data_confidence,
    )

    documents_present = frozenset(
        Document.objects.filter(business=business).values_list("doc_type", flat=True)
    )
    config = load_config()
    required_fields = config.get("required_profile_fields", [])
    values = business.required_profile_fields()
    completed = sum(1 for field_name in required_fields if values.get(field_name) not in (None, ""))

    return BusinessSnapshot(
        months_operating=business.months_operating,
        compliance=compliance_snapshot,
        financials=financial_snapshot,
        documents_present=documents_present,
        profile_fields_complete=completed,
        profile_fields_total=len(required_fields),
    )


def persist_result(business: Business, result: ReadinessResult) -> ReadinessAssessment:
    return cast(
        ReadinessAssessment,
        ReadinessAssessment.objects.create(
            business=business,
            total_score=result.total_score,
            band=result.band,
            component_scores=[asdict(component) for component in result.component_scores],
            gaps=[asdict(gap) for gap in result.gaps],
            data_confidence=result.data_confidence,
            config_version=result.config_version,
            computed_at=timezone.now(),
        ),
    )


def recompute_readiness(business: Business) -> ReadinessAssessment:
    snapshot = build_snapshot(business)
    result = compute_readiness(snapshot)
    assessment = persist_result(business, result)
    # Matching is a separate pure function; both are refreshed from one service call.
    from apps.opportunities.services import recompute_matches

    recompute_matches(business)
    return assessment


def latest_assessment(business: Business) -> ReadinessAssessment | None:
    return cast(
        ReadinessAssessment | None,
        ReadinessAssessment.objects.filter(business=business).order_by("-computed_at").first(),
    )
