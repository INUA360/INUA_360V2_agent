"""Append-only audit events. Never log secrets or raw financial rows."""

from __future__ import annotations

from typing import Any

from apps.audit.models import AuditLog

SENSITIVE_METADATA_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "file",
    "pdf",
    "statement_text",
    "national_id",
    "id_number",
}


def _clean(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_METADATA_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[str(key)] = value
        elif isinstance(value, dict):
            cleaned[str(key)] = _clean(value)
        elif isinstance(value, (list, tuple)):
            cleaned[str(key)] = [
                item for item in value if isinstance(item, (str, int, float, bool))
            ]
    return cleaned


def log_event(
    *,
    actor: Any = None,
    business: Any = None,
    action: str,
    entity: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        business=business,
        action=action,
        entity=entity,
        metadata=_clean(metadata),
    )
