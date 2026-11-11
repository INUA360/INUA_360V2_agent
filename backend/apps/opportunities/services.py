"""ORM adapter around the pure matching/checklist functions."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.businesses.models import Business
from apps.compliance.models import BusinessCompliance
from apps.documents.models import Document
from apps.opportunities.checklist import build_checklist
from apps.opportunities.matching import (
    FIT_ORDER,
    MatchSnapshot,
    OpportunityData,
    evaluate_match,
)
from apps.opportunities.models import Opportunity, OpportunityMatch
from apps.readiness.services import latest_assessment

STALE_LISTING_DAYS = 120


def _opportunity_data(opportunity: Opportunity) -> OpportunityData:
    return OpportunityData(
        id=str(opportunity.id),
        name=opportunity.name,
        provider=opportunity.provider,
        provider_type=opportunity.provider_type,
        type=opportunity.type,
        min_amount=opportunity.min_amount,
        max_amount=opportunity.max_amount,
        allowed_sectors=tuple(opportunity.allowed_sectors or []),
        counties=tuple(opportunity.counties or []),
        min_months_operating=opportunity.min_months_operating,
        min_readiness_score=opportunity.min_readiness_score,
        required_compliance=tuple(opportunity.required_compliance or []),
        required_documents=tuple(opportunity.required_documents or []),
        accepts_informal=opportunity.accepts_informal,
        application_url=opportunity.application_url,
        deadline=opportunity.deadline,
        status=opportunity.status,
        description=opportunity.description,
    )


def build_match_snapshot(business: Business) -> MatchSnapshot:
    compliance = BusinessCompliance.objects.filter(business=business).first()
    funding_need = getattr(business, "funding_need", None)
    requested = funding_need.amount if funding_need else None
    if requested is not None:
        requested = Decimal(requested)
    assessment = latest_assessment(business)
    score = assessment.total_score if assessment else 0
    documents = frozenset(
        Document.objects.filter(business=business).values_list("doc_type", flat=True)
    )

    return MatchSnapshot(
        sector=business.sector,
        county=business.county,
        structure=business.structure,
        months_operating=business.months_operating,
        requested_amount=requested,
        readiness_score=score,
        pin_valid=bool(compliance and compliance.has_valid_pin()),
        tcc_valid=bool(compliance and compliance.has_valid_tcc()),
        permit_valid=bool(compliance and compliance.has_valid_permit()),
        registration_valid=bool(compliance and compliance.is_registered()),
        tcc_status=compliance.tcc_effective_status if compliance else "none",
        permit_status=compliance.permit_effective_status if compliance else "none",
        documents_present=documents,
        today=timezone.localdate(),
    )


def active_opportunities() -> list[Opportunity]:
    cutoff = timezone.now() - timedelta(days=STALE_LISTING_DAYS)
    return list(
        Opportunity.objects.filter(status=Opportunity.Status.ACTIVE, last_verified_at__gte=cutoff)
    )


def recompute_matches(business: Business) -> list[OpportunityMatch]:
    snapshot = build_match_snapshot(business)
    opportunities = active_opportunities()
    computed = []
    for opportunity in opportunities:
        result = evaluate_match(snapshot, _opportunity_data(opportunity))
        if result is not None:
            computed.append((opportunity, result))

    keep_ids = []
    now = timezone.now()
    for opportunity, result in computed:
        match_row, _ = OpportunityMatch.objects.update_or_create(
            business=business,
            opportunity=opportunity,
            defaults={
                "fit_level": result.fit_level,
                "explanation": result.explanation,
                "computed_at": now,
            },
        )
        keep_ids.append(match_row.id)

    OpportunityMatch.objects.filter(business=business).exclude(id__in=keep_ids).delete()
    return list(OpportunityMatch.objects.filter(business=business, id__in=keep_ids))


def list_matches(business: Business, include_dismissed: bool = False) -> list[OpportunityMatch]:
    queryset = OpportunityMatch.objects.filter(business=business).select_related("opportunity")
    if not include_dismissed:
        queryset = queryset.exclude(state=OpportunityMatch.State.DISMISSED)
    rows = list(queryset)
    rows.sort(
        key=lambda row: (
            FIT_ORDER.get(row.fit_level, 9),
            row.opportunity.min_readiness_score,
            row.opportunity.deadline or datetime.max.date(),
            row.opportunity.name,
        )
    )
    return rows


def checklist_for(business: Business, opportunity: Opportunity) -> dict[str, Any]:
    snapshot = build_match_snapshot(business)
    return build_checklist(snapshot, _opportunity_data(opportunity))
