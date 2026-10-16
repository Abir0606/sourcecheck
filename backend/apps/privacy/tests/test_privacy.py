from __future__ import annotations

import json

import pytest
from django.urls import reverse

from apps.analysis.models import AnalysisJob
from apps.common.adapters import get_storage
from apps.documents.models import Document

pytestmark = pytest.mark.django_db


def test_export_produces_downloadable_bundle(api, workspace, make_document):
    api.force_authenticate(workspace.owner)
    make_document(workspace=workspace, role="source", text="Exportable content.")
    # Export requests require a write role; owner qualifies.
    from apps.workspaces.models import Membership  # noqa: F401

    url = reverse("export-list", kwargs={"workspace_pk": workspace.id})
    r = api.post(url)
    assert r.status_code == 202
    export_id = r.data["id"]

    # Eager task processed the export.
    detail = reverse("export-detail", kwargs={"workspace_pk": workspace.id, "pk": export_id})
    assert api.get(detail).data["status"] == "completed"

    download = reverse("export-download", kwargs={"workspace_pk": workspace.id, "pk": export_id})
    resp = api.get(download)
    assert resp.status_code == 200
    payload = json.loads(b"".join(resp.streaming_content).decode())
    assert payload["workspace"]["id"] == str(workspace.id)
    assert len(payload["documents"]) == 1


def test_deletion_request_purges_documents_and_analyses(api, workspace, make_document, run_analysis_job):
    api.force_authenticate(workspace.owner)
    target = make_document(workspace=workspace, role="target", text="A claim about the dam.")
    make_document(workspace=workspace, role="source", text="The dam is real evidence.")
    run_analysis_job(workspace, target)
    assert Document.objects.filter(workspace=workspace).count() == 2

    # Capture blob keys to confirm they are removed from storage.
    keys = list(Document.objects.filter(workspace=workspace).values_list("storage_key", flat=True))

    url = reverse("deletion-list", kwargs={"workspace_pk": workspace.id})
    r = api.post(url, {"scope": "documents"}, format="json")
    assert r.status_code == 202
    deletion_id = r.data["id"]

    detail = reverse("deletion-detail", kwargs={"workspace_pk": workspace.id, "pk": deletion_id})
    assert api.get(detail).data["status"] == "completed"

    assert Document.objects.filter(workspace=workspace).count() == 0
    assert AnalysisJob.objects.filter(workspace=workspace).count() == 0
    for key in keys:
        assert not get_storage().exists(key)


def test_deletion_requires_admin(api, workspace, make_user):
    from apps.workspaces.models import Membership

    editor = make_user()
    Membership.objects.create(workspace=workspace, user=editor, role="editor")
    api.force_authenticate(editor)
    url = reverse("deletion-list", kwargs={"workspace_pk": workspace.id})
    assert api.post(url, {"scope": "documents"}, format="json").status_code == 403


def test_privacy_overview_reports_inventory(api, workspace, make_document):
    api.force_authenticate(workspace.owner)
    make_document(workspace=workspace, role="source", text="Some content.")
    url = reverse("privacy-overview", kwargs={"workspace_pk": workspace.id})
    r = api.get(url)
    assert r.status_code == 200
    assert r.data["data_inventory"]["documents"] == 1
