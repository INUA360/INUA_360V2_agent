from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class Opportunity(UUIDModel):
    class ProviderType(models.TextChoices):
        BANK = "bank", "Bank"
        SACCO = "sacco", "SACCO"
        MFI = "mfi", "Microfinance institution"
        GOVERNMENT = "government", "Government"
        NGO_GRANT = "ngo_grant", "NGO / grant"
        DFI = "dfi", "Development finance institution"
        EQUIPMENT_FINANCIER = "equipment_financier", "Equipment financier"

    class Type(models.TextChoices):
        LOAN = "loan", "Loan"
        GRANT = "grant", "Grant"
        ASSET_FINANCE = "asset_finance", "Asset finance"
        SACCO_LOAN = "sacco_loan", "SACCO loan"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        DRAFT = "draft", "Draft"

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    provider_type = models.CharField(max_length=40, choices=ProviderType.choices)
    type = models.CharField(max_length=40, choices=Type.choices)
    description = models.TextField()
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2)
    allowed_sectors = models.JSONField(default=list, blank=True)
    counties = models.JSONField(default=list, blank=True)
    min_months_operating = models.PositiveIntegerField(default=0)
    min_readiness_score = models.PositiveSmallIntegerField(default=0)
    required_compliance = models.JSONField(default=list, blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    accepts_informal = models.BooleanField(default=True)
    application_url = models.URLField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    source_url = models.URLField(blank=True)
    last_verified_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_stale(self) -> bool:
        return self.last_verified_at < timezone.now() - timedelta(days=60)

    @property
    def is_expired_listing(self) -> bool:
        return self.last_verified_at < timezone.now() - timedelta(days=120)

    @property
    def deadline_passed(self) -> bool:
        return bool(self.deadline and self.deadline < timezone.localdate())


class OpportunityMatch(UUIDModel):
    class FitLevel(models.TextChoices):
        STRONG = "strong", "Strong"
        POSSIBLE = "possible", "Possible"
        STRETCH = "stretch", "Stretch"

    class State(models.TextChoices):
        NEW = "new", "New"
        SAVED = "saved", "Saved"
        APPLIED = "applied", "Applied (self-reported)"
        DISMISSED = "dismissed", "Dismissed"

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="opportunity_matches"
    )
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="matches")
    fit_level = models.CharField(max_length=20, choices=FitLevel.choices)
    explanation = models.JSONField(default=dict)
    state = models.CharField(max_length=20, choices=State.choices, default=State.NEW)
    computed_at = models.DateTimeField()

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["fit_level", "opportunity__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "opportunity"], name="uniq_match_business_opportunity"
            )
        ]

    def __str__(self) -> str:
        return f"{self.opportunity.name} ({self.fit_level})"
