"""
Evidence retrieval. Evidence is retrieved BEFORE the analyzer is asked to judge
a claim, and retrieval is always restricted to the workspace's *source*
documents (never the target document itself).
"""
from __future__ import annotations

import re

from django.conf import settings

from apps.common.adapters import get_embedder, get_vector_store
from apps.common.analyzer.base import EvidenceCandidate
from apps.common.constants import DocumentRole, DocumentStatus
from apps.documents.models import Document, Passage

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were",
    "for", "on", "with", "that", "this", "by", "as", "at", "from", "it", "be",
}
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")


def _keywords(text: str, limit: int = 6) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    seen: list[str] = []
    for t in tokens:
        if t not in _STOPWORDS and t not in seen:
            seen.append(t)
        if len(seen) >= limit:
            break
    return seen


def source_document_ids(workspace_id) -> list:
    return list(
        Document.objects.filter(
            workspace_id=workspace_id,
            role=DocumentRole.SOURCE,
            status=DocumentStatus.READY,
        ).values_list("id", flat=True)
    )


def retrieve_candidates(*, workspace_id, target_passage: Passage, limit: int | None = None) -> list[EvidenceCandidate]:
    limit = limit or settings.CANDIDATE_EVIDENCE_LIMIT
    src_ids = source_document_ids(workspace_id)
    if not src_ids:
        return []

    by_id: dict[str, EvidenceCandidate] = {}

    # 1) Semantic retrieval (pgvector), strictly scoped to source documents.
    try:
        embedding = get_embedder().embed([target_passage.text])[0]
        hits = get_vector_store().search(
            workspace_id=workspace_id, embedding=embedding, limit=limit, document_ids=src_ids
        )
    except Exception:  # pragma: no cover - depends on DB extension
        hits = []

    passage_map = {
        str(p.id): p
        for p in Passage.objects.filter(id__in=[h["passage_id"] for h in hits]).select_related("document")
    }
    for hit in hits:
        p = passage_map.get(str(hit["passage_id"]))
        if p is None:
            continue
        by_id[str(p.id)] = _candidate(p, score=hit["score"], match_source="semantic")

    # 2) Keyword/fuzzy retrieval to catch literal overlaps semantic search may miss.
    keywords = _keywords(target_passage.text)
    if keywords:
        from django.db.models import Q

        query = Q()
        for kw in keywords:
            query |= Q(text__icontains=kw)
        matches = (
            Passage.objects.filter(
                workspace_id=workspace_id, document_id__in=src_ids
            )
            .filter(query)
            .select_related("document")[: limit * 2]
        )
        for p in matches:
            key = str(p.id)
            if key not in by_id:
                by_id[key] = _candidate(p, score=0.5, match_source="keyword")

    candidates = sorted(by_id.values(), key=lambda c: c.score, reverse=True)[:limit]
    return candidates


def _candidate(passage: Passage, *, score: float, match_source: str) -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_id=str(passage.id),
        document_id=str(passage.document_id),
        filename=passage.document.original_filename,
        page_number=passage.page_number,
        text=passage.text,
        score=float(score),
        match_source=match_source,
    )
