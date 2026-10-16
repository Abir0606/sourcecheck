# Architecture

## Shape

A **modular monolith** with three deployable processes sharing one codebase:

1. **React SPA** (`frontend/`) — Vite + TypeScript.
2. **Django + DRF API** (`backend/`, process: `web`).
3. **Celery worker** (+ beat) — async processing.

No microservices. Modules map to Django apps under `backend/apps/`:

| App | Responsibility |
|---|---|
| `common` | Adapters, audit, permissions, health, logging, shared constants |
| `accounts` | Custom email-login user, session/CSRF auth |
| `workspaces` | Tenant boundary, memberships, roles, settings |
| `documents` | Upload, extraction, chunking, passages/embeddings |
| `analysis` | Retrieval, analyzer orchestration, findings, review, reports |
| `privacy` | Export and deletion flows |

## Ports and adapters

Business logic depends only on interfaces; providers are selected by env var.

- `StorageBackend` — `LocalStorage` / `AzureBlobStorage`
- `VectorStore` — `PgVectorStore` (pgvector)
- `Analyzer` — offline `RulesAnalyzer` (default), `OpenAICompatibleAnalyzer`,
  `AzureOpenAIAnalyzer`
- `OcrProvider` — `NullOcr`, `TesseractOcr`
- `EmbeddingBackend` — offline deterministic `HashingEmbedder`

Azure SDKs are imported **lazily inside adapters**, so the app boots with no cloud
configuration. See `backend/apps/common/adapters/` and `backend/apps/common/analyzer/`.

## Processing pipeline

### Document ingest (async, idempotent)
`upload → validate type/size → store blob (content hashed) → DocumentPage rows →
overlapping Passages with page + char offsets → embeddings → status=ready`.
Re-running is safe: existing pages/passages are replaced.

### Analysis (async, idempotent)
For each target passage:
1. **Retrieve** candidate evidence from the workspace's **source** documents only
   (`analysis/retrieval.py`): semantic (pgvector) + keyword/fuzzy.
2. **Assess** via the configured analyzer, which sees only those candidates and
   must return evidence ids.
3. **Validate** every returned id (`analysis/services.validate_cited_evidence`):
   it must be in the candidate set **and** resolve to a Passage in the **same
   workspace** belonging to a **source** document. Nothing is persisted otherwise.
4. Persist `Finding` + `FindingEvidence` (marked validated).
5. **Writing feedback** is produced separately and never mixed into verification.

The analyzer cannot be steered by document content: prompts wrap document text as
untrusted data and instruct the model to ignore embedded instructions and to cite
only provided ids.

## Data model (summary)

`Workspace` ← `Membership` (owner/admin/editor/viewer). All tenant data is
`WorkspaceScopedModel` (carries `workspace` FK).

- `Document` (role: target|source) → `DocumentPage`, `Passage` (embedding vector)
- `AnalysisJob` → `Finding` → `FindingEvidence` (→ `Passage` → `Document`)
- `WritingSuggestion`
- `AuditEvent`
- `ExportJob`, `DeletionRequest`

## Authorization

Enforced server-side on every endpoint and reused by tasks:
`apps/common/permissions.py` (`roles_for`, `has_workspace_write`, `has_workspace_admin`)
and viewsets that always filter querysets by the caller's memberships. Cross-tenant
objects return 404, not 403, to avoid existence leaks.

## Reliability

- Async + idempotent tasks; late acks; bounded retries (`CONFIG`: `backend/config/settings/base.py`).
- Progress, stage, and error codes on `Document` and `AnalysisJob`; the UI polls
  and survives page refresh (state is in the DB, not the browser).
- `/healthz` (liveness) and `/readyz` (DB + storage readiness).
- Structured JSON logs with a per-request id; **document text is never logged**.
