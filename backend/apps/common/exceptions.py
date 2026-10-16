from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .constants import FINDING_STATUS_DESCRIPTIONS

logger = logging.getLogger("apps.errors")


def api_exception_handler(exc, context):
    """Consistent error envelope; log without leaking document content."""
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(detail, dict) and "error" in detail:
        return response

    code = getattr(exc, "default_code", "error")
    message = detail if isinstance(detail, str) else "Request could not be processed."
    response.data = {"error": {"code": code, "message": message, "detail": detail}}
    return response


__all__ = ["api_exception_handler", "FINDING_STATUS_DESCRIPTIONS"]
