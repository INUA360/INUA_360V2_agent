"""Parse → preview → confirm flow. No PDF or password is ever persisted."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.ingestion.models import PendingStatement, Statement
from apps.ingestion.normalizer import NormalizedTransaction, normalize_row
from apps.ingestion.parsers.base import (
    ParseResult,
    StatementParseError,
    StatementPasswordError,
)
from apps.ingestion.parsers.mpesa_pdf import MpesaPdfParser

PARSERS = {Statement.Source.MPESA_PDF: MpesaPdfParser}


def _serialize_row(row: NormalizedTransaction) -> dict[str, Any]:
    return {
        "source_ref": row.source_ref,
        "occurred_at": row.occurred_at.isoformat(),
        "direction": row.direction,
        "amount": str(row.amount),
        "balance": str(row.balance) if row.balance is not None else None,
        "counterparty_text": row.counterparty_text,
        "category": row.category,
        "raw_details": row.raw_details,
    }


def _parse_result(
    result: ParseResult, normalized: list[NormalizedTransaction], issues: list[Any]
) -> dict[str, Any]:
    total_candidates = len(result.rows) + len(result.skipped)
    reasons = Counter(issue.reason for issue in issues)
    reasons.update(issue.reason for issue in result.skipped)
    known = sum(1 for row in normalized if row.category != "uncategorized")
    known_share = (known / len(normalized)) if normalized else 0.0
    if not normalized:
        confidence = "low"
    elif total_candidates and len(normalized) / total_candidates >= 0.98 and known_share >= 0.5:
        confidence = "high"
    elif len(normalized) / max(total_candidates, 1) >= 0.85:
        confidence = "medium"
    else:
        confidence = "low"
    dates = [row.occurred_at.date() for row in normalized]
    return {
        "rows_parsed": len(normalized),
        "rows_skipped": sum(reasons.values()),
        "rows_seen": total_candidates,
        "skipped_reasons": [
            {"reason": reason, "count": count} for reason, count in reasons.most_common()
        ],
        "pages": result.pages,
        "layout_variant": result.layout_variant,
        "warnings": result.warnings,
        "categorisation_confidence": round(known_share, 3),
        "confidence": confidence,
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "preview": [_serialize_row(row) for row in normalized[:10]],
        "caveat": (
            "This is a rule-based parse preview, not a verified bank record. "
            "Check the period and row count before confirming."
        ),
    }


def parse_statement(business: Any, uploaded_file: Any, password: str | None) -> PendingStatement:
    """Parse in memory and hold normalized rows for confirmation."""
    size = getattr(uploaded_file, "size", 0)
    if size > settings.STATEMENT_MAX_BYTES:
        raise ValidationError({"file": "Statement must be 10 MB or smaller."})
    if size == 0:
        raise ValidationError({"file": "The uploaded file is empty."})

    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b"%PDF-":
        raise ValidationError({"file": "Upload the statement PDF from M-Pesa."})

    parser = PARSERS[Statement.Source.MPESA_PDF]()
    try:
        result = parser.parse(uploaded_file, password or None)
    except StatementPasswordError as exc:
        raise ValidationError(
            {"password": "Could not open the statement. Check the password and try again."}
        ) from exc
    except StatementParseError as exc:
        raise ValidationError({"file": str(exc)}) from exc
    finally:
        # The file handle goes out of scope; Django keeps it in memory only.
        uploaded_file.seek(0)

    normalized: list[NormalizedTransaction] = []
    issues = []
    seen: set[str] = set()
    for raw in result.rows:
        row, issue = normalize_row(raw)
        if issue:
            issues.append(issue)
            continue
        assert row is not None
        if row.source_ref in seen:
            issues.append(type("Issue", (), {"reason": "duplicate_receipt"})())
            continue
        seen.add(row.source_ref)
        normalized.append(row)

    summary = _parse_result(result, normalized, issues)
    if not normalized:
        summary["warnings"].append(
            "We could not find any transactions. Check that you uploaded the statement "
            "PDF itself, not a screenshot."
        )
        raise ValidationError(
            {
                "file": "No transactions could be read from this statement.",
                "parse_summary": summary,
            }
        )

    PendingStatement.purge_expired()
    pending = PendingStatement.objects.create(
        business=business,
        source=Statement.Source.MPESA_PDF,
        normalized_rows=[_serialize_row(row) for row in normalized],
        summary=summary,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        expires_at=timezone.now() + timedelta(minutes=settings.PENDING_STATEMENT_TTL_MINUTES),
    )
    return cast(PendingStatement, pending)


@transaction.atomic
def confirm_statement(user: Any, pending_id: Any) -> tuple[Statement, int]:
    business = user.business
    pending = (
        PendingStatement.objects.for_user(user)  # type: ignore[attr-defined]
        .select_for_update()
        .filter(pk=pending_id)
        .first()
    )
    if pending is None:
        raise ValidationError({"detail": "This parse preview was not found."})
    if pending.is_expired:
        pending.delete()
        raise ValidationError(
            {"detail": "This preview expired. Parse the statement again to continue."}
        )

    business = pending.business
    rows = pending.normalized_rows or []
    if not rows:
        pending.delete()
        raise ValidationError({"detail": "This preview has no transactions."})

    existing_refs = set(TransactionRefQuery(business=pending.business, source=pending.source))
    unique: list[dict[str, Any]] = []
    for row in rows:
        ref = str(row["source_ref"])
        if ref in existing_refs:
            continue
        existing_refs.add(ref)
        unique.append(row)

    statement = Statement.objects.create(
        business=pending.business,
        source=pending.source,
        period_start=pending.period_start,
        period_end=pending.period_end,
        row_count=len(unique),
        warnings=pending.summary.get("warnings", []),
        parse_metadata={
            "confidence": pending.summary.get("confidence"),
            "pages": pending.summary.get("pages"),
            "layout_variant": pending.summary.get("layout_variant"),
            "rows_skipped": pending.summary.get("rows_skipped"),
            "skipped_reasons": pending.summary.get("skipped_reasons", []),
        },
    )

    from apps.financials.models import Transaction

    Transaction.objects.bulk_create(
        [
            Transaction(
                business=pending.business,
                statement=statement,
                source=pending.source,
                source_ref=str(row["source_ref"]),
                occurred_at=row["occurred_at"],
                direction=row["direction"],
                amount=Decimal(str(row["amount"])),
                balance=Decimal(str(row["balance"])) if row.get("balance") else None,
                counterparty_text=str(row.get("counterparty_text", ""))[:255],
                category=str(row.get("category", "uncategorized")),
                raw_details=str(row.get("raw_details", ""))[:2000],
            )
            for row in unique
        ]
    )

    pending.delete()

    from apps.audit.services import log_event
    from apps.businesses.onboarding import advance_onboarding_step
    from apps.financials.services import recompute_monthly_financials
    from apps.opportunities.services import recompute_matches
    from apps.readiness.services import recompute_readiness

    recompute_monthly_financials(business)
    advance_onboarding_step(user, 3)
    log_event(
        actor=user,
        business=pending.business,
        action="statement.confirmed",
        entity=f"statement:{statement.id}",
        metadata={"row_count": statement.row_count},
    )
    recompute_readiness(business)
    recompute_matches(business)
    return statement, len(rows) - len(unique)


class TransactionRefQuery:
    """Small iterable that avoids importing Transaction at module import time."""

    def __init__(self, business: Any, source: str) -> None:
        self.business = business
        self.source = source

    def __iter__(self):  # type: ignore[no-untyped-def]
        from apps.financials.models import Transaction

        yield from Transaction.objects.filter(
            business=self.business, source=self.source
        ).values_list("source_ref", flat=True)


@transaction.atomic
def delete_statement(user: Any, statement_id: Any) -> None:
    statement = (
        Statement.objects.for_user(user)  # type: ignore[attr-defined]
        .filter(pk=statement_id)
        .first()
    )
    if statement is None:
        raise ValidationError({"detail": "Statement not found."})
    business = statement.business
    statement.delete()

    from apps.audit.services import log_event
    from apps.financials.services import recompute_monthly_financials
    from apps.opportunities.services import recompute_matches
    from apps.readiness.services import recompute_readiness

    recompute_monthly_financials(business)
    log_event(
        actor=user,
        business=business,
        action="statement.deleted",
        entity=f"statement:{statement_id}",
    )
    recompute_readiness(business)
    recompute_matches(business)
