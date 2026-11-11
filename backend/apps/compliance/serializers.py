from __future__ import annotations

import re
from typing import Any

from rest_framework import serializers

from apps.compliance.models import BusinessCompliance

KRA_PIN_RE = re.compile(r"^[AP]\d{9}[A-Z]$")


class ComplianceSerializer(serializers.ModelSerializer[BusinessCompliance]):
    tcc_effective_status = serializers.CharField(read_only=True)
    permit_effective_status = serializers.CharField(read_only=True)
    verification = serializers.SerializerMethodField()
    tcc_days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = BusinessCompliance
        fields = [
            "id",
            "registration_status",
            "registration_number",
            "kra_pin",
            "pin_status",
            "tcc_status",
            "tcc_expiry",
            "tcc_effective_status",
            "tcc_days_remaining",
            "county_permit_number",
            "county_permit_expiry",
            "permit_effective_status",
            "other_permits",
            "verification",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "tcc_effective_status",
            "tcc_days_remaining",
            "permit_effective_status",
            "verification",
            "created_at",
            "updated_at",
        ]

    def get_verification(self, obj: BusinessCompliance) -> dict[str, str]:
        return {
            "registration": obj.registration_verification,
            "kra_pin": obj.kra_pin_verification,
            "tcc": obj.tcc_verification,
            "county_permit": obj.permit_verification,
        }

    def validate_kra_pin(self, value: str) -> str:
        value = (value or "").strip().upper()
        if value and not KRA_PIN_RE.match(value):
            raise serializers.ValidationError("Enter a valid KRA PIN, for example P123456789A.")
        return value

    def validate_other_permits(self, value: Any) -> Any:
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Other permits must be a list.")
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each permit must be an object.")
            cleaned.append(
                {
                    "name": str(item.get("name", ""))[:120],
                    "expiry": item.get("expiry") or None,
                }
            )
        return cleaned

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        tcc_status = attrs.get("tcc_status", getattr(self.instance, "tcc_status", None))
        tcc_expiry = attrs.get("tcc_expiry", getattr(self.instance, "tcc_expiry", None))
        if tcc_status == BusinessCompliance.TccStatus.VALID and not tcc_expiry:
            raise serializers.ValidationError({"tcc_expiry": "A valid TCC needs an expiry date."})
        return attrs
