"""
Analysis orchestration. This is the single place that:
  1. retrieves evidence,
  2. asks the analyzer, and
  3. VALIDATES every evidence id before persisting anything.

A returned evidence id is accepted only if it (a) was in the candidate set
retrieved for that claim and (b) resolves to a Passage in the same workspace
that belongs to a source document.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.common.analyzer import get_analyzer
from apps.common.analyzer.base import EvidenceCandidate
from apps.common.constants import (
    AnalysisStage,
    AnalysisStatus,
    DocumentRole,
    DocumentStatus,
)
from apps.documents.models import Document, Passage

from .models import AnalysisJob, Finding, FindingEvidence, WritingSuggestion
from .retrieval import retrieve_candidates

logger = logging.getLogger("apps.analysis")


class InvalidEvidenceError(Exception):
    pass


def validate_cited_evidence(
    cited_ids: list[str],
    candidates: list[EvidenceCandidate],
    *,
    workspace_id,
) -> list[EvidenceCandidate]:
    """
    Return only the cited candidates that are valid for this workspace.
    Unknown ids, ids not in the candidate set, cross-workspace ids, and target-
    document ids are all rejected.
    """
    allowed = {c.evidence_id: c for c in candidates}
    valid: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for cid in cited_ids:
        if cid in seen or cid not in allowed:
            continue
        seen.add(cid)
        valid.append(allowed[cid])

    if not valid:
        return []

    # Defence in depth: confirm the passages really exist in this workspace and
    # belong to source documents (guards against any retrieval-layer bug).
    ids = [c.evidence_id for c in valid]
    real = set(
        Passage.objects.filter(
            id__in=ids,
            workspace_id=workspace_id,
            document__role=DocumentRole.SOURCE,
        ).values_list("id", flat=True)
    )
    return [c for c in valid if c.evidence_id in {str(i) for i in real}]


def run_analysis(job_id) -> str:
    job = AnalysisJob.objects.select_related("workspace", "target_document").get(pk=job_id)
    if job.status in (AnalysisStatus.SUCCEEDED, AnalysisStatus.CANCELLED):
        return job.status

    job.status = AnalysisStatus.RUNNING
    job.stage = AnalysisStage.RETRIEVING
    job.started_at = timezone.now()
    job.progress = 0
    job.error_code = ""
    job.error_message = ""
    job.save(update_fields=["status", "stage", "started_at", "progress", "error_code", "error_message", "updated_at"])

    target: Document = job.target_document
    if target.status != DocumentStatus.READY:
        return _fail(job, "target_not_ready", "The target document has not finished processing.")
    if target.role != DocumentRole.TARGET:
        return _fail(job, "wrong_role", "The selected document is not a target document.")

    analyzer = get_analyzer()

    try:
        target_passages = list(
            Passage.objects.filter(document=target).order_by("chunk_index")
        )
        if not target_passages:
            return _fail(job, "no_target_text", "The target document has no extractable text.")

        job.total_claims = len(target_passages)
        job.save(update_fields=["total_claims", "updated_at"])

        # Idempotent re-run: clear previous findings for this job.
        Finding.objects.filter(analysis_job=job).delete()
        WritingSuggestion.objects.filter(analysis_job=job).delete()

        written_suggestions: list[WritingSuggestion] = []

        for index, passage in enumerate(target_passages, start=1):
            job.refresh_from_db(fields=["status"])
            if job.status == AnalysisStatus.CANCELLED:
                logger.info("analysis.cancelled", extra={"context": {"job_id": str(job.id)}})
                return job.status

            job.stage = AnalysisStage.RETRIEVING
            candidates = retrieve_candidates(workspace_id=job.workspace_id, target_passage=passage)

            job.stage = AnalysisStage.ASSESSING
            assessment = analyzer.assess_claim(claim_text=passage.text, candidates=candidates)

            valid_evidence = validate_cited_evidence(
                assessment.cited_evidence_ids, candidates, workspace_id=job.workspace_id
            )

            with transaction.atomic():
                finding = Finding.objects.create(
                    workspace_id=job.workspace_id,
                    analysis_job=job,
                    target_passage=passage,
                    status=assessment.status,
                    claim_text=passage.text,
                    explanation=assessment.explanation,
                    confidence=float(assessment.confidence),
                    needs_human_review=assessment.needs_human_review,
                    model_name=analyzer.name,
                    model_version=analyzer.version,
                )
                FindingEvidence.objects.bulk_create(
                    [
                        FindingEvidence(
                            finding=finding,
                            passage_id=c.evidence_id,
                            source_document_id=c.document_id,
                            page_number=c.page_number,
                            rank=rank,
                            score=c.score,
                            snippet=c.text[:1000],
                            is_validated=True,
                        )
                        for rank, c in enumerate(valid_evidence)
                    ]
                )

            # Writing feedback is stored separately from verification.
            for note in analyzer.review_writing(text=passage.text):
                written_suggestions.append(
                    WritingSuggestion(
                        workspace_id=job.workspace_id,
                        analysis_job=job,
                        target_passage=passage,
                        category=note.category,
                        severity=note.severity,
                        message=note.message[:1000],
                        suggestion=note.suggestion[:1000],
                    )
                )

            job.processed_claims = index
            job.progress = min(99, int(index / len(target_passages) * 100))
            job.save(update_fields=["processed_claims", "progress", "stage", "updated_at"])

        if written_suggestions:
            WritingSuggestion.objects.bulk_create(written_suggestions)

        job.status = AnalysisStatus.SUCCEEDED
        job.stage = AnalysisStage.FINALISING
        job.progress = 100
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "stage", "progress", "finished_at", "updated_at"])
        logger.info(
            "analysis.succeeded",
            extra={"context": {"job_id": str(job.id), "claims": job.total_claims}},
        )
        return job.status

    except Exception as exc:  # noqa: BLE001
        logger.exception("analysis.failed", exc_info=exc)
        return _fail(job, "analysis_error", "Analysis failed. You can retry.")


def _fail(job: AnalysisJob, code: str, message: str) -> str:
    job.status = AnalysisStatus.FAILED
    job.error_code = code
    job.error_message = message[:500]
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_code", "error_message", "finished_at", "updated_at"])
    return job.status
