"""Local development settings. Safe defaults; no Azure required."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Serve media/static simply in dev; WhiteNoise still works.
CORS_ALLOW_ALL_ORIGINS = True
