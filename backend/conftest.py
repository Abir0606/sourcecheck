from __future__ import annotations

import io

import pytest
from rest_framework.test import APIClient

from apps.analysis.models import AnalysisJob
from apps.analysis.services import run_analysis
from apps.documents.models import Document
from apps.documents.services import process_document
from apps.workspaces.models import Membership, Workspace

# Non-personal, clearly fictional sample content used across tests and seeds.


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def make_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    counter = {"n": 0}

    def _make(password="test-pass-12345", **extra):
        counter["n"] += 1
        email = extra.pop("email", f"user{counter['n']}@example.test")
        return User.objects.create_user(email=email, password=password, **extra)

    return _make


@pytest.fixture
def workspace(db, make_user):
    owner = make_user()
    ws = Workspace.objects.create(name="Test Workspace", created_by=owner)
    Membership.objects.create(workspace=ws, user=owner, role="owner")
    ws.owner = owner
    return ws


@pytest.fixture
def auth_api(api, make_user):
    def _auth(user):
        api.force_authenticate(user=user)
        return api

    return _auth


@pytest.fixture
def make_document(db):
    def _make(*, workspace, role, text, filename=None, user=None, process=True):
        filename = filename or f"{role}.txt"
        document = Document.objects.create(
            workspace=workspace,
            role=role,
            original_filename=filename,
            content_type="text/plain",
            size_bytes=len(text.encode()),
            sha256="0" * 64,
            storage_key=f"workspaces/{workspace.id}/documents/{role}.txt",
            created_by=user,
        )
        from apps.common.adapters import get_storage

        get_storage().save(document.storage_key, io.BytesIO(text.encode()))
        if process:
            process_document(document.id)
            document.refresh_from_db()
        return document

    return _make


@pytest.fixture
def run_analysis_job(db):
    def _run(workspace, target, user=None):
        job = AnalysisJob.objects.create(
            workspace=workspace, target_document=target, requested_by=user
        )
        run_analysis(job.id)
        job.refresh_from_db()
        return job

    return _run
