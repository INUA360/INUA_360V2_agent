from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer[Business]):
    years_operating = serializers.FloatField(read_only=True)
    onboarding_percent = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "trading_name",
            "sector",
            "what_they_sell",
            "county",
            "town",
            "started_on",
            "years_operating",
            "structure",
            "employee_band",
            "owner_name",
            "owner_phone",
            "onboarding_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "years_operating",
            "onboarding_percent",
            "created_at",
            "updated_at",
        ]

    def get_onboarding_percent(self, obj: Business) -> int:
        from apps.businesses.onboarding import onboarding_percent

        return onboarding_percent(obj.owner)

    def validate_started_on(self, value):  # type: ignore[no-untyped-def]
        if value > timezone.localdate():
            raise serializers.ValidationError("Start date cannot be in the future.")
        return value
