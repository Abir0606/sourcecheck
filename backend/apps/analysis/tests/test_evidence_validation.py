from __future__ import annotations

import pytest

from apps.analysis.services import validate_cited_evidence
from apps.common.analyzer.base import EvidenceCandidate
from apps.workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db


def test_only_workspace_scoped_candidates_are_accepted(workspace, make_user, make_document):
    # A valid source passage in the same workspace.
    source = make_document(workspace=workspace, role="source", text="Valid evidence passage here.")
    valid_passage = source.passages.first()
    candidate = EvidenceCandidate(
        evidence_id=str(valid_passage.id),
        document_id=str(source.id),
        filename=source.original_filename,
        page_number=None,
        text=valid_passage.text,
        score=0.9,
    )

    # A passage in a *different* workspace, smuggled in as a candidate.
    other_owner = make_user()
    other_ws = Workspace.objects.create(name="Other", created_by=other_owner)
    Membership.objects.create(workspace=other_ws, user=other_owner, role="owner")
    other_doc = make_document(workspace=other_ws, role="source", text="Foreign evidence text.")
    foreign_passage = other_doc.passages.first()
    foreign_candidate = EvidenceCandidate(
        evidence_id=str(foreign_passage.id),
        document_id=str(other_doc.id),
        filename=other_doc.original_filename,
        page_number=None,
        text=foreign_passage.text,
        score=0.99,
    )

    result = validate_cited_evidence(
        [candidate.evidence_id, foreign_candidate.evidence_id, "does-not-exist"],
        [candidate, foreign_candidate],
        workspace_id=workspace.id,
    )
    assert [c.evidence_id for c in result] == [candidate.evidence_id]


def test_target_document_passage_is_not_valid_evidence(workspace, make_document):
    target = make_document(workspace=workspace, role="target", text="Target claim content.")
    target_passage = target.passages.first()
    candidate = EvidenceCandidate(
        evidence_id=str(target_passage.id),
        document_id=str(target.id),
        filename=target.original_filename,
        page_number=None,
        text=target_passage.text,
        score=1.0,
    )
    result = validate_cited_evidence([candidate.evidence_id], [candidate], workspace_id=workspace.id)
    assert result == []


def test_missing_ids_yield_empty_result(workspace):
    assert validate_cited_evidence([], [], workspace_id=workspace.id) == []
    assert validate_cited_evidence(["nope"], [], workspace_id=workspace.id) == []
