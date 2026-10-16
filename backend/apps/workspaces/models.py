from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.constants import WorkspaceRole
from apps.common.models import TimeStampedModel


class Workspace(TimeStampedModel):
    """
    A tenant boundary. `data_region` and `retention_days` are configuration,
    not legal decisions — the controller/DPO sets the values (see decisions doc).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    data_region = models.CharField(max_length=40, default=settings.DATA_REGION)
    retention_days = models.PositiveIntegerField(
        default=0,
        help_text="0 means 'retain until deleted'. Actual value is a controller decision.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workspaces",
    )
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or "workspace"
            candidate = base
            i = 1
            while Workspace.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}-{i}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def role_for(self, user) -> str | None:
        if getattr(user, "is_superuser", False):
            return WorkspaceRole.OWNER
        return (
            Membership.objects.filter(workspace=self, user=user)
            .values_list("role", flat=True)
            .first()
        )


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=WorkspaceRole.choices, default=WorkspaceRole.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "user")
        ordering = ["workspace", "user__email"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user} in {self.workspace} as {self.role}"
