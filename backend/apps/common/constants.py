"""
Central vocabulary. Keeping user-facing wording here prevents drift between
the analyzer, the API, and the UI — especially the crucial distinction that
"not found in the uploaded sources" is NOT equivalent to "false".
"""
from __future__ import annotations

from django.db import models


class FindingStatus(models.TextChoices):
    SUPPORTED = "supported", "Supported"
    PARTIALLY_SUPPORTED = "partially_supported", "Partially supported"
    UNSUPPORTED_BY_SOURCES = "unsupported_by_sources", "Unsupported by uploaded sources"
    CONFLICTS_WITH_SOURCES = "conflicts_with_sources", "Conflicts with uploaded sources"
    CITATION_ISSUE = "citation_issue", "Citation issue"


# Neutral, legally-careful descriptions shown in tooltips / report footers.
FINDING_STATUS_DESCRIPTIONS: dict[str, str] = {
    FindingStatus.SUPPORTED: "The uploaded sources appear to support this statement.",
    FindingStatus.PARTIALLY_SUPPORTED: "The uploaded sources support part of this statement.",
    FindingStatus.UNSUPPORTED_BY_SOURCES: (
        "This statement was not found in the uploaded sources. This does not mean "
        "the statement is false — only that the uploaded sources do not cover it."
    ),
    FindingStatus.CONFLICTS_WITH_SOURCES: (
        "The uploaded sources appear to contradict this statement."
    ),
    FindingStatus.CITATION_ISSUE: (
        "The citation could not be verified against the uploaded sources "
        "(missing source, mismatched page, or malformed reference)."
    ),
}


class DocumentRole(models.TextChoices):
    TARGET = "target", "Target document"
    SOURCE = "source", "Source document"


class DocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    VALIDATING = "validating", "Validating"
    EXTRACTING = "extracting", "Extracting text"
    OCR = "ocr", "Running OCR"
    CHUNKING = "chunking", "Splitting into passages"
    EMBEDDING = "embedding", "Indexing passages"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"
    UNSUPPORTED = "unsupported", "Unsupported file type"
    EMPTY = "empty", "No extractable text"


class WorkspaceRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


# Roles permitted to perform mutating actions.
WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.EDITOR}
ADMIN_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}


class AnalysisStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ReviewState(models.TextChoices):
    UNREVIEWED = "unreviewed", "Needs review"
    ACCEPTED = "accepted", "Accepted"
    CORRECTED = "corrected", "Corrected"
    DISMISSED = "dismissed", "Dismissed"


class WritingCategory(models.TextChoices):
    CLARITY = "clarity", "Clarity"
    GRAMMAR = "grammar", "Grammar"
    READABILITY = "readability", "Readability"
    STYLE = "style", "Style"


class AnalysisStage(models.TextChoices):
    PENDING = "pending", "Pending"
    RETRIEVING = "retrieving", "Retrieving evidence"
    ASSESSING = "assessing", "Assessing claims"
    WRITING_REVIEW = "writing_review", "Reviewing writing"
    FINALISING = "finalising", "Finalising"


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


# A finding needs a human when the model is unsure or evidence is weak.
def needs_human_review(status: str, confidence: float, *, has_evidence: bool) -> bool:
    if status == FindingStatus.UNSUPPORTED_BY_SOURCES:
        return True
    if confidence < 0.6:
        return True
    if not has_evidence and status != FindingStatus.CITATION_ISSUE:
        return True
    return False
