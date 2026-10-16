from __future__ import annotations

from .models import AuditEvent


def record_audit_event(
    *,
    action: str,
    workspace=None,
    actor=None,
    request=None,
    object_type: str = "",
    object_id: str = "",
    **metadata,
) -> AuditEvent:
    """Create an audit event. `metadata` must be free of document text."""
    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR"
        )
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]
    return AuditEvent.objects.create(
        workspace=workspace,
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        ip=ip,
        user_agent=user_agent,
        metadata=metadata or {},
    )
