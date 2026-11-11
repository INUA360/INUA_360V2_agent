from __future__ import annotations

from rest_framework import serializers

from apps.financials.models import FundingNeed, Loan, MonthlyFinancial, Transaction


class TransactionSerializer(serializers.ModelSerializer[Transaction]):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "source",
            "source_ref",
            "occurred_at",
            "direction",
            "amount",
            "balance",
            "counterparty_text",
            "category",
        ]


class MonthlyFinancialSerializer(serializers.ModelSerializer[MonthlyFinancial]):
    class Meta:
        model = MonthlyFinancial
        fields = ["month", "inflow", "outflow", "net", "txn_count"]


class LoanSerializer(serializers.ModelSerializer[Loan]):
    class Meta:
        model = Loan
        fields = [
            "id",
            "lender",
            "outstanding",
            "monthly_repayment",
            "ends_on",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_outstanding(self, value):  # type: ignore[no-untyped-def]
        if value < 0:
            raise serializers.ValidationError("Outstanding balance cannot be negative.")
        return value

    def validate_monthly_repayment(self, value):  # type: ignore[no-untyped-def]
        if value < 0:
            raise serializers.ValidationError("Monthly repayment cannot be negative.")
        return value


class FundingNeedSerializer(serializers.ModelSerializer[FundingNeed]):
    class Meta:
        model = FundingNeed
        fields = [
            "id",
            "amount",
            "purpose",
            "description",
            "timeframe",
            "avg_monthly_revenue",
            "avg_monthly_expenses",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value):  # type: ignore[no-untyped-def]
        if value <= 0:
            raise serializers.ValidationError("Enter the amount you need.")
        return value
