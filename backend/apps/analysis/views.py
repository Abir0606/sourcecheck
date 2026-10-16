from __future__ import annotations

import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.audit import record_audit_event
from apps.common.constants import AnalysisStatus, DocumentRole
from apps.common.exceptions import FINDING_STATUS_DESCRIPTIONS
from apps.common.permissions import has_workspace_write
from apps.documents.models import Document
from apps.workspaces.models import Workspace

from .models import AnalysisJob, Finding, WritingSuggestion
from .serializers import (
    AnalysisJobSerializer,
    CreateAnalysisSerializer,
    FindingSerializer,
    FindingReviewSerializer,
    WritingSuggestionSerializer,
)


class AnalysisJobViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisJobSerializer

    def get_workspace(self) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return AnalysisJob.objects.filter(workspace=self.get_workspace()).select_related("target_document")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        target = request.query_params.get("target_document_id")
        if target:
            qs = qs.filter(target_document_id=target)
        return Response(AnalysisJobSerializer(qs, many=True).data)

    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission to run analysis."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CreateAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_id = serializer.validated_data["target_document_id"]
        idem = serializer.validated_data.get("idempotency_key", "")

        document = get_object_or_404(Document, pk=target_id, workspace=workspace)
        if document.role != DocumentRole.TARGET:
            return Response(
                {"error": {"code": "invalid_target", "message": "Selected document is not a target document."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not document.is_ready:
            return Response(
                {"error": {"code": "not_ready", "message": "The target document has not finished processing."}},
                status=status.HTTP_409_CONFLICT,
            )
        if not Document.objects.filter(
            workspace=workspace, role=DocumentRole.SOURCE, status="ready"
        ).exists():
            return Response(
                {"error": {"code": "no_sources", "message": "Upload at least one source document first."}},
                status=status.HTTP_409_CONFLICT,
            )

        if idem:
            existing = AnalysisJob.objects.filter(workspace=workspace, idempotency_key=idem).first()
            if existing:
                return Response(AnalysisJobSerializer(existing).data, status=status.HTTP_200_OK)

        job = AnalysisJob.objects.create(
            workspace=workspace,
            target_document=document,
            requested_by=request.user,
            idempotency_key=idem,
        )
        from .tasks import run_analysis_task

        async_result = run_analysis_task.delay(str(job.id))
        job.celery_task_id = async_result.id
        job.save(update_fields=["celery_task_id", "updated_at"])
        record_audit_event(
            action="analysis.requested",
            workspace=workspace,
            actor=request.user,
            request=request,
            object_type="analysis_job",
            object_id=job.id,
            target_document_id=str(document.id),
        )
        return Response(AnalysisJobSerializer(job).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(AnalysisJobSerializer(job).data)

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, *args, **kwargs):
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(AnalysisJobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        if job.status in (AnalysisStatus.QUEUED, AnalysisStatus.RUNNING):
            job.status = AnalysisStatus.CANCELLED
            job.save(update_fields=["status", "updated_at"])
            record_audit_event(
                action="analysis.cancelled", workspace=workspace, actor=request.user,
                request=request, object_type="analysis_job", object_id=job.id,
            )
        return Response(AnalysisJobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        if job.status in (AnalysisStatus.SUCCEEDED, AnalysisStatus.RUNNING):
            return Response(AnalysisJobSerializer(job).data)
        job.status = AnalysisStatus.QUEUED
        job.error_code = ""
        job.error_message = ""
        job.progress = 0
        job.save(update_fields=["status", "error_code", "error_message", "progress", "updated_at"])
        from .tasks import run_analysis_task

        run_analysis_task.delay(str(job.id))
        return Response(AnalysisJobSerializer(job).data)

    @action(detail=True, methods=["get"])
    def findings(self, request, *args, **kwargs):
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        qs = Finding.objects.filter(analysis_job=job).select_related("target_passage__document")
        qs = self._filter_findings(qs, request.query_params)

        summary = self._summary(job)
        page = self.paginate_queryset(qs)
        if page is not None:
            data = FindingSerializer(page, many=True).data
            response = self.get_paginated_response(data)
            response.data["summary"] = summary
            return response
        return Response({"results": FindingSerializer(qs, many=True).data, "summary": summary})

    def _filter_findings(self, qs, params):
        if status := params.get("status"):
            qs = qs.filter(status=status)
        if review_state := params.get("review_state"):
            qs = qs.filter(review_state=review_state)
        if min_conf := params.get("min_confidence"):
            try:
                qs = qs.filter(confidence__gte=float(min_conf))
            except ValueError:
                pass
        if (nhr := params.get("needs_human_review")) is not None:
            qs = qs.filter(needs_human_review=nhr.lower() in ("1", "true", "yes"))
        return qs

    def _summary(self, job) -> dict:
        from django.db.models import Count

        rows = Finding.objects.filter(analysis_job=job).values("status").annotate(n=Count("id"))
        counts = {r["status"]: r["n"] for r in rows}
        return {
            "total": sum(counts.values()),
            "by_status": counts,
            "needs_human_review": Finding.objects.filter(analysis_job=job, needs_human_review=True).count(),
        }

    @action(detail=True, methods=["get"], url_path="writing")
    def writing(self, request, *args, **kwargs):
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        qs = WritingSuggestion.objects.filter(analysis_job=job).select_related("target_passage")
        return Response(WritingSuggestionSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def report(self, request, *args, **kwargs):
        job = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        findings = list(
            Finding.objects.filter(analysis_job=job)
            .select_related("target_passage__document")
            .prefetch_related("evidence__source_document")
        )
        # NOTE: query param is `export` (not `format`) because DRF reserves
        # `format` for renderer/content negotiation overrides.
        fmt = request.query_params.get("export", "json")
        record_audit_event(
            action="report.exported", workspace=job.workspace, actor=request.user,
            request=request, object_type="analysis_job", object_id=job.id, format=fmt,
        )
        if fmt == "csv":
            return self._csv_report(job, findings)
        return Response(self._json_report(job, findings))

    def _json_report(self, job, findings) -> dict:
        return {
            "generated_at": job.updated_at.isoformat(),
            "disclaimer": (
                "This report compares statements in the target document against only the "
                "source documents uploaded to this workspace. 'Unsupported by uploaded "
                "sources' means the statement was not found in those sources; it does not "
                "mean the statement is false. This is not a plagiarism report."
            ),
            "analysis": AnalysisJobSerializer(job).data,
            "status_descriptions": FINDING_STATUS_DESCRIPTIONS,
            "findings": FindingSerializer(findings, many=True).data,
            "writing_suggestions": WritingSuggestionSerializer(
                WritingSuggestion.objects.filter(analysis_job=job), many=True
            ).data,
        }

    def _csv_report(self, job, findings) -> HttpResponse:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["status", "confidence", "needs_human_review", "review_state",
             "target_page", "claim", "explanation", "evidence_file", "evidence_page", "evidence_snippet"]
        )
        for f in findings:
            ev = list(f.evidence.all())
            if not ev:
                writer.writerow([
                    f.get_status_display(), f.confidence, f.needs_human_review, f.review_state,
                    f.target_passage.page_number or "", f.claim_text, f.explanation, "", "", "",
                ])
            for e in ev:
                writer.writerow([
                    f.get_status_display(), f.confidence, f.needs_human_review, f.review_state,
                    f.target_passage.page_number or "", f.claim_text, f.explanation,
                    e.source_document.original_filename, e.page_number or "", e.snippet,
                ])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="analysis-{job.id}.csv"'
        return response


class FindingViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FindingSerializer

    def get_workspace(self) -> Workspace:
        return get_object_or_404(
            Workspace.objects.filter(memberships__user=self.request.user).distinct(),
            pk=self.kwargs["workspace_pk"],
        )

    def get_queryset(self):
        return Finding.objects.filter(workspace=self.get_workspace()).select_related(
            "target_passage__document"
        ).prefetch_related("evidence__source_document")

    def retrieve(self, request, *args, **kwargs):
        finding = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return Response(FindingSerializer(finding).data)

    def partial_update(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        if not has_workspace_write(request.user, workspace):
            return Response(
                {"error": {"code": "forbidden", "message": "You do not have permission to review."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        finding = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        serializer = FindingReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        finding.mark_reviewed(
            state=serializer.validated_data["review_state"],
            user=request.user,
            note=serializer.validated_data.get("review_note", ""),
        )
        record_audit_event(
            action="finding.reviewed", workspace=workspace, actor=request.user,
            request=request, object_type="finding", object_id=finding.id,
            review_state=finding.review_state,
        )
        return Response(FindingSerializer(finding).data)
