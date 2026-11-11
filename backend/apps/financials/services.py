"""Source-agnostic aggregation and descriptive metrics.

These are descriptive statistics only. Nothing here gives financial advice.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from apps.financials.models import FundingNeed, Loan, MonthlyFinancial, Transaction


@dataclass(frozen=True)
class FinancialMetrics:
    has_statement: bool
    months_of_data: int
    average_monthly_inflow: Decimal
    average_monthly_outflow: Decimal
    average_monthly_revenue: Decimal
    revenue_consistency_cv: float
    net_cash_flow_positive_ratio: float
    debt_service_ratio: float | None
    data_confidence: str
    revenue_caveat: str
    monthly: list[dict[str, Any]]


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@transaction.atomic
def recompute_monthly_financials(business: Any) -> list[MonthlyFinancial]:
    """Rebuild monthly aggregates from transactions for one business."""
    rows = (
        Transaction.objects.filter(business=business)
        .annotate(month=TruncMonth("occurred_at"))
        .values("month")
        .annotate(
            inflow=Sum("amount", filter=Q(direction=Transaction.Direction.IN)),
            outflow=Sum("amount", filter=Q(direction=Transaction.Direction.OUT)),
            txn_count=Count("id"),
        )
        .order_by("month")
    )
    MonthlyFinancial.objects.filter(business=business).delete()
    created = []
    for row in rows:
        month_value = row["month"]
        month = month_value.date() if hasattr(month_value, "date") else month_value
        if isinstance(month, date):
            month = month.replace(day=1)
        inflow = _decimal(row["inflow"])
        outflow = _decimal(row["outflow"])
        created.append(
            MonthlyFinancial(
                business=business,
                month=month,
                inflow=inflow,
                outflow=outflow,
                net=inflow - outflow,
                txn_count=row["txn_count"],
            )
        )
    if created:
        MonthlyFinancial.objects.bulk_create(created)
    return created


def delete_statement_and_aggregates(statement: Any) -> None:
    from apps.ingestion.models import Statement

    business = statement.business
    Statement.objects.filter(pk=statement.pk).delete()
    recompute_monthly_financials(business)


def compute_metrics(business: Any) -> FinancialMetrics:
    from apps.ingestion.models import Statement

    monthly = list(MonthlyFinancial.objects.filter(business=business).order_by("month"))
    has_statement = Statement.objects.filter(business=business).exists()
    monthly_payload = [
        {
            "month": row.month.isoformat(),
            "inflow": str(row.inflow),
            "outflow": str(row.outflow),
            "net": str(row.net),
            "txn_count": row.txn_count,
        }
        for row in monthly
    ]

    funding_need = FundingNeed.objects.filter(business=business).first()

    if not has_statement or not monthly:
        revenue = _decimal(getattr(funding_need, "avg_monthly_revenue", None))
        expenses = _decimal(getattr(funding_need, "avg_monthly_expenses", None))
        return FinancialMetrics(
            has_statement=False,
            months_of_data=0,
            average_monthly_inflow=revenue,
            average_monthly_outflow=expenses,
            average_monthly_revenue=revenue,
            revenue_consistency_cv=0.0,
            net_cash_flow_positive_ratio=0.0,
            debt_service_ratio=None,
            data_confidence="low",
            revenue_caveat=(
                "No statement uploaded. These figures are self-reported and receive "
                "reduced weight in the readiness score."
            ),
            monthly=[],
        )

    inflows = [float(row.inflow) for row in monthly]
    outflows = [float(row.outflow) for row in monthly]
    average_inflow = Decimal(str(statistics.mean(inflows))) if inflows else Decimal("0")
    average_outflow = Decimal(str(statistics.mean(outflows))) if outflows else Decimal("0")
    mean_inflow = statistics.mean(inflows) if inflows else 0.0
    cv = (statistics.pstdev(inflows) / mean_inflow) if mean_inflow > 0 else 1.0
    positive_ratio = sum(1 for row in monthly if row.net >= 0) / len(monthly) if monthly else 0.0

    customer_total = Transaction.objects.filter(
        business=business,
        direction=Transaction.Direction.IN,
        category="customer_payment",
    ).aggregate(total=Sum("amount"))["total"]
    total_inflow = Transaction.objects.filter(
        business=business, direction=Transaction.Direction.IN
    ).aggregate(total=Sum("amount"))["total"]
    customer_share = (
        float(_decimal(customer_total) / _decimal(total_inflow))
        if _decimal(total_inflow) > 0
        else 0.0
    )

    if customer_share >= 0.3:
        average_revenue = _decimal(customer_total) / Decimal(len(monthly))
        caveat = (
            "Average revenue counts transactions categorised as customer payments. "
            "Categorisation uses simple keyword rules and may be incomplete."
        )
    else:
        average_revenue = average_inflow
        caveat = (
            "Categorisation confidence is low, so all money in is treated as a "
            "revenue approximation. This may overstate revenue."
        )

    loan_repayments = Loan.objects.filter(business=business).aggregate(
        total=Sum("monthly_repayment")
    )["total"]
    detected_repayments = Transaction.objects.filter(
        business=business,
        direction=Transaction.Direction.OUT,
        category__in=["loan_repayment", "fuliza_repayment"],
    ).aggregate(total=Sum("amount"))["total"]
    monthly_detected = _decimal(detected_repayments) / Decimal(max(len(monthly), 1))
    monthly_loan = _decimal(loan_repayments) + monthly_detected
    dsr = float(monthly_loan / average_inflow) if average_inflow > 0 else None

    if len(monthly) >= 6 and customer_share >= 0.3:
        confidence = "high"
    elif len(monthly) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return FinancialMetrics(
        has_statement=True,
        months_of_data=len(monthly),
        average_monthly_inflow=average_inflow.quantize(Decimal("0.01")),
        average_monthly_outflow=average_outflow.quantize(Decimal("0.01")),
        average_monthly_revenue=average_revenue.quantize(Decimal("0.01")),
        revenue_consistency_cv=round(cv, 4),
        net_cash_flow_positive_ratio=round(positive_ratio, 4),
        debt_service_ratio=round(dsr, 4) if dsr is not None else None,
        data_confidence=confidence,
        revenue_caveat=caveat,
        monthly=monthly_payload,
    )


def metrics_dict(business: Any) -> dict[str, Any]:
    return asdict(compute_metrics(business))
