from __future__ import annotations

from typing import Any

from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.businesses.models import Business
from apps.businesses.onboarding import advance_onboarding_step
from apps.businesses.serializers import BusinessSerializer
from apps.common.mixins import MerchantAPIView


class BusinessView(MerchantAPIView):
    """GET/PUT the merchant's business profile (PUT upserts for onboarding)."""

    def get(self, request: Any) -> Response:
        business = Business.objects.for_user(request.user).first()  # type: ignore[attr-defined]
        if business is None:
            raise NotFound("No business profile yet.")
        return Response(BusinessSerializer(business).data)

    def put(self, request: Any) -> Response:
        business = Business.objects.for_user(request.user).first()  # type: ignore[attr-defined]
        if business is None:
            serializer = BusinessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            business = serializer.save(owner=request.user)
            created = True
        else:
            serializer = BusinessSerializer(business, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            business = serializer.save()
            created = False

        advance_onboarding_step(request.user, 2)
        from apps.audit.services import log_event

        log_event(
            actor=request.user,
            business=business,
            action="business.created" if created else "business.updated",
            entity=f"business:{business.id}",
        )
        from apps.readiness.services import recompute_readiness

        recompute_readiness(business)
        return Response(BusinessSerializer(business).data)
