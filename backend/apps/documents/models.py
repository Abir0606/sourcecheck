from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from apps.common.constants import DocumentRole, DocumentStatus
from apps.common.models import WorkspaceScopedModel


def document_storage_key(workspace_id, document_id, filename: str) -> str:
    """Content is stored under a per-workspace prefix for clean deletion."""
    safe = filename.replace("\\", "/").split("/")[-1]
    return f"workspaces/{workspace_id}/documents/{document_id}/{safe}"


class Document(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=DocumentRole.choices)
    original_filename = models.CharField(max_length=512)
    content_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)
    storage_key = models.CharField(max_length=1024)
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.UPLOADED, db_index=True
    )
    stage_detail = models.CharField(max_length=200, blank=True)
    page_count = models.PositiveIntegerField(default=0)
    char_count = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=16, blank=True)
    ocr_used = models.BooleanField(default=False)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_documents"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "role", "-created_at"]),
            models.Index(fields=["workspace", "sha256"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.original_filename

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY


class DocumentPage(models.Model):
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    char_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["document", "page_number"]
        indexes = [models.Index(fields=["document", "page_number"])]


class Passage(WorkspaceScopedModel):
    """
    The searchable unit. Carries page + filename context via its document so any
    finding can always show where evidence came from.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="passages")
    page_number = models.PositiveIntegerField(null=True, blank=True)
    chunk_index = models.PositiveIntegerField(default=0)
    text = models.TextField()
    start_char = models.PositiveIntegerField(default=0)
    end_char = models.PositiveIntegerField(default=0)
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        indexes = [
            models.Index(fields=["workspace", "document"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.document.original_filename} p{self.page_number} #{self.chunk_index}"
