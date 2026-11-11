from __future__ import annotations

from typing import Any

from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView
from apps.readiness.models import ReadinessAssessment
from apps.readiness.serializers import ReadinessAssessmentSerializer
from apps.readiness.services import latest_assessment, recompute_readiness


def _payload(assessment: ReadinessAssessment, history: list[ReadinessAssessment]) -> dict[str, Any]:
    from apps.readiness.engine import load_config

    return {
        "latest": ReadinessAssessmentSerializer(assessment).data,
        "history": ReadinessAssessmentSerializer(history, many=True).data,
        "disclaimer": str(load_config()["notes"]["disclaimer"]).strip(),
        "score_is": "rule_based_rubric_not_credit_score",
    }


class ReadinessView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        assessment = latest_assessment(business)
        if assessment is None:
            assessment = recompute_readiness(business)
        history = ReadinessAssessment.objects.filter(business=business).order_by("-computed_at")[
            :20
        ]
        return Response(_payload(assessment, list(history)))


class ReadinessRecomputeView(LatestBusinessMixin, MerchantAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "readiness_recompute"

    def post(self, request: Any) -> Response:
        business = self.get_business()
        assessment = recompute_readiness(business)
        history = ReadinessAssessment.objects.filter(business=business).order_by("-computed_at")[
            :20
        ]
        return Response(_payload(assessment, list(history)))
