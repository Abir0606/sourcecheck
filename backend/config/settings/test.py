"""Settings for the automated test suite. Runs tasks inline (no broker needed)."""
from .local import *  # noqa: F401,F403

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGE_BACKEND = "local"
ANALYZER_BACKEND = "rules"
OCR_PROVIDER = "none"

# Faster, isolated test runs.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
