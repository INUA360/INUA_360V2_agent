"""Synthetic encrypted M-Pesa statements for tests and local development.

TODO(owner): obtain 3–5 redacted real statements (personal and till/paybill)
before launch. These synthetic statements must not be treated as proof that the
parser handles every real Safaricom layout.

Never put real PII in this repository.
"""

from __future__ import annotations

import io
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

import pikepdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

Layout = Literal["a", "b"]


@dataclass
class SyntheticRow:
    receipt: str
    occurred_at: datetime
    details: str
    status: str
    paid_in: Decimal | None
    withdrawn: Decimal | None
    balance: Decimal


def _money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:,.2f}"


def _build_rows(months: int, rows_per_month: int, seed: int) -> list[SyntheticRow]:
    rng = random.Random(seed)
    rows: list[SyntheticRow] = []
    balance = Decimal("50000.00")
    start = datetime(2024, 1, 1, 8, 0)
    counter = 0

    customer_texts = [
        "Payment from customer INUA RETAIL",
        "Customer M-PESA Payment order 4821",
        "Till payment from customer Wanjiku",
        "Invoice payment from customer ABC Traders",
    ]
    out_texts = [
        "Send to supplier Nairobi Wholesalers",
        "Transfer to savings account",
        "Pay Bill KPLC prepaid token",
        "Buy goods from Mama Mboga Supplies",
    ]
    small_out_texts = [
        "M-PESA charge",
        "Fuliza repayment",
        "Airtime purchase",
        "Withdrawal at agent",
        "Mshwari loan repayment",
    ]

    for month_index in range(months):
        month_start = start + timedelta(days=31 * month_index)
        revenue_scale = Decimal(str(1.0 + (month_index % 4) * 0.08))
        for row_index in range(rows_per_month):
            counter += 1
            receipt = f"Q{chr(65 + (counter % 26))}{counter:09d}"[:12]
            day_offset = min(27, int(row_index * 27 / max(rows_per_month, 1)))
            occurred = month_start + timedelta(
                days=day_offset, hours=rng.randint(0, 9), minutes=rng.randint(0, 59)
            )
            roll = rng.random()
            if roll < 0.55:
                amount = Decimal(rng.randint(1500, 25000)).quantize(Decimal("0.01")) * (
                    revenue_scale
                )
                paid_in = amount.quantize(Decimal("0.01"))
                withdrawn = None
                details = rng.choice(customer_texts)
            elif roll < 0.75:
                amount = Decimal(rng.randint(500, 12000)).quantize(Decimal("0.01"))
                paid_in = None
                withdrawn = amount
                details = rng.choice(out_texts)
            elif roll < 0.92:
                amount = Decimal(rng.randint(10, 300)).quantize(Decimal("0.01"))
                paid_in = None
                withdrawn = amount
                details = rng.choice(small_out_texts)
            else:
                amount = Decimal(rng.randint(1000, 5000)).quantize(Decimal("0.01"))
                paid_in = None
                withdrawn = amount
                details = "Withdrawal at agent"

            if paid_in is not None:
                balance += paid_in
            if withdrawn is not None:
                balance -= withdrawn
            if balance < 0:
                balance += Decimal("50000.00")

            rows.append(
                SyntheticRow(
                    receipt=receipt,
                    occurred_at=occurred,
                    details=details,
                    status="Completed",
                    paid_in=paid_in,
                    withdrawn=withdrawn,
                    balance=balance.quantize(Decimal("0.01")),
                )
            )
    return rows


def _table_data(rows: list[SyntheticRow], layout: Layout) -> list[list[Any]]:
    styles = getSampleStyleSheet()
    detail_style = styles["BodyText"].clone("details", fontSize=6.5, leading=7.5)
    if layout == "a":
        header = [
            "Receipt No.",
            "Completion Time",
            "Details",
            "Transaction Status",
            "Paid In",
            "Withdrawn",
            "Balance",
        ]
    else:
        header = [
            "Completion Time",
            "Receipt No",
            "Details",
            "Status",
            "Money In",
            "Money Out",
            "Balance",
        ]

    data: list[list[Any]] = [header]
    for row in rows:
        if layout == "a":
            cells: list[object] = [
                row.receipt,
                row.occurred_at.strftime("%d/%m/%y %H:%M"),
                Paragraph(row.details, detail_style),
                row.status,
                _money(row.paid_in),
                _money(row.withdrawn),
                _money(row.balance),
            ]
        else:
            cells = [
                row.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                row.receipt,
                Paragraph(row.details, detail_style),
                row.status,
                _money(row.paid_in),
                _money(row.withdrawn),
                _money(row.balance),
            ]
        data.append(cells)
    return data


def _build_pdf(rows: list[SyntheticRow], layout: Layout, title: str) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="Inua360 synthetic fixture",
    )
    styles = getSampleStyleSheet()
    story: list[object] = [
        Paragraph("M-PESA STATEMENT (SYNTHETIC TEST FIXTURE)", styles["Heading2"]),
        Paragraph(
            "This document is generated for parser tests. It contains no real customer data.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]
    data = _table_data(rows, layout)
    col_widths = [23 * mm, 26 * mm, 58 * mm, 22 * mm, 18 * mm, 20 * mm, 20 * mm]
    table = LongTable(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("LEADING", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9AA7B8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return output.getvalue()


def generate_statement_bytes(
    *,
    months: int = 12,
    rows_per_month: int = 30,
    password: str = "test-password",
    layout: Layout = "a",
    seed: int = 42,
    pad_bytes: int = 0,
) -> bytes:
    """Return an encrypted, multi-page PDF statement in memory."""
    rows = _build_rows(months, rows_per_month, seed)
    raw = _build_pdf(rows, layout, title=f"Synthetic M-Pesa {layout}")
    pdf = pikepdf.open(io.BytesIO(raw))
    if pad_bytes:
        attachment = pikepdf.AttachedFileSpec(
            pdf,
            os.urandom(pad_bytes),
            filename="synthetic-appendix.bin",  # type: ignore[call-arg]
            description="Padding so upload-path tests exceed the 2.5 MB spool threshold.",
        )
        pdf.attachments["synthetic-appendix.bin"] = attachment
    output = io.BytesIO()
    pdf.save(
        output,
        encryption=pikepdf.Encryption(owner=password, user=password, R=6),
        compress_streams=True,
    )
    pdf.close()
    return output.getvalue()
