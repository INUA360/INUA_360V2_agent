from __future__ import annotations

from typing import Any

from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView, no_content
from apps.common.pagination import StandardPagination
from apps.ingestion.models import Statement
from apps.ingestion.serializers import StatementParseSerializer, StatementSerializer
from apps.ingestion.services import confirm_statement, delete_statement, parse_statement


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class StatementParseView(LatestBusinessMixin, MerchantAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "statement_parse"

    def post(self, request: Any) -> Response:
        business = self.get_business()
        serializer = StatementParseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending = parse_statement(
            business,
            serializer.validated_data["file"],
            serializer.validated_data.get("password"),
        )
        return Response(
            {
                "pending_id": str(pending.id),
                "summary": pending.summary,
                "expires_at": pending.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class StatementConfirmView(MerchantAPIView):
    def post(self, request: Any, pending_id: Any) -> Response:
        statement, duplicates = confirm_statement(request.user, pending_id)
        payload = StatementSerializer(statement).data
        payload["duplicate_rows_skipped"] = duplicates
        return Response(payload, status=status.HTTP_201_CREATED)


class StatementListView(MerchantAPIView):
    def get(self, request: Any) -> Response:
        queryset = Statement.objects.for_user(request.user).order_by("-created_at")  # type: ignore[attr-defined]
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(StatementSerializer(page, many=True).data)
        return Response(StatementSerializer(queryset, many=True).data)


class StatementDetailView(MerchantAPIView):
    def delete(self, request: Any, pk: Any) -> Response:
        delete_statement(request.user, pk)
        return no_content()
