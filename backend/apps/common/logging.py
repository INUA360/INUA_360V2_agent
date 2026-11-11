"""Logging filters/formatters.

Two guarantees:
- A request id appears on every log line.
- Passwords, tokens, statement file contents and decrypted payloads can never
  be written to logs, even if a caller accidentally passes them as extras.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

SENSITIVE_KEYS = {
    "password",
    "secret",
    "authorization",
    "access",
    "access_token",
    "refresh",
    "refresh_token",
    "token",
    "file",
    "statement",
    "decrypted",
    "raw_details",
    "national_id",
    "id_number",
    "pin",
}

_REDACTION = "[REDACTED]"
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(password|secret|token|authorization|national_id|id_number)\b\s*[=:]\s*(\S+)"
)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (_REDACTION if str(key).lower() in SENSITIVE_KEYS else redact_value(val))
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    return value


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _BEARER_RE.sub(r"\1[REDACTED]", record.msg)
            record.msg = _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}={_REDACTION}", record.msg)
        for key in list(record.__dict__):
            if key.lower() in SENSITIVE_KEYS:
                record.__dict__[key] = _REDACTION
        return True


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = request_id_ctx.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Small dependency-free JSON formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = {}
        for key, value in record.__dict__.items():
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "request_id",
                "taskName",
            }:
                continue
            if key.startswith("_"):
                continue
            extra[key] = value
        if extra:
            payload["extra"] = redact_value(extra)
        return json.dumps(payload, default=str)
