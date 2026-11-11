"""Production settings. DEBUG must stay off."""

from __future__ import annotations

from typing import Any

from .base import *  # noqa: F403

DEBUG = False

if SECRET_KEY == "unsafe-dev-only-secret-key-change-me":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]  # noqa: F405
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production")

COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(__import__("os").environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Analytics/Sentry must never receive statement content or PII.
if SENTRY_DSN:  # noqa: F405
    import sentry_sdk  # type: ignore[import-not-found]
    from sentry_sdk.integrations.django import DjangoIntegration  # type: ignore[import-not-found]

    def _scrub(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        request = event.get("request", {})
        request.pop("data", None)
        request.pop("cookies", None)
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration()],
        send_default_pii=False,
        before_send=_scrub,
        environment=__import__("os").environ.get("SENTRY_ENVIRONMENT", "production"),
    )
