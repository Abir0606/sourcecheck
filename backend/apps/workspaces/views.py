from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.audit import record_audit_event
from apps.common.permissions import has_workspace_admin, has_workspace_write

from .models import Membership, Workspace
from .serializers import (
    MembershipSerializer,
    WorkspaceSerializer,
    WorkspaceSettingsSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    Workspace CRUD. Querysets are always filtered to the caller's memberships,
    so a user can never enumerate or touch another tenant's workspace.
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return Workspace.objects.all()
        return Workspace.objects.filter(memberships__user=user).distinct()

    def perform_create(self, serializer):
        workspace = serializer.save()
        record_audit_event(
            action="workspace.created",
            workspace=workspace,
            actor=self.request.user,
            request=self.request,
            object_type="workspace",
            object_id=workspace.id,
        )

    @action(detail=True, methods=["get", "patch"], url_path="settings", url_name="settings")
    def workspace_settings(self, request, pk=None):
        workspace = self.get_object()
        if request.method == "PATCH" and not has_workspace_admin(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "Admin role required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method == "GET":
            return Response(WorkspaceSettingsSerializer(workspace).data)
        serializer = WorkspaceSettingsSerializer(workspace, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit_event(
            action="workspace.settings_updated",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="workspace",
            object_id=workspace.id,
            fields=sorted(serializer.validated_data.keys()),
        )
        return Response(serializer.data)


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_workspace(self):
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Membership.objects.all()
        return Membership.objects.filter(workspace__memberships__user=self.request.user)

    def _require_admin(self, workspace):
        return has_workspace_admin(self.request.user, workspace) or has_workspace_write(
            self.request.user, workspace
        )

    def list(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        qs = Membership.objects.filter(workspace=workspace).select_related("user")
        return Response(MembershipSerializer(qs, many=True).data)

    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_admin(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "Admin role required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = MembershipSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        raw_user = request.data.get("user")
        user_id = raw_user.get("id") if isinstance(raw_user, dict) else raw_user
        from django.contrib.auth import get_user_model

        user = get_object_or_404(get_user_model(), pk=user_id)
        membership, created = Membership.objects.update_or_create(
            workspace=workspace, user=user,
            defaults={"role": serializer.validated_data["role"]},
        )
        record_audit_event(
            action="membership.changed",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="membership",
            object_id=membership.id,
            role=membership.role,
        )
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_admin(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "Admin role required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_object_or_404(Membership, workspace=workspace, pk=kwargs["pk"])
        if membership.role == "owner" and Membership.objects.filter(
            workspace=workspace, role="owner"
        ).count() == 1:
            return Response(
                {"error": {"code": "conflict", "message": "A workspace must keep at least one owner."}},
                status=status.HTTP_409_CONFLICT,
            )
        record_audit_event(
            action="membership.removed",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="membership",
            object_id=membership.id,
        )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
