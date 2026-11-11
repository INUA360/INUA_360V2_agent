from __future__ import annotations

from django.db import models

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class Transaction(UUIDModel):
    class Direction(models.TextChoices):
        IN = "in", "Money in"
        OUT = "out", "Money out"

    class Source(models.TextChoices):
        MPESA_PDF = "mpesa_pdf", "M-Pesa PDF"

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="transactions"
    )
    statement = models.ForeignKey(
        "ingestion.Statement", on_delete=models.CASCADE, related_name="transactions"
    )
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.MPESA_PDF)
    source_ref = models.CharField(max_length=80)
    occurred_at = models.DateTimeField()
    direction = models.CharField(max_length=8, choices=Direction.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    counterparty_text = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=40, default="uncategorized")
    raw_details = models.TextField(blank=True)

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-occurred_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "source", "source_ref"], name="uniq_txn_business_source_ref"
            )
        ]
        indexes = [
            models.Index(fields=["business", "occurred_at"]),
            models.Index(fields=["business", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_ref} {self.direction} {self.amount}"


class MonthlyFinancial(UUIDModel):
    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="monthly_financials"
    )
    month = models.DateField(help_text="First day of the month")
    inflow = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    outflow = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    txn_count = models.PositiveIntegerField(default=0)

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["month"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "month"], name="uniq_monthly_business_month"
            )
        ]

    def __str__(self) -> str:
        return f"{self.month:%Y-%m} in={self.inflow} out={self.outflow}"


class Loan(UUIDModel):
    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="loans"
    )
    lender = models.CharField(max_length=255)
    outstanding = models.DecimalField(max_digits=14, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=14, decimal_places=2)
    ends_on = models.DateField(null=True, blank=True)

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.lender}: {self.outstanding}"


class FundingNeed(UUIDModel):
    class Purpose(models.TextChoices):
        WORKING_CAPITAL = "working_capital", "Working capital"
        STOCK = "stock", "Stock / inventory"
        EQUIPMENT = "equipment", "Equipment"
        EXPANSION = "expansion", "Expansion"
        OTHER = "other", "Other"

    class Timeframe(models.TextChoices):
        IMMEDIATE = "immediate", "Immediately"
        ONE_TO_THREE_MONTHS = "1_3_months", "1–3 months"
        THREE_TO_SIX_MONTHS = "3_6_months", "3–6 months"
        SIX_TO_TWELVE_MONTHS = "6_12_months", "6–12 months"
        FLEXIBLE = "flexible", "Flexible"

    business = models.OneToOneField(
        "businesses.Business", on_delete=models.CASCADE, related_name="funding_need"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    description = models.CharField(max_length=500, blank=True)
    timeframe = models.CharField(
        max_length=20, choices=Timeframe.choices, default=Timeframe.FLEXIBLE
    )
    avg_monthly_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    avg_monthly_expenses = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    def __str__(self) -> str:
        return f"{self.amount} for {self.purpose}"
