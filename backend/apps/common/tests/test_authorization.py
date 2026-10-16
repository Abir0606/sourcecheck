from __future__ import annotations

import pytest
from django.urls import reverse

from apps.workspaces.models import Membership

pytestmark = pytest.mark.django_db


@pytest.fixture
def outsider(make_user):
    return make_user()


def test_outsider_cannot_access_other_workspace(api, workspace, outsider):
    api.force_authenticate(outsider)
    url = reverse("document-list", kwargs={"workspace_pk": workspace.id})
    assert api.get(url).status_code == 404


def test_outsider_cannot_list_memberships(api, workspace, outsider):
    api.force_authenticate(outsider)
    url = reverse("workspace-members", kwargs={"workspace_pk": workspace.id})
    assert api.get(url).status_code == 404


def test_outsider_cannot_read_findings(api, workspace, outsider, make_document, run_analysis_job):
    target = make_document(workspace=workspace, role="target", text="A claim about the dam.")
    make_document(workspace=workspace, role="source", text="The dam is real evidence.")
    job = run_analysis_job(workspace, target)
    finding = job.findings.first()
    if finding is None:
        pytest.skip("No findings produced for this fixture text.")

    api.force_authenticate(outsider)
    url = reverse("finding-detail", kwargs={"workspace_pk": workspace.id, "pk": finding.id})
    assert api.get(url).status_code == 404


def test_member_without_write_role_cannot_change_settings(api, workspace, make_user):
    editor = make_user()
    Membership.objects.create(workspace=workspace, user=editor, role="editor")
    api.force_authenticate(editor)
    url = reverse("workspace-settings", kwargs={"pk": workspace.id})
    r = api.patch(url, {"retention_days": 30}, format="json")
    assert r.status_code == 403


def test_admin_can_change_settings(api, workspace):
    api.force_authenticate(workspace.owner)
    url = reverse("workspace-settings", kwargs={"pk": workspace.id})
    r = api.patch(url, {"retention_days": 90}, format="json")
    assert r.status_code == 200
    workspace.refresh_from_db()
    assert workspace.retention_days == 90
