from __future__ import annotations

from django.db import models

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class ReadinessAssessment(UUIDModel):
    class Band(models.TextChoices):
        NOT_YET = "not_yet_ready", "Not yet ready"
        GETTING_THERE = "getting_there", "Getting there"
        FUNDABLE_WITH_PREPARATION = "fundable_with_preparation", "Fundable with preparation"
        STRONG = "strong", "Strong"

    class Confidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="readiness_assessments"
    )
    total_score = models.PositiveSmallIntegerField()
    band = models.CharField(max_length=40, choices=Band.choices)
    component_scores = models.JSONField(default=list)
    gaps = models.JSONField(default=list)
    data_confidence = models.CharField(max_length=10, choices=Confidence.choices)
    config_version = models.CharField(max_length=20)
    computed_at = models.DateTimeField()

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-computed_at"]

    def __str__(self) -> str:
        return f"{self.total_score} ({self.band})"
