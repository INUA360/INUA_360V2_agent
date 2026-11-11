"""Onboarding progress is derived from real records, never client input."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import User


def onboarding_percent(user: User) -> int:
    from apps.businesses.models import Business
    from apps.compliance.models import BusinessCompliance
    from apps.documents.models import Document
    from apps.financials.models import FundingNeed
    from apps.ingestion.models import Statement

    business = Business.objects.for_user(user).first()  # type: ignore[attr-defined]
    if business is None:
        return 0

    percent = 25
    compliance = BusinessCompliance.objects.for_user(user).filter(business=business).first()  # type: ignore[attr-defined]
    if compliance and compliance.kra_pin:
        percent += 25

    has_statement = (
        Statement.objects.for_user(user)  # type: ignore[attr-defined]
        .filter(business=business, status="confirmed")
        .exists()
    )
    has_manual = FundingNeed.objects.for_user(user).filter(business=business).exists()  # type: ignore[attr-defined]
    if has_statement or has_manual:
        percent += 25

    if Document.objects.for_user(user).filter(business=business).exists():  # type: ignore[attr-defined]
        percent += 25
    return min(percent, 100)


def is_onboarding_complete(user: User) -> bool:
    return onboarding_percent(user) >= 100


def advance_onboarding_step(user: User, step: int) -> None:
    if step > user.onboarding_step:
        user.onboarding_step = step
        user.save(update_fields=["onboarding_step", "updated_at"])
