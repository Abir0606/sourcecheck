from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import WorkspaceScopedModel


class DeletionScope(models.TextChoices):
    DOCUMENTS = "documents", "Documents and extracted data"
    ANALYSIS = "analysis", "Analysis results only"
    WORKSPACE = "workspace", "Entire workspace"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DeletionRequest(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=20, choices=DeletionScope.choices)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def complete(self, result: dict) -> None:
        self.status = RequestStatus.COMPLETED
        self.result = result
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "result", "completed_at", "updated_at"])


class ExportJob(WorkspaceScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    storage_key = models.CharField(max_length=1024, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    error_message = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.now())
