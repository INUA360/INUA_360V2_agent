from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import LatestBusinessMixin, MerchantAPIView, no_content
from apps.common.pagination import StandardPagination
from apps.common.permissions import IsBusinessOwner, IsMerchant
from apps.financials.models import FundingNeed, Loan, MonthlyFinancial
from apps.financials.serializers import (
    FundingNeedSerializer,
    LoanSerializer,
    MonthlyFinancialSerializer,
)
from apps.financials.services import compute_metrics


class FinancialSummaryView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        metrics = compute_metrics(business)
        return Response(
            {
                "has_statement": metrics.has_statement,
                "months_of_data": metrics.months_of_data,
                "average_monthly_inflow": str(metrics.average_monthly_inflow),
                "average_monthly_outflow": str(metrics.average_monthly_outflow),
                "average_monthly_revenue": str(metrics.average_monthly_revenue),
                "revenue_consistency_cv": metrics.revenue_consistency_cv,
                "net_cash_flow_positive_ratio": metrics.net_cash_flow_positive_ratio,
                "debt_service_ratio": metrics.debt_service_ratio,
                "data_confidence": metrics.data_confidence,
                "revenue_caveat": metrics.revenue_caveat,
            }
        )


class MonthlyFinancialView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        rows = MonthlyFinancial.objects.for_user(request.user).filter(  # type: ignore[attr-defined]
            business=business
        )
        return Response(MonthlyFinancialSerializer(rows, many=True).data)


class LoanListCreateView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        rows = Loan.objects.for_user(request.user).filter(business=business)  # type: ignore[attr-defined]
        paginator = StandardPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(LoanSerializer(page, many=True).data)
        return Response(LoanSerializer(rows, many=True).data)

    def post(self, request: Any) -> Response:
        business = self.get_business()
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = serializer.save(business=business)
        self._recompute(request.user, business, "loan.created", loan)
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)

    def _recompute(self, user: Any, business: Any, action: str, loan: Loan) -> None:
        from apps.audit.services import log_event
        from apps.opportunities.services import recompute_matches
        from apps.readiness.services import recompute_readiness

        log_event(
            actor=user,
            business=business,
            action=action,
            entity=f"loan:{loan.id}",
        )
        recompute_readiness(business)
        recompute_matches(business)


class LoanDetailView(MerchantAPIView):
    permission_classes = [IsAuthenticated, IsMerchant, IsBusinessOwner]

    def _get(self, request: Any, pk: Any) -> Loan:
        loan = (
            Loan.objects.for_user(request.user)  # type: ignore[attr-defined]
            .filter(pk=pk)
            .first()
        )
        if loan is None:
            raise NotFound("Not found.")
        self.check_object_permissions(request, loan)
        return cast(Loan, loan)

    def put(self, request: Any, pk: Any) -> Response:
        loan = self._get(request, pk)
        serializer = LoanSerializer(loan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        loan = serializer.save()
        self._recompute(request.user, loan)
        return Response(LoanSerializer(loan).data)

    def delete(self, request: Any, pk: Any) -> Response:
        loan = self._get(request, pk)
        business = loan.business
        loan.delete()
        self._recompute(request.user, business, "loan.deleted", pk)
        return no_content()

    def _recompute(
        self,
        user: Any,
        loan_or_business: Any,
        action: str = "loan.updated",
        pk: Any = None,
    ) -> None:
        from apps.audit.services import log_event
        from apps.opportunities.services import recompute_matches
        from apps.readiness.services import recompute_readiness

        business = getattr(loan_or_business, "business", loan_or_business)
        log_event(
            actor=user,
            business=business,
            action=action,
            entity=f"loan:{pk or getattr(loan_or_business, 'id', '')}",
        )
        recompute_readiness(business)
        recompute_matches(business)


class FundingNeedView(LatestBusinessMixin, MerchantAPIView):
    def get(self, request: Any) -> Response:
        business = self.get_business()
        funding_need = (
            FundingNeed.objects.for_user(request.user)
            .filter(  # type: ignore[attr-defined]
                business=business
            )
            .first()
        )
        if funding_need is None:
            raise NotFound("No funding need set yet.")
        return Response(FundingNeedSerializer(funding_need).data)

    def put(self, request: Any) -> Response:
        business = self.get_business()
        funding_need = (
            FundingNeed.objects.for_user(request.user)
            .filter(  # type: ignore[attr-defined]
                business=business
            )
            .first()
        )
        if funding_need is None:
            serializer = FundingNeedSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            funding_need = serializer.save(business=business)
        else:
            serializer = FundingNeedSerializer(funding_need, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            funding_need = serializer.save()

        from apps.audit.services import log_event
        from apps.financials.services import recompute_monthly_financials
        from apps.opportunities.services import recompute_matches
        from apps.readiness.services import recompute_readiness

        recompute_monthly_financials(business)
        log_event(
            actor=request.user,
            business=business,
            action="funding_need.updated",
            entity=f"funding_need:{funding_need.id}",
        )
        recompute_readiness(business)
        recompute_matches(business)
        return Response(FundingNeedSerializer(funding_need).data)
