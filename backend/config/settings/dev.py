"""Local development settings."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "backend"]

# Keep dev convenient but never write statement PDFs to disk.
STORAGE_BACKEND = "filesystem"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Local dev is served over http.
COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": [  # noqa: F405
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
