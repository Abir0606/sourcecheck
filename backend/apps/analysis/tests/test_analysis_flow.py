from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.analysis.models import AnalysisJob, Finding
from apps.common.constants import AnalysisStatus, FindingStatus
from apps.sample_content import SOURCE_TEXT, TARGET_TEXT

pytestmark = pytest.mark.django_db


def _upload(api, workspace, *, role, name, content):
    url = reverse("document-list", kwargs={"workspace_pk": workspace.id})
    upload = SimpleUploadedFile(name, content, content_type="text/plain")
    return api.post(url, {"role": role, "file": upload}, format="multipart")


def _start_analysis(api, workspace, target_id, idem=""):
    url = reverse("analysis-list", kwargs={"workspace_pk": workspace.id})
    return api.post(url, {"target_document_id": str(target_id), "idempotency_key": idem}, format="json")


def test_upload_to_findings_flow(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(api, workspace, role="target", name="report.txt", content=TARGET_TEXT.encode())
    _upload(api, workspace, role="source", name="source.txt", content=SOURCE_TEXT.encode())

    resp = _start_analysis(api, workspace, target.data["id"])
    assert resp.status_code == 201, resp.data
    job_id = resp.data["id"]

    # Tasks run eagerly in tests; the DB reflects the completed job.
    job = AnalysisJob.objects.get(id=job_id)
    assert job.status == AnalysisStatus.SUCCEEDED
    assert job.findings.exists()

    findings_url = reverse(
        "analysis-findings", kwargs={"workspace_pk": workspace.id, "pk": job_id}
    )
    r = api.get(findings_url)
    assert r.status_code == 200
    assert r.data["summary"]["total"] == job.findings.count()

    # Every persisted evidence row must be validated and point at a source doc.
    for finding in Finding.objects.filter(analysis_job=job):
        for ev in finding.evidence.all():
            assert ev.is_validated is True
            assert ev.source_document.role == "source"


def test_analysis_requires_a_source_document(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(api, workspace, role="target", name="report.txt", content=TARGET_TEXT.encode())
    resp = _start_analysis(api, workspace, target.data["id"])
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "no_sources"


def test_analysis_is_idempotent(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(api, workspace, role="target", name="report.txt", content=TARGET_TEXT.encode())
    _upload(api, workspace, role="source", name="source.txt", content=SOURCE_TEXT.encode())

    first = _start_analysis(api, workspace, target.data["id"], idem="abc")
    second = _start_analysis(api, workspace, target.data["id"], idem="abc")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert AnalysisJob.objects.filter(workspace=workspace).count() == 1


def test_failed_analysis_can_be_retried(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(api, workspace, role="target", name="report.txt", content=TARGET_TEXT.encode())
    _upload(api, workspace, role="source", name="source.txt", content=SOURCE_TEXT.encode())
    job_id = _start_analysis(api, workspace, target.data["id"]).data["id"]

    job = AnalysisJob.objects.get(id=job_id)
    job.status = AnalysisStatus.FAILED
    job.error_code = "analysis_error"
    job.save(update_fields=["status", "error_code"])

    retry_url = reverse("analysis-retry", kwargs={"workspace_pk": workspace.id, "pk": job_id})
    r = api.post(retry_url)
    assert r.status_code == 200
    job.refresh_from_db()
    assert job.status == AnalysisStatus.SUCCEEDED


def test_review_and_report(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(api, workspace, role="target", name="report.txt", content=TARGET_TEXT.encode())
    _upload(api, workspace, role="source", name="source.txt", content=SOURCE_TEXT.encode())
    job_id = _start_analysis(api, workspace, target.data["id"]).data["id"]

    finding = Finding.objects.filter(analysis_job_id=job_id).first()
    detail_url = reverse("finding-detail", kwargs={"workspace_pk": workspace.id, "pk": finding.id})
    r = api.patch(detail_url, {"review_state": "accepted", "review_note": "Looks right."}, format="json")
    assert r.status_code == 200
    finding.refresh_from_db()
    assert finding.review_state == "accepted"
    assert finding.reviewed_by_id == workspace.owner.id

    report_url = reverse("analysis-report", kwargs={"workspace_pk": workspace.id, "pk": job_id})
    json_report = api.get(report_url, {"export": "json"})
    assert json_report.status_code == 200
    assert "findings" in json_report.data
    assert "not a plagiarism report" in json_report.data["disclaimer"]

    csv_report = api.get(report_url, {"export": "csv"})
    assert csv_report.status_code == 200
    assert csv_report["Content-Type"].startswith("text/csv")


def test_unsupported_statements_are_never_labelled_false(api, workspace):
    api.force_authenticate(workspace.owner)
    target = _upload(
        api, workspace, role="target", name="report.txt",
        content=b"The moon is made entirely of green cheese and orbitz.",
    )
    _upload(api, workspace, role="source", name="source.txt", content=SOURCE_TEXT.encode())
    job_id = _start_analysis(api, workspace, target.data["id"]).data["id"]

    for finding in Finding.objects.filter(analysis_job_id=job_id):
        if finding.status == FindingStatus.UNSUPPORTED_BY_SOURCES:
            assert "not mean the statement is false" in finding.explanation
            assert finding.needs_human_review is True
