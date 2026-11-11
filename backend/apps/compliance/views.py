from __future__ import annotations

from typing import Any

from rest_framework.response import Response

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView
from apps.compliance.models import BusinessCompliance
from apps.compliance.serializers import ComplianceSerializer
from apps.compliance.verifiers import get_verifier


class ComplianceView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        compliance = (
            BusinessCompliance.objects.for_user(request.user)
            .filter(  # type: ignore[attr-defined]
                business=business
            )
            .first()
        )
        if compliance is None:
            return Response(
                {
                    "id": None,
                    "registration_status": "unknown",
                    "registration_number": "",
                    "kra_pin": "",
                    "pin_status": "unknown",
                    "tcc_status": "none",
                    "tcc_expiry": None,
                    "tcc_effective_status": "none",
                    "tcc_days_remaining": None,
                    "county_permit_number": "",
                    "county_permit_expiry": None,
                    "permit_effective_status": "none",
                    "other_permits": [],
                    "verification": {
                        "registration": "self_reported",
                        "kra_pin": "self_reported",
                        "tcc": "self_reported",
                        "county_permit": "self_reported",
                    },
                }
            )
        return Response(ComplianceSerializer(compliance).data)

    def put(self, request: Any) -> Response:
        business = self.get_business()
        compliance = (
            BusinessCompliance.objects.for_user(request.user)
            .filter(  # type: ignore[attr-defined]
                business=business
            )
            .first()
        )
        if compliance is None:
            serializer = ComplianceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            compliance = serializer.save(business=business)
            created = True
        else:
            serializer = ComplianceSerializer(compliance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            compliance = serializer.save()
            created = False

        verifier = get_verifier()
        update_fields = []
        if compliance.kra_pin:
            pin_result = verifier.verify_pin(compliance.kra_pin)
            compliance.kra_pin_verification = pin_result.status
            tcc_result = verifier.verify_tcc(compliance.kra_pin)
            compliance.tcc_verification = tcc_result.status
            update_fields.extend(["kra_pin_verification", "tcc_verification"])
        if update_fields:
            compliance.save(update_fields=update_fields + ["updated_at"])

        from apps.audit.services import log_event
        from apps.businesses.onboarding import advance_onboarding_step
        from apps.readiness.services import recompute_readiness

        advance_onboarding_step(request.user, 3)
        log_event(
            actor=request.user,
            business=business,
            action="compliance.created" if created else "compliance.updated",
            entity=f"compliance:{compliance.id}",
        )
        recompute_readiness(business)
        return Response(ComplianceSerializer(compliance).data)
