from __future__ import annotations

import uuid
from typing import Any

from apps.common.logging import request_id_ctx


class RequestIDMiddleware:
    """Attach a request id to the request and to log records."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming if incoming and len(incoming) <= 128 else str(uuid.uuid4())
        request.request_id = request_id
        token = request_id_ctx.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_ctx.reset(token)
        response["X-Request-ID"] = request_id
        return response
