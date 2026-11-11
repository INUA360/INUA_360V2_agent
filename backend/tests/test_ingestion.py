from __future__ import annotations

import io
from decimal import Decimal

import pytest

from apps.ingestion.generator import generate_statement_bytes
from apps.ingestion.normalizer import normalize_row, parse_amount
from apps.ingestion.parsers.base import (
    RawTransactionRow,
    StatementPasswordError,
)
from apps.ingestion.parsers.mpesa_pdf import MpesaPdfParser


@pytest.mark.parametrize("layout", ["a", "b"])
def test_parser_reads_synthetic_encrypted_statement(layout: str) -> None:
    raw = generate_statement_bytes(
        months=2, rows_per_month=4, password="correct-horse", layout=layout
    )
    result = MpesaPdfParser().parse(io.BytesIO(raw), "correct-horse")
    assert result.rows
    assert result.pages >= 1
    assert result.layout_variant in {"layout_a", "layout_b"}
    assert all(row.receipt for row in result.rows)
    assert all((row.paid_in or 0) > 0 or (row.withdrawn or 0) > 0 for row in result.rows)


def test_parser_rejects_wrong_password_without_leaking_it() -> None:
    raw = generate_statement_bytes(months=1, rows_per_month=3, password="right-password")
    with pytest.raises(StatementPasswordError) as excinfo:
        MpesaPdfParser().parse(io.BytesIO(raw), "wrong-password")
    assert "wrong-password" not in str(excinfo.value)


def test_parser_rejects_non_pdf() -> None:
    from apps.ingestion.parsers.base import StatementFormatError

    with pytest.raises(StatementFormatError):
        MpesaPdfParser().parse(io.BytesIO(b"not a pdf"), None)


def test_normalizer_parses_dates_amounts_and_direction() -> None:
    row = RawTransactionRow(
        receipt="ABC123XYZ",
        completion_time="2025-01-15 10:30:00",
        details="Received from JANE DOE",
        status="Completed",
        paid_in=Decimal("1250.50"),
        withdrawn=None,
        balance=Decimal("5000.00"),
    )
    normalized, issue = normalize_row(row)
    assert issue is None
    assert normalized is not None
    assert normalized.direction == "in"
    assert normalized.amount == Decimal("1250.50")
    assert normalized.category == "transfer"


def test_parse_amount_accepts_formatted_strings() -> None:
    assert parse_amount("KES 12,345.67") == Decimal("12345.67")
    assert parse_amount("") is None
    assert parse_amount(None) is None
