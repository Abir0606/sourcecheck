"""
Workspace-scoped authorization.

Every API view and background task must resolve the caller's membership in the
target workspace. These helpers are the single place that logic lives.
"""
from __future__ import annotations

from rest_framework import permissions

from .constants import ADMIN_ROLES, WRITE_ROLES, WorkspaceRole


def roles_for(user, workspace) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    if getattr(user, "is_superuser", False):
        return {WorkspaceRole.OWNER}
    from apps.workspaces.models import Membership

    return set(
        Membership.objects.filter(workspace=workspace, user=user).values_list(
            "role", flat=True
        )
    )


def has_workspace_access(user, workspace) -> bool:
    return bool(roles_for(user, workspace))


def has_workspace_write(user, workspace) -> bool:
    return bool(roles_for(user, workspace) & WRITE_ROLES)


def has_workspace_admin(user, workspace) -> bool:
    return bool(roles_for(user, workspace) & ADMIN_ROLES)


class WorkspaceAccessPermission(permissions.BasePermission):
    """The object (or view) must expose `.workspace`; caller must be a member."""

    read_roles = None  # any member may read by default
    write_roles = WRITE_ROLES

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", None)
        if workspace is None:
            return False
        roles = roles_for(request.user, workspace)
        if request.method in permissions.SAFE_METHODS:
            return bool(roles)
        return bool(roles & self.write_roles)
