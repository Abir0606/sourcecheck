# SourceCheck

A document **source-checking** application. A user creates a workspace, uploads one
**target** document and one or more **source** documents, and the app checks the
target's claims and citations against **only the uploaded sources**.

- Findings are labelled `Supported`, `Partially supported`, `Unsupported by uploaded
  sources`, `Conflicts with uploaded sources`, or `Citation issue`.
- **"Unsupported by uploaded sources" never means "false"** — only that the uploaded
  sources do not cover the statement. This distinction is enforced in the code
  (`backend/apps/common/constants.py`) and surfaced verbatim in the UI and reports.
- This is **not** plagiarism detection and does **not** search the public internet.

> **Runs with no Azure credentials.** Everything has a local default; cloud services
> sit behind adapters and are enabled with environment variables.

---

## Architecture at a glance

```
React SPA (Vite/TS) ──HTTP──▶ Django + DRF API ──enqueue──▶ Celery worker
                                     │                           │
                                     ├── PostgreSQL (+pgvector) ◀─┤
                                     └── Object storage adapter ◀─┘
                                          (local FS | Azure Blob)
```

Cloud touchpoints are ports/adapters: `StorageBackend`, `VectorStore`, `Analyzer`,
`OcrProvider`, `EmbeddingBackend`. See `docs/architecture.md`.

## Project layout

```
backend/    Django project (config/ = settings; apps/ = domain modules)
frontend/   React + TypeScript SPA (Vite)
infra/      Azure Bicep templates (deployment only, no business logic)
docs/       Architecture, privacy (GDPR/DPA), security, deployment, Azure notes
docker-compose.yml
.env.example
```

---

## Quick start (local, no Azure)

**Prerequisites:** Docker, Python 3.12+, Node 20+.

```powershell
# 1. Configuration
Copy-Item .env.example .env

# 2. Infrastructure (PostgreSQL+pgvector, Redis) on host port 5433
docker compose up -d db redis

# 3. Backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py seed_demo      # demo user + sample documents
..\.venv\Scripts\python manage.py runserver       # http://127.0.0.1:8000

# 4. Worker (separate terminal) — processes uploads and analyses
cd backend
..\.venv\Scripts\python -m celery -A config worker -l info

# 5. Frontend (separate terminal)
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```

Demo credentials created by `seed_demo`: `demo@example.test` / `demo-pass-12345`.

> The compose DB uses **host port 5433** to avoid clashing with a local PostgreSQL on
> 5432. Override with `DATABASE_URL` in `.env` if needed.

### Or run everything in Docker

```powershell
docker compose up --build       # api + worker + beat + db + redis
```
The frontend is simplest to run with `npm run dev` (it proxies `/api` to the API).

## Tests

```powershell
cd backend
..\.venv\Scripts\python -m pytest
```

Covers authorization / cross-workspace isolation, evidence-ID validation, document
deletion, task retry, and the full upload→analysis→report flow. Tests run tasks
eagerly, so no broker is required.

---

## What is local/mock vs what needs Azure

| Capability | Local default | Azure option (adapter) |
|---|---|---|
| Object storage | Filesystem (`local_storage/`) | Azure Blob Storage (`STORAGE_BACKEND=azure`) |
| Vector search | pgvector | pgvector on Azure PostgreSQL Flexible Server |
| Broker | Redis (compose) | Azure Cache for Redis (or Service Bus) |
| Analysis | Offline deterministic `rules` analyzer | Azure OpenAI / OpenAI-compatible (`ANALYZER_BACKEND=...`) |
| OCR | Disabled (`OCR_PROVIDER=none`) | Local Tesseract, or Azure AI Document Intelligence |
| Secrets | `.env` | Azure Key Vault (`SECRET_PROVIDER=key_vault`) |
| Identity | Django sessions | Entra ID (documented upgrade path) |

The `rules` analyzer is fully offline and deterministic — it never contacts the
internet — so the app is usable and testable with zero external services.

---

## Privacy & deployment documentation

Start with:

- `docs/privacy/decisions-needed.md` — **legal/operational decisions that must be
  made by the controller/DPO/counsel** (not by this software).
- `docs/privacy/data-inventory.md`, `data-flow.md`, `retention-schedule.md`
- `docs/privacy/dpia-input-pack.md`, `subprocessors.md`
- `docs/security-overview.md`
- `docs/deployment/` and `docs/azure/` (region verification, cost notes)

**No software or infrastructure configuration alone makes this service legally
compliant.** The docs identify what the application provides and what people must
decide.
