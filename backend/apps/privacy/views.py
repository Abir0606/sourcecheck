from __future__ import annotations

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import AnalysisJob, Finding
from apps.common.adapters import get_storage
from apps.common.audit import record_audit_event
from apps.common.permissions import has_workspace_admin, has_workspace_write
from apps.documents.models import Document
from apps.workspaces.models import Workspace

from .models import DeletionRequest, ExportJob, RequestStatus
from .serializers import DeletionRequestSerializer, ExportJobSerializer


class PrivacyOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get_workspace(self, request, workspace_pk) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=request.user).distinct(), pk=workspace_pk
        )

    def get(self, request, workspace_pk):
        workspace = self.get_workspace(request, workspace_pk)
        return Response(
            {
                "workspace": {
                    "id": str(workspace.id),
                    "name": workspace.name,
                    "data_region": workspace.data_region,
                    "retention_days": workspace.retention_days,
                },
                "data_inventory": {
                    "documents": Document.objects.filter(workspace=workspace).count(),
                    "analyses": AnalysisJob.objects.filter(workspace=workspace).count(),
                    "findings": Finding.objects.filter(workspace=workspace).count(),
                },
                "notes": (
                    "Retention, lawful basis, and transfer mechanisms are controller/DPO "
                    "decisions, not application settings. See docs/privacy/decisions-needed.md."
                ),
            }
        )


class ExportViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExportJobSerializer

    def get_workspace(self) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return ExportJob.objects.filter(workspace=self.get_workspace())

    def list(self, request, *args, **kwargs):
        return Response(ExportJobSerializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        export = ExportJob.objects.create(workspace=workspace, requested_by=request.user)
        from .tasks import process_export_task

        process_export_task.delay(str(export.id))
        record_audit_event(
            action="export.requested", workspace=workspace, actor=request.user,
            request=request, object_type="export_job", object_id=export.id,
        )
        return Response(ExportJobSerializer(export).data, status=status.HTTP_202_ACCEPTED)

    def retrieve(self, request, *args, **kwargs):
        export = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(ExportJobSerializer(export).data)

    @action(detail=True, methods=["get"])
    def download(self, request, *args, **kwargs):
        export = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        if export.status != RequestStatus.COMPLETED or not export.storage_key or export.is_expired:
            return Response(
                {"error": {"code": "not_available", "message": "This export is not available."}},
                status=status.HTTP_409_CONFLICT,
            )
        storage = get_storage()
        with storage.open(export.storage_key) as fh:
            data = fh.read()
        record_audit_event(
            action="export.downloaded", workspace=export.workspace, actor=request.user,
            request=request, object_type="export_job", object_id=export.id,
        )
        response = StreamingHttpResponse(iter([data]), content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="export-{export.id}.json"'
        return response


class DeletionRequestViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DeletionRequestSerializer

    def get_workspace(self) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return DeletionRequest.objects.filter(workspace=self.get_workspace())

    def list(self, request, *args, **kwargs):
        return Response(DeletionRequestSerializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_admin(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "Admin role required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deletion = DeletionRequest.objects.create(
            workspace=workspace,
            scope=serializer.validated_data["scope"],
            requested_by=request.user,
        )
        from .tasks import process_deletion_task

        process_deletion_task.delay(str(deletion.id))
        record_audit_event(
            action="deletion.requested", workspace=workspace, actor=request.user,
            request=request, object_type="deletion_request", object_id=deletion.id,
            scope=deletion.scope,
        )
        return Response(DeletionRequestSerializer(deletion).data, status=status.HTTP_202_ACCEPTED)

    def retrieve(self, request, *args, **kwargs):
        deletion = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(DeletionRequestSerializer(deletion).data)
