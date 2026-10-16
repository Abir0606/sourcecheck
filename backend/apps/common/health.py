from __future__ import annotations

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(_request):
    """Liveness: process is up. Cheap; no dependencies checked."""
    return JsonResponse({"status": "ok", "service": "sourcecheck-api"})


@require_GET
def readyz(_request):
    """Readiness: dependencies reachable. Used by Container Apps probes."""
    checks: dict[str, str] = {}
    ok = True

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks["database"] = "ok"
    except Exception:  # pragma: no cover - depends on runtime env
        checks["database"] = "unavailable"
        ok = False

    try:
        from .adapters import get_storage

        get_storage().healthcheck()
        checks["storage"] = "ok"
    except Exception:  # pragma: no cover
        checks["storage"] = "unavailable"
        ok = False

    return JsonResponse({"status": "ok" if ok else "degraded", "checks": checks}, status=200 if ok else 503)
