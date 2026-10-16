"""Vector store adapter. Only pgvector is implemented; the interface allows a
managed search service to be added later without touching business logic."""
from __future__ import annotations

import abc


class VectorStore(abc.ABC):
    @abc.abstractmethod
    def search(
        self,
        *,
        workspace_id,
        embedding: list[float],
        limit: int,
        document_ids: list | None = None,
        exclude_document_ids: list | None = None,
    ) -> list[dict]: ...


class PgVectorStore(VectorStore):
    """Uses pgvector cosine distance over Passage rows, always scoped by workspace."""

    def search(self, *, workspace_id, embedding, limit, document_ids=None, exclude_document_ids=None):
        from django.db import connection

        vec = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
        sql = [
            "SELECT id, document_id, page_number, 1 - (embedding <=> %s::vector) AS score",
            "FROM documents_passage WHERE workspace_id = %s AND embedding IS NOT NULL",
        ]
        params: list = [vec, str(workspace_id)]
        if document_ids:
            sql.append("AND document_id = ANY(%s)")
            params.append([str(d) for d in document_ids])
        if exclude_document_ids:
            sql.append("AND NOT (document_id = ANY(%s))")
            params.append([str(d) for d in exclude_document_ids])
        sql.append("ORDER BY embedding <=> %s::vector LIMIT %s")
        params.extend([vec, limit])

        with connection.cursor() as cur:
            cur.execute(" ".join(sql), params)
            rows = cur.fetchall()
        return [
            {"passage_id": r[0], "document_id": r[1], "page_number": r[2], "score": float(r[3])}
            for r in rows
        ]
