from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from apps.audit.services import log_event
from apps.common.tenancy import set_current_user_id
from apps.opportunities.models import Opportunity

# Merchant-data models are deliberately NOT registered. Staff must never browse
# businesses, transactions, documents, compliance records, or assessments.


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "name",
        "provider",
        "provider_type",
        "type",
        "status",
        "last_verified_at",
        "stale_badge",
        "deadline",
    )
    list_filter = ("status", "provider_type", "type", "accepts_informal")
    search_fields = ("name", "provider", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at", "stale_badge")
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "name",
                    "provider",
                    "provider_type",
                    "type",
                    "description",
                    "status",
                )
            },
        ),
        (
            "Amounts and eligibility",
            {
                "fields": (
                    "min_amount",
                    "max_amount",
                    "allowed_sectors",
                    "counties",
                    "min_months_operating",
                    "min_readiness_score",
                    "required_compliance",
                    "required_documents",
                    "accepts_informal",
                )
            },
        ),
        (
            "Application",
            {
                "fields": (
                    "application_url",
                    "deadline",
                    "source_url",
                    "last_verified_at",
                    "notes",
                )
            },
        ),
        ("Audit", {"fields": ("created_at", "updated_at", "stale_badge")}),
    )

    @admin.display(description="Freshness")
    def stale_badge(self, obj: Opportunity) -> str:
        age_days = (timezone.now() - obj.last_verified_at).days
        if age_days > 120:
            return format_html(
                '<span style="color:#b91c1c;font-weight:bold">EXPIRED ({})</span>', age_days
            )
        if age_days > 60:
            return format_html(
                '<span style="color:#b45309;font-weight:bold">STALE ({}d)</span>', age_days
            )
        return format_html('<span style="color:#15803d">OK ({}d)</span>', age_days)

    def save_model(self, request: Any, obj: Opportunity, form: Any, change: bool) -> None:
        if not obj.last_verified_at:
            messages.error(request, "last_verified_at is required.")
            return
        with transaction.atomic():
            if getattr(request.user, "is_authenticated", False):
                set_current_user_id(request.user.pk)
            super().save_model(request, obj, form, change)
            log_event(
                actor=request.user,
                business=None,
                action="opportunity.updated" if change else "opportunity.created",
                entity=f"opportunity:{obj.id}",
                metadata={"name": obj.name, "status": obj.status},
            )
