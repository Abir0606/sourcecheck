from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.constants import (
    AnalysisStage,
    AnalysisStatus,
    FindingStatus,
    ReviewState,
    WritingCategory,
)
from apps.common.models import WorkspaceScopedModel


class AnalysisJob(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="analysis_jobs"
    )
    status = models.CharField(
        max_length=20, choices=AnalysisStatus.choices, default=AnalysisStatus.QUEUED, db_index=True
    )
    stage = models.CharField(
        max_length=20, choices=AnalysisStage.choices, default=AnalysisStage.PENDING
    )
    progress = models.PositiveSmallIntegerField(default=0)
    total_claims = models.PositiveIntegerField(default=0)
    processed_claims = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(max_length=128, blank=True)
    celery_task_id = models.CharField(max_length=128, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="analysis_jobs"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["workspace", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="unique_idempotency_key_per_workspace",
            )
        ]


class Finding(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="findings")
    target_passage = models.ForeignKey(
        "documents.Passage", on_delete=models.CASCADE, related_name="findings"
    )
    status = models.CharField(max_length=32, choices=FindingStatus.choices, db_index=True)
    claim_text = models.TextField()
    explanation = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)
    needs_human_review = models.BooleanField(default=True)
    model_name = models.CharField(max_length=64, blank=True)
    model_version = models.CharField(max_length=32, blank=True)
    review_state = models.CharField(
        max_length=20, choices=ReviewState.choices, default=ReviewState.UNREVIEWED, db_index=True
    )
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_findings"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["target_passage__chunk_index"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["analysis_job", "status"]),
        ]

    def mark_reviewed(self, *, state: str, user, note: str = "") -> None:
        self.review_state = state
        self.review_note = note
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save(update_fields=["review_state", "review_note", "reviewed_by", "reviewed_at", "updated_at"])


class FindingEvidence(models.Model):
    """
    Evidence shown to the user. `is_validated` is set only after the service
    confirms the passage id exists and belongs to the same workspace.
    """

    id = models.BigAutoField(primary_key=True)
    finding = models.ForeignKey(Finding, on_delete=models.CASCADE, related_name="evidence")
    passage = models.ForeignKey(
        "documents.Passage", on_delete=models.CASCADE, related_name="cited_by"
    )
    source_document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="cited_evidence"
    )
    page_number = models.PositiveIntegerField(null=True, blank=True)
    rank = models.PositiveSmallIntegerField(default=0)
    score = models.FloatField(default=0.0)
    snippet = models.TextField(blank=True)
    is_validated = models.BooleanField(default=False)

    class Meta:
        ordering = ["finding", "rank"]
        indexes = [models.Index(fields=["finding", "rank"])]


class WritingSuggestion(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="writing_suggestions")
    target_passage = models.ForeignKey(
        "documents.Passage", on_delete=models.CASCADE, null=True, blank=True, related_name="writing_suggestions"
    )
    category = models.CharField(max_length=20, choices=WritingCategory.choices)
    severity = models.CharField(max_length=16, default="info")
    message = models.CharField(max_length=1000)
    suggestion = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ["category", "id"]
