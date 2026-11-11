from __future__ import annotations

from typing import Any

from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTCookieAuthentication(JWTAuthentication):
    """JWT authentication via `Authorization: Bearer` (and optional access cookie).

    The refresh token lives in an httpOnly cookie; the short-lived access token
    is returned in the login/refresh response body. We still accept an access
    cookie for future same-origin deployments.
    """

    def authenticate(self, request: Any) -> Any:
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)
        access = request.COOKIES.get("inua_access")
        if not access:
            return None
        validated = self.get_validated_token(access)
        return self.get_user(validated), validated
