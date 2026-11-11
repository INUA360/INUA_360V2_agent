from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class Statement(UUIDModel):
    class Source(models.TextChoices):
        MPESA_PDF = "mpesa_pdf", "M-Pesa PDF"

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="statements"
    )
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.MPESA_PDF)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    parse_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-period_end", "-created_at"]

    def __str__(self) -> str:
        return f"{self.source} statement {self.period_start}–{self.period_end}"


class PendingStatement(UUIDModel):
    """Short-lived parse→confirm hold.

    Contains only normalized transaction rows and summary metadata. It never
    contains the uploaded PDF, decrypted bytes, National ID, or password.
    """

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="pending_statements"
    )
    source = models.CharField(max_length=32, default=Statement.Source.MPESA_PDF)
    normalized_rows = models.JSONField(default=list)
    summary = models.JSONField(default=dict)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    expires_at = models.DateTimeField()

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @classmethod
    def purge_expired(cls) -> int:
        deleted, _ = cls.objects.filter(expires_at__lte=timezone.now()).delete()
        return int(deleted)
