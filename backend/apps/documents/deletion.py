from __future__ import annotations

from django.db import transaction

from apps.common.adapters import get_storage
from apps.documents.models import Document


def purge_document(document: Document) -> None:
    """
    Fully remove a document: stored blob, extracted pages, passages (and their
    embeddings), and — via FK cascade — any findings that referenced it.
    """
    storage = get_storage()
    storage_key = document.storage_key
    with transaction.atomic():
        document.pages.all().delete()
        document.passages.all().delete()
        document.delete()
    if storage_key:
        storage.delete(storage_key)


def purge_workspace_data(workspace) -> dict:
    """Delete all document-derived data for a workspace (retention/deletion flow)."""
    from apps.analysis.models import AnalysisJob, Finding

    storage = get_storage()
    counts = {
        "documents": 0,
        "analyses": 0,
        "findings": 0,
    }
    for document in Document.objects.filter(workspace=workspace):
        purge_document(document)
        counts["documents"] += 1
    counts["findings"] = Finding.objects.filter(workspace=workspace).count()
    counts["analyses"] = AnalysisJob.objects.filter(workspace=workspace).count()
    AnalysisJob.objects.filter(workspace=workspace).delete()
    # Remove any orphaned blobs under the workspace prefix.
    storage.delete_prefix(f"workspaces/{workspace.id}/")
    return counts
