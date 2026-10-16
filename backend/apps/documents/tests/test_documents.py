from __future__ import annotations


import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.common.adapters import get_storage
from apps.common.constants import DocumentStatus
from apps.documents.models import Document

pytestmark = pytest.mark.django_db


def _upload(api, workspace, *, role, name, content):
    url = reverse("document-list", kwargs={"workspace_pk": workspace.id})
    upload = SimpleUploadedFile(name, content, content_type="text/plain")
    return api.post(url, {"role": role, "file": upload}, format="multipart")


def test_upload_target_and_source_are_processed(api, workspace):
    api.force_authenticate(workspace.owner)
    r_target = _upload(api, workspace, role="target", name="report.txt", content=b"Claim one. Claim two.")
    assert r_target.status_code == 201, r_target.data
    r_source = _upload(api, workspace, role="source", name="source.txt", content=b"Evidence for claim one.")
    assert r_source.status_code == 201, r_source.data

    # Eager processing means documents are READY immediately.
    assert Document.objects.get(id=r_target.data["id"]).status == DocumentStatus.READY
    source = Document.objects.get(id=r_source.data["id"])
    assert source.status == DocumentStatus.READY
    assert source.passages.exists()


def test_unsupported_file_type_is_rejected(api, workspace):
    api.force_authenticate(workspace.owner)
    r = _upload(api, workspace, role="source", name="notes.exe", content=b"MZ\x00binary")
    assert r.status_code == 400
    assert r.data["error"]["code"] == "unsupported_type"
    assert not Document.objects.filter(workspace=workspace).exists()


def test_empty_file_is_rejected(api, workspace):
    api.force_authenticate(workspace.owner)
    r = _upload(api, workspace, role="source", name="empty.txt", content=b"")
    assert r.status_code == 400
    assert r.data["error"]["code"] == "empty_file"


def test_delete_document_removes_blob_and_rows(api, workspace):
    api.force_authenticate(workspace.owner)
    r = _upload(api, workspace, role="source", name="source.txt", content=b"Some evidence text.")
    document = Document.objects.get(id=r.data["id"])
    key = document.storage_key
    assert get_storage().exists(key)

    url = reverse("document-detail", kwargs={"workspace_pk": workspace.id, "pk": document.id})
    assert api.delete(url).status_code == 204
    assert not Document.objects.filter(id=document.id).exists()
    assert not get_storage().exists(key)


def test_upload_requires_write_role(api, workspace, make_user):
    from apps.workspaces.models import Membership

    viewer = make_user()
    Membership.objects.create(workspace=workspace, user=viewer, role="viewer")
    api.force_authenticate(viewer)
    r = _upload(api, workspace, role="source", name="source.txt", content=b"text")
    assert r.status_code == 403
