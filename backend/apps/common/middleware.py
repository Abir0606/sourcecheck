from __future__ import annotations

import uuid

from .logging import request_id_var, user_id_var


class RequestContextMiddleware:
    """Attaches a request id for log correlation. Does not log request bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token_r = request_id_var.set(rid)
        token_u = None
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            token_u = user_id_var.set(str(request.user.pk))
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token_r)
            if token_u is not None:
                user_id_var.reset(token_u)
        response["X-Request-ID"] = rid
        return response
