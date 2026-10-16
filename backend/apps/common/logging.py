"""Structured, privacy-preserving logging.

Rules:
- Never log document text or extracted passages.
- Log identifiers, counts, timing, and status only.
- A per-request id is attached for correlation.
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
workspace_id_var: ContextVar[str | None] = ContextVar("workspace_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.workspace_id = workspace_id_var.get()
        record.user_id = user_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "workspace_id": getattr(record, "workspace_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)
