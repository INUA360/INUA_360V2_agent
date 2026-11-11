"""Generic normalizer: RawTransactionRow -> canonical NormalizedTransaction.

This layer is source-agnostic. Adding a bank statement parser later means
writing a new parser, not touching this code or the canonical schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.financials.categories import classify
from apps.ingestion.parsers.base import RawTransactionRow


@dataclass(frozen=True)
class NormalizedTransaction:
    source_ref: str
    occurred_at: datetime
    direction: str
    amount: Decimal
    balance: Decimal | None
    counterparty_text: str
    category: str
    raw_details: str


@dataclass(frozen=True)
class NormalizationIssue:
    source_ref: str
    reason: str


DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_datetime(value: str) -> datetime | None:
    text = " ".join((value or "").replace("\n", " ").split())
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            naive = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return None


def parse_amount(value: str | Decimal | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).upper().replace("KES", "").replace(",", "").replace(" ", "").strip()
    if not text or text in {"-", "--"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def normalize_row(
    row: RawTransactionRow,
) -> tuple[NormalizedTransaction | None, NormalizationIssue | None]:
    receipt = (row.receipt or "").strip()
    if not receipt:
        return None, NormalizationIssue(source_ref="", reason="missing_receipt")
    occurred_at = parse_datetime(row.completion_time)
    if occurred_at is None:
        return None, NormalizationIssue(source_ref=receipt, reason="unparseable_date")

    paid_in = row.paid_in
    withdrawn = row.withdrawn
    if paid_in is not None and paid_in > 0:
        direction = "in"
        amount = paid_in
    elif withdrawn is not None and withdrawn > 0:
        direction = "out"
        amount = withdrawn
    else:
        return None, NormalizationIssue(source_ref=receipt, reason="no_amount")

    details = " ".join((row.details or "").split())
    return (
        NormalizedTransaction(
            source_ref=receipt,
            occurred_at=occurred_at,
            direction=direction,
            amount=amount,
            balance=row.balance,
            counterparty_text=details[:255],
            category=classify(details, direction),
            raw_details=details[:2000],
        ),
        None,
    )
