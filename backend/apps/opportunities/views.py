from __future__ import annotations

from typing import Any

from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView
from apps.opportunities.models import Opportunity, OpportunityMatch
from apps.opportunities.serializers import (
    MatchStateSerializer,
    OpportunityMatchSerializer,
    OpportunitySerializer,
)
from apps.opportunities.services import checklist_for, list_matches


class MatchListView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        include_dismissed = request.query_params.get("include_dismissed") == "true"
        rows = list_matches(business, include_dismissed=include_dismissed)
        return Response(OpportunityMatchSerializer(rows, many=True).data)


class MatchDetailView(MerchantAPIView):
    def patch(self, request: Any, pk: Any) -> Response:
        match_row = (
            OpportunityMatch.objects.for_user(request.user)  # type: ignore[attr-defined]
            .select_related("opportunity")
            .filter(pk=pk)
            .first()
        )
        if match_row is None:
            raise NotFound("Not found.")
        self.check_object_permissions(request, match_row)
        serializer = MatchStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        match_row.state = serializer.validated_data["state"]
        match_row.save(update_fields=["state", "updated_at"])
        return Response(OpportunityMatchSerializer(match_row).data)


class OpportunityDetailView(MerchantAPIView):
    def get(self, request: Any, pk: Any) -> Response:
        opportunity = Opportunity.objects.filter(pk=pk).first()
        if opportunity is None:
            raise NotFound("Not found.")
        return Response(OpportunitySerializer(opportunity).data)


class OpportunityChecklistView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any, pk: Any) -> Response:
        business = self.get_business()
        opportunity = Opportunity.objects.filter(pk=pk).first()
        if opportunity is None:
            raise NotFound("Not found.")
        return Response(checklist_for(business, opportunity))
