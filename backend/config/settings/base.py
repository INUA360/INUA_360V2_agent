"""Base Django settings shared by all environments.

All thresholds/weights live in YAML config files (readiness, categories), not here.
Secrets and deployment-specific values come from the environment.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-only-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "storages",
    # Local
    "apps.common",
    "apps.accounts",
    "apps.businesses",
    "apps.compliance",
    "apps.ingestion",
    "apps.financials",
    "apps.documents",
    "apps.readiness",
    "apps.opportunities",
    "apps.audit",
]

MIDDLEWARE = [
    "apps.common.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database. default = runtime role (inua_app). migrator = migrations role.
# Both point at the same physical database; the migrator alias is used by the
# migration/bootstrap tooling and the test harness only.
# ---------------------------------------------------------------------------
DB_SSLMODE = os.environ.get("DB_SSLMODE", "prefer")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "inua360")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": os.environ.get("DB_USER", "inua_app"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "inua_app_dev_password"),
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "OPTIONS": {"sslmode": DB_SSLMODE},
        "ATOMIC_REQUESTS": True,
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    },
    "migrator": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": os.environ.get("DB_MIGRATOR_USER", "inua_migrator"),
        "PASSWORD": os.environ.get("DB_MIGRATOR_PASSWORD", "inua_migrator_dev_password"),
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "OPTIONS": {"sslmode": DB_SSLMODE},
        "ATOMIC_REQUESTS": False,
        "DISABLE_SERVER_SIDE_CURSORS": True,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Uploads: memory only. Statements are capped at 10 MB; keep these just above
# that so Django can never spool the encrypted PDF to a temp file.
# ---------------------------------------------------------------------------
STATEMENT_MAX_BYTES = int(os.environ.get("STATEMENT_MAX_BYTES", str(10 * 1024 * 1024)))
DOCUMENT_MAX_BYTES = int(os.environ.get("DOCUMENT_MAX_BYTES", str(10 * 1024 * 1024)))
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]
FILE_UPLOAD_MAX_MEMORY_SIZE = STATEMENT_MAX_BYTES + (2 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = STATEMENT_MAX_BYTES + (2 * 1024 * 1024)
PENDING_STATEMENT_TTL_MINUTES = int(os.environ.get("PENDING_STATEMENT_TTL_MINUTES", "30"))

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.accounts.authentication.JWTCookieAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.common.exceptions.envelope_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/min",
        "register": "10/hour",
        "statement_parse": "10/hour",
        "readiness_recompute": "30/hour",
    },
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Inua360 API",
    "DESCRIPTION": (
        "Financial passport and funding-readiness API. The readiness score is a "
        "transparent, rule-based rubric; it is not a credit score and does not "
        "guarantee funding."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Views on this API are plain APIViews with envelope payloads, so drf-spectacular
# cannot infer a serializer for them. The schema is intentionally partial in
# Milestone 1; do not fail `check --deploy` for that documentation-only warning.
SILENCED_SYSTEM_CHECKS = ["drf_spectacular.W001", "drf_spectacular.W002"]

# ---------------------------------------------------------------------------
# Cookies / CORS
# ---------------------------------------------------------------------------
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_ORIGIN)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", FRONTEND_ORIGIN)
COOKIE_SECURE = env_bool("COOKIE_SECURE", False)
REFRESH_COOKIE_NAME = "inua_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "Lax")
COOKIE_DOMAIN = os.environ.get("CSRF_COOKIE_DOMAIN") or None
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Storage (private bucket). Local dev uses MinIO; prod uses Supabase Storage S3.
# ---------------------------------------------------------------------------
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "filesystem")
if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": os.environ.get("S3_ACCESS_KEY_ID"),
                "secret_key": os.environ.get("S3_SECRET_ACCESS_KEY"),
                "bucket_name": os.environ.get("S3_BUCKET", "inua360-private"),
                "endpoint_url": os.environ.get("S3_ENDPOINT_URL"),
                "region_name": os.environ.get("S3_REGION", "us-east-1"),
                "addressing_style": os.environ.get("S3_ADDRESSING_STYLE", "path"),
                "signature_version": "s3v4",
                "default_acl": None,
                "querystring_auth": True,
                "file_overwrite": False,
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
STORAGE_SIGNED_URL_TTL_SECONDS = 300

# ---------------------------------------------------------------------------
# Compliance verifier (interface; self-reported implementation in MVP)
# ---------------------------------------------------------------------------
COMPLIANCE_VERIFIER = os.environ.get(
    "COMPLIANCE_VERIFIER", "apps.compliance.verifiers.SelfReportedVerifier"
)

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@inua360.example")

# ---------------------------------------------------------------------------
# Logging: structured-ish JSON with redaction of secrets/statement content.
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.common.logging.JsonFormatter"},
        "plain": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "filters": {
        "redact": {"()": "apps.common.logging.SensitiveDataFilter"},
        "request_id": {"()": "apps.common.logging.RequestIDFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["redact", "request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "inua360": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Security defaults (prod settings tighten further)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_SECURE = COOKIE_SECURE
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
