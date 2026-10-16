"""
Export and deletion flows. These cover originals (blobs), extracted text,
passages/embeddings (search data), and analysis results. The retention schedule
and lawful basis are controller decisions — see docs/privacy/.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import timedelta

from django.utils import timezone

from apps.analysis.models import Finding, AnalysisJob, WritingSuggestion
from apps.common.adapters import get_storage
from apps.documents.deletion import purge_workspace_data
from apps.documents.models import Document

from .models import DeletionRequest, DeletionScope, ExportJob, RequestStatus

logger = logging.getLogger("apps.privacy")

EXPORT_TTL_HOURS = 24


def build_workspace_export(workspace) -> dict:
    documents = []
    for doc in Document.objects.filter(workspace=workspace).prefetch_related("pages"):
        documents.append(
            {
                "id": str(doc.id),
                "role": doc.role,
                "filename": doc.original_filename,
                "content_type": doc.content_type,
                "size_bytes": doc.size_bytes,
                "sha256": doc.sha256,
                "status": doc.status,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat(),
                "pages": [
                    {"page_number": p.page_number, "text": p.text} for p in doc.pages.all()
                ],
            }
        )

    analyses = []
    for job in AnalysisJob.objects.filter(workspace=workspace):
        findings = []
        for f in Finding.objects.filter(analysis_job=job).prefetch_related("evidence__source_document"):
            findings.append(
                {
                    "status": f.status,
                    "claim_text": f.claim_text,
                    "explanation": f.explanation,
                    "confidence": f.confidence,
                    "needs_human_review": f.needs_human_review,
                    "review_state": f.review_state,
                    "review_note": f.review_note,
                    "evidence": [
                        {
                            "filename": e.source_document.original_filename,
                            "page_number": e.page_number,
                            "snippet": e.snippet,
                            "score": e.score,
                        }
                        for e in f.evidence.all()
                    ],
                }
            )
        analyses.append(
            {
                "id": str(job.id),
                "target_document_id": str(job.target_document_id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "findings": findings,
                "writing_suggestions": list(
                    WritingSuggestion.objects.filter(analysis_job=job).values(
                        "category", "severity", "message", "suggestion"
                    )
                ),
            }
        )

    return {
        "exported_at": timezone.now().isoformat(),
        "data_region": workspace.data_region,
        "retention_days": workspace.retention_days,
        "workspace": {"id": str(workspace.id), "name": workspace.name, "slug": workspace.slug},
        "documents": documents,
        "analyses": analyses,
    }


def process_export(export_job_id) -> str:
    export_job = ExportJob.objects.select_related("workspace").get(pk=export_job_id)
    export_job.status = RequestStatus.RUNNING
    export_job.save(update_fields=["status", "updated_at"])
    try:
        payload = build_workspace_export(export_job.workspace)
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        key = f"workspaces/{export_job.workspace_id}/exports/{export_job.id}.json"
        get_storage().save(key, io.BytesIO(data))
        export_job.storage_key = key
        export_job.size_bytes = len(data)
        export_job.status = RequestStatus.COMPLETED
        export_job.completed_at = timezone.now()
        export_job.expires_at = timezone.now() + timedelta(hours=EXPORT_TTL_HOURS)
        export_job.save(
            update_fields=["storage_key", "size_bytes", "status", "completed_at", "expires_at", "updated_at"]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("export.failed", exc_info=exc)
        export_job.status = RequestStatus.FAILED
        export_job.error_message = "Export failed."
        export_job.save(update_fields=["status", "error_message", "updated_at"])
    return export_job.status


def process_deletion(deletion_id) -> str:
    deletion = DeletionRequest.objects.select_related("workspace").get(pk=deletion_id)
    deletion.status = RequestStatus.RUNNING
    deletion.save(update_fields=["status", "updated_at"])
    try:
        if deletion.scope == DeletionScope.ANALYSIS:
            workspace = deletion.workspace
            result = {
                "findings": Finding.objects.filter(workspace=workspace).count(),
                "analyses": AnalysisJob.objects.filter(workspace=workspace).count(),
            }
            AnalysisJob.objects.filter(workspace=workspace).delete()
        else:
            result = purge_workspace_data(deletion.workspace)
        deletion.complete(result)
        logger.info(
            "deletion.completed",
            extra={"context": {"deletion_id": str(deletion.id), "scope": deletion.scope}},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("deletion.failed", exc_info=exc)
        deletion.status = RequestStatus.FAILED
        deletion.error_message = "Deletion failed."
        deletion.save(update_fields=["status", "error_message", "updated_at"])
    return deletion.status
