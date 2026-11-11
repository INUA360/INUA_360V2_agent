"""M-Pesa PDF parser.

Columns are detected from each page's header row, never from fixed positions.
This tolerates the common personal, till, and paybill statement variants.
"""

from __future__ import annotations

import io
import re
from typing import Any, BinaryIO

import pdfplumber
import pikepdf

from apps.ingestion.normalizer import parse_amount
from apps.ingestion.parsers.base import (
    ParseResult,
    RawTransactionRow,
    SkippedRow,
    StatementFormatError,
    StatementPasswordError,
)

RECEIPT_RE = re.compile(r"^[A-Z0-9]{6,32}$")
FOOTER_HINTS = ("page ", "statement", "generated on", "total", "opening balance", "closing balance")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def _label(value: str) -> str:
    return re.sub(r"[^a-z0-9 +/]", "", _cell(value).lower()).strip()


def _detect_columns(row: list[str]) -> dict[str, int] | None:
    columns: dict[str, int] = {}
    for index, raw in enumerate(row):
        label = _label(raw)
        if not label:
            continue
        if "receipt" in label or label in {"receipt no", "txn id", "transaction id"}:
            columns["receipt"] = index
        elif "completion" in label or ("date" in label and "time" in label):
            columns["time"] = index
        elif "details" in label or "description" in label or "narrative" in label:
            columns["details"] = index
        elif "status" in label:
            columns["status"] = index
        elif "paid in" in label or "money in" in label or label == "in":
            columns["paid_in"] = index
        elif "withdraw" in label or "money out" in label or label == "out":
            columns["withdrawn"] = index
        elif "balance" in label:
            columns["balance"] = index
    if (
        "receipt" in columns
        and "time" in columns
        and ("paid_in" in columns or "withdrawn" in columns)
    ):
        return columns
    return None


def _looks_like_header(row: list[str]) -> bool:
    return _detect_columns(row) is not None


def _receipt_is_valid(receipt: str) -> bool:
    return bool(RECEIPT_RE.match(receipt.replace(" ", "")))


class MpesaPdfParser:
    """Parse a (possibly encrypted) M-Pesa PDF entirely in memory."""

    def parse(self, file: BinaryIO, secret: str | None) -> ParseResult:
        decrypted = self._decrypt(file, secret)
        result = ParseResult()
        pending_rows: list[dict[str, Any]] = []

        try:
            with pdfplumber.open(decrypted) as pdf:
                result.pages = len(pdf.pages)
                for page_number, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables() or []
                    page_found_header = False
                    for table in tables:
                        columns: dict[str, int] | None = None
                        for raw_row in table:
                            row = [_cell(cell) for cell in raw_row]
                            if not any(row):
                                continue
                            if _looks_like_header(row):
                                columns = _detect_columns(row)
                                page_found_header = True
                                if "money in" in " ".join(row).lower():
                                    result.layout_variant = "layout_b"
                                elif result.layout_variant == "unknown":
                                    result.layout_variant = "layout_a"
                                continue
                            if columns is None:
                                continue
                            self._consume_row(row, columns, page_number, pending_rows, result)
                    if not page_found_header and not tables:
                        result.warnings.append(f"No table found on page {page_number}.")
        except StatementPasswordError:
            raise
        except Exception as exc:  # noqa: BLE001 - sanitized boundary
            raise StatementFormatError(
                "The statement could not be read as a PDF. Try re-downloading it."
            ) from exc

        rows: list[RawTransactionRow] = []
        for item in pending_rows:
            rows.append(
                RawTransactionRow(
                    receipt=str(item.get("receipt", "")),
                    completion_time=str(item.get("time", "")),
                    details=str(item.get("details", "")),
                    status=str(item.get("status", "")),
                    paid_in=parse_amount(item.get("paid_in")),
                    withdrawn=parse_amount(item.get("withdrawn")),
                    balance=parse_amount(item.get("balance")),
                )
            )
        result.rows = rows
        if not rows:
            result.warnings.append(
                "No transactions were detected. The statement layout may not be supported yet."
            )
        return result

    def _decrypt(self, file: BinaryIO, secret: str | None) -> io.BytesIO:
        file.seek(0)
        header = file.read(5)
        file.seek(0)
        if header != b"%PDF-":
            raise StatementFormatError("The uploaded file is not a PDF.")
        try:
            if secret:
                pdf = pikepdf.open(file, password=secret)
            else:
                pdf = pikepdf.open(file)
        except pikepdf.PasswordError as exc:
            raise StatementPasswordError(
                "Could not open the statement. Check the password and try again."
            ) from exc
        except pikepdf.PdfError as exc:
            raise StatementFormatError(
                "The statement could not be opened. The file may be corrupted."
            ) from exc

        output = io.BytesIO()
        try:
            with pdf:
                pdf.save(output)
        except pikepdf.PdfError as exc:
            raise StatementFormatError(
                "The statement could not be decrypted. Check the file and password."
            ) from exc
        output.seek(0)
        return output

    def _consume_row(
        self,
        row: list[str],
        columns: dict[str, int],
        page_number: int,
        pending_rows: list[dict[str, Any]],
        result: ParseResult,
    ) -> None:
        def value(key: str) -> str:
            index = columns.get(key)
            if index is None or index >= len(row):
                return ""
            return row[index]

        joined = " ".join(row).lower()
        receipt = value("receipt").replace(" ", "")
        details = value("details")
        has_amount = bool(value("paid_in") or value("withdrawn") or value("balance"))

        if not receipt and not has_amount:
            if details and pending_rows:
                pending_rows[-1]["details"] = (
                    f"{pending_rows[-1].get('details', '')} {details}".strip()
                )
                return
            if details:
                result.skipped.append(
                    SkippedRow(page=page_number, reason="orphan_details", excerpt=details[:80])
                )
            return

        if receipt and not _receipt_is_valid(receipt):
            reason = "summary_or_footer_row"
            if not any(hint in joined for hint in FOOTER_HINTS):
                reason = "invalid_receipt"
            result.skipped.append(SkippedRow(page=page_number, reason=reason, excerpt=receipt[:40]))
            return

        status = value("status")
        if status and status.lower() not in {"completed", "complete", "success", "successful"}:
            result.skipped.append(
                SkippedRow(
                    page=page_number,
                    reason=f"status_{status.lower().replace(' ', '_')}",
                    excerpt=receipt[:40],
                )
            )
            return

        pending_rows.append(
            {
                "receipt": receipt,
                "time": value("time"),
                "details": details,
                "status": status,
                "paid_in": value("paid_in"),
                "withdrawn": value("withdrawn"),
                "balance": value("balance"),
            }
        )
