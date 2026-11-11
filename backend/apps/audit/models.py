from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import UUIDModel


class AuditLog(UUIDModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    business = models.ForeignKey(
        "businesses.Business",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["business", "created_at"])]

    def __str__(self) -> str:
        return f"{self.action} {self.entity}"
