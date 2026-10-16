"""
Base Django settings for SourceCheck.

All environment-specific values come from environment variables so the same
image runs locally and on Azure. Nothing here contacts Azure at import time.
"""
from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    EMBEDDING_DIM=(int, 384),
    DEFAULT_RETENTION_DAYS=(int, 0),
    LOG_DOCUMENT_TEXT=(bool, False),
    MAX_UPLOAD_BYTES=(int, 25 * 1024 * 1024),
)

# Load a .env file if present (local development convenience only).
_env_file = BASE_DIR.parent / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.workspaces",
    "apps.documents",
    "apps.analysis",
    "apps.privacy",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database (PostgreSQL + pgvector) ---------------------------------------
DATABASES = {"default": env.db("DATABASE_URL", default="postgres://sourcecheck:sourcecheck@localhost:5433/sourcecheck")}
DATABASES["default"]["CONN_MAX_AGE"] = 60

# --- Auth --------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # SPA reads csrftoken cookie to set X-CSRFToken
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- i18n / tz ---------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static ------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "120/min",
        "uploads": "30/hour",
        "analyses": "20/hour",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

# --- CORS (local dev: SPA origin differs from API origin) --------------------
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True

# --- Celery ------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_TASK_DEFAULT_RETRY_DELAY = 30
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"

# --- Application / adapter configuration ------------------------------------
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
LOCAL_STORAGE_DIR = env("LOCAL_STORAGE_DIR", default=str(BASE_DIR / "local_storage"))
VECTOR_STORE = env("VECTOR_STORE", default="pgvector")
OCR_PROVIDER = env("OCR_PROVIDER", default="none")
TESSERACT_CMD = env("TESSERACT_CMD", default="tesseract")
ANALYZER_BACKEND = env("ANALYZER_BACKEND", default="rules")

AZURE_STORAGE_ACCOUNT_URL = env("AZURE_STORAGE_ACCOUNT_URL", default="")
AZURE_STORAGE_CONTAINER = env("AZURE_STORAGE_CONTAINER", default="documents")
AZURE_STORAGE_AUTH = env("AZURE_STORAGE_AUTH", default="managed_identity")

AI_BASE_URL = env("AI_BASE_URL", default="")
AI_API_KEY = env("AI_API_KEY", default="")
AI_MODEL = env("AI_MODEL", default="")
AZURE_OPENAI_ENDPOINT = env("AZURE_OPENAI_ENDPOINT", default="")
AZURE_OPENAI_DEPLOYMENT = env("AZURE_OPENAI_DEPLOYMENT", default="")
AZURE_OPENAI_API_VERSION = env("AZURE_OPENAI_API_VERSION", default="2024-06-01")

SECRET_PROVIDER = env("SECRET_PROVIDER", default="env")
AZURE_KEY_VAULT_URL = env("AZURE_KEY_VAULT_URL", default="")

# --- Analysis tuning ---------------------------------------------------------
EMBEDDING_DIM = env("EMBEDDING_DIM")
PASSAGE_TARGET_CHARS = 1200
PASSAGE_OVERLAP_CHARS = 200
CANDIDATE_EVIDENCE_LIMIT = 12
MAX_UPLOAD_BYTES = env("MAX_UPLOAD_BYTES")
ALLOWED_UPLOAD_EXTENSIONS = [
    ".pdf", ".docx", ".txt", ".md", ".rtf", ".odt", ".xlsx", ".csv",
]

# --- Privacy -----------------------------------------------------------------
DATA_REGION = env("DATA_REGION", default="local")
DEFAULT_RETENTION_DAYS = env("DEFAULT_RETENTION_DAYS")
LOG_DOCUMENT_TEXT = env("LOG_DOCUMENT_TEXT")

# --- Logging (privacy-preserving: never log document text) --------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.common.logging.JsonFormatter",
        },
    },
    "filters": {
        "request_context": {"()": "apps.common.logging.RequestContextFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
