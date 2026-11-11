"""Consistent error envelope for every API error."""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def envelope_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    request_id = getattr(request, "request_id", "-")
    detail = response.data

    if isinstance(exc, ValidationError):
        code = "validation_error"
        message = "Some fields are invalid."
        details = detail
    else:
        code = getattr(exc, "default_code", "error")
        if isinstance(detail, dict) and "detail" in detail:
            message = str(detail["detail"])
            details = None
        elif isinstance(detail, list):
            message = "; ".join(str(item) for item in detail)
            details = detail
        else:
            message = str(detail)
            details = None

    response.data = {
        "error": {"code": code, "message": message, "details": details},
        "request_id": request_id,
    }
    return response
