"""Test settings. Real PostgreSQL is required (RLS cannot be tested on SQLite)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False
TESTING = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="inua360-test-media-"))
STORAGE_BACKEND = "filesystem"

# Throttling is exercised explicitly in tests via override_settings.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "auth": "1000/min",
        "register": "1000/hour",
        "statement_parse": "1000/hour",
        "readiness_recompute": "1000/hour",
    },
}

PENDING_STATEMENT_TTL_MINUTES = 30
COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
