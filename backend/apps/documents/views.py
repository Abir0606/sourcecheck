from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.audit import record_audit_event
from apps.common.constants import DocumentStatus
from apps.common.permissions import has_workspace_write
from apps.documents.extraction import ExtractionError, validate_upload
from apps.documents.models import Document, Passage
from apps.documents.serializers import (
    DocumentSerializer,
    DocumentStatusSerializer,
    DocumentUploadSerializer,
    PassageSerializer,
)
from apps.documents.services import create_document_from_upload
from apps.documents.tasks import process_document_task
from apps.workspaces.models import Workspace

import io


class DocumentViewSet(viewsets.GenericViewSet):
    """
    Documents are always nested under a workspace and every query is scoped to
    it. Uploads validate type/size before anything is persisted.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DocumentSerializer

    def get_workspace(self) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return Document.objects.filter(workspace=self.get_workspace()).select_related("created_by")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        role = request.query_params.get("role")
        if role in ("target", "source"):
            qs = qs.filter(role=role)
        return Response(DocumentSerializer(qs, many=True).data)

    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission to upload."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        role = serializer.validated_data["role"]

        # Pre-validate before touching storage for a fast, clear error.
        try:
            validate_upload(fileobj=io.BytesIO(uploaded.read()), filename=uploaded.name, declared_type=uploaded.content_type)
            uploaded.seek(0)
        except ExtractionError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = create_document_from_upload(
            workspace=workspace, role=role, uploaded_file=uploaded, user=request.user
        )
        process_document_task.delay(str(document.id))
        record_audit_event(
            action="document.uploaded",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="document",
            object_id=document.id,
            role=role,
            size_bytes=document.size_bytes,
        )
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        document = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(DocumentSerializer(document).data)

    def destroy(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission to delete."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        document = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        from apps.documents.deletion import purge_document

        purge_document(document)
        record_audit_event(
            action="document.deleted",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="document",
            object_id=document.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, *args, **kwargs):
        document = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(DocumentStatusSerializer(document).data)

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission to reprocess."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        document = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        document.status = DocumentStatus.UPLOADED
        document.error_code = ""
        document.error_message = ""
        document.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        process_document_task.delay(str(document.id))
        record_audit_event(
            action="document.reprocessed",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="document",
            object_id=document.id,
        )
        return Response(DocumentStatusSerializer(document).data)

    @action(detail=True, methods=["get"], url_path="passages")
    def passages(self, request, *args, **kwargs):
        document = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        qs = Passage.objects.filter(document=document).order_by("chunk_index")
        return Response(PassageSerializer(qs, many=True).data)
