# SourceCheck — Build & Setup Notes

This document explains **what was built, how, and with exactly which tools,
versions, and containers**. For the short "run it" guide, see `README.md`.

---

## 1. What this is

**SourceCheck** is a document **source-checking** web app:

- A user creates a **workspace**, uploads a **target** document and one or more
  **source** documents.
- The app reads the target, breaks it into passages, retrieves the most relevant
  evidence **from the uploaded sources only**, and produces **findings**:
  `Supported`, `Partially supported`, `Unsupported by uploaded sources`,
  `Conflicts with uploaded sources`, `Citation issue`.
- It also produces separate **writing feedback** (kept strictly apart from
  verification).
- **"Unsupported by uploaded sources" never means "false."** This rule is a central
  constant (`backend/apps/common/constants.py`) and is shown verbatim in the UI.
- It is **not** plagiarism detection and does **not** touch the public internet.
- It runs **fully locally with zero Azure credentials**; cloud services are behind
  adapters and turned on with environment variables.

---

## 2. How it was built (chronological)

1. **Reconnaissance** — inspected the (empty) working directory, confirmed the
   available toolchain (Python, Node, Docker, Git, GitHub CLI). No Azure CLI or
   Terraform present.
2. **Architecture & data model** — chose a **modular monolith** (Django + DRF API,
   Celery worker/beat, React SPA), with ports/adapters so every cloud dependency has
   a local default.
3. **Backend scaffold** — Django project `config/` with split settings
   (`base` / `local` / `production` / `test`) and domain apps under `apps/`.
4. **Domain modules** — `common`, `accounts`, `workspaces`, `documents`, `analysis`,
   `privacy`, each with models, serializers, views, services, tasks and tests.
5. **Adapters** — storage, vector store, embeddings, OCR, analyzer, secrets; every
   cloud SDK import is lazy so the app boots without them.
6. **Migrations** — generated, plus a hand-added `VectorExtension()` operation so
   `CREATE EXTENSION vector` runs on first migrate.
7. **Tests** — `pytest` suite covering authorization/tenant isolation, evidence
   validation, deletion, retries, and the full upload→analysis→report flow.
8. **Local infrastructure** — `docker-compose.yml` (Postgres+pgvector, Redis, and
   optional api/worker/beat), `Dockerfile`, `.env.example`.
9. **Manual verification** — migrations applied, `seed_demo` populated a workspace,
   HTTP smoke test of `/healthz`, `/readyz` and `/api/v1/meta/enums`.
10. **Frontend** — Vite + React + TypeScript SPA, validated with a strict
    `tsc --noEmit && vite build`.
11. **Docs** — architecture, security overview, privacy pack, deployment and Azure
    notes.
12. **Azure infrastructure** — Bicep templates + `azd` config + GitHub Actions CI/CD.

---

## 3. Tech stack and versions

### Backend (Python) — `backend/requirements.txt`

| Package | Version | Why it's used |
|---|---|---|
| Django | 5.1.6 | Web framework, ORM, auth, admin, migrations |
| djangorestframework | 3.15.2 | REST API, serializers, viewsets, throttling |
| django-cors-headers | 4.7.0 | CORS for the separate SPA origin |
| django-filter | 24.3 | Filtering on list endpoints |
| psycopg[binary] | 3.2.4 | PostgreSQL driver (Django 5 uses psycopg 3) |
| pgvector | 0.3.6 | Django integration for the `vector` column type |
| celery | 5.4.0 | Background workers (ingest + analysis) |
| redis | 5.2.1 | Celery broker/result client |
| gunicorn | 23.0.0 | Production WSGI server |
| whitenoise | 6.8.2 | Static file serving for the API/Django admin |
| django-environ | 0.11.2 | 12-factor config from environment/.env |
| pydantic | 2.10.6 | Validation of analyzer (AI) structured output |
| pypdf | 5.1.0 | PDF text extraction |
| python-docx | 1.1.2 | DOCX text extraction |
| openpyxl | 3.1.5 | XLSX text extraction |
| python-magic | 0.4.27 | Content-type sniffing on upload |
| pytesseract | 0.3.13 | Optional OCR (only if `OCR_PROVIDER=tesseract`) |
| pdf2image | 1.17.0 | Rasterize PDFs for OCR |
| scikit-learn | 1.6.1 | Offline, deterministic hashing embeddings |
| numpy | 2.2.1 | Vector math for embeddings |
| django-storages[azure] | 1.14.4 | Blob storage backend |
| azure-storage-blob | 12.24.1 | Azure Blob SDK (lazy import) |
| azure-identity | 1.20.0 | Managed identity / DefaultAzureCredential |
| azure-keyvault-secrets | 4.9.0 | Key Vault secret provider (lazy import) |
| pytest | 8.3.4 | Test framework |
| pytest-django | 4.9.0 | Django test integration |
| pytest-cov | 6.0.0 | Coverage plugin |
| responses | 0.25.5 | HTTP mocking for adapter tests |
| ruff | 0.9.3 | Linter |

### Frontend (Node) — `frontend/package.json`

| Package | Version | Why it's used |
|---|---|---|
| react | 18.3.1 | UI library |
| react-dom | 18.3.1 | DOM renderer |
| react-router-dom | ^6.30.6 | Client-side routing |
| @tanstack/react-query | 5.59.16 | Server-state / data fetching & caching |
| typescript | 5.6.3 | Type safety (strict mode) |
| vite | ^5.4.21 | Dev server + bundler |
| @vitejs/plugin-react | 4.3.3 | React fast-refresh / JSX |
| @types/react | 18.3.12 | React typings |
| @types/react-dom | 18.3.1 | ReactDOM typings |

### Infrastructure & tooling

| Tool | Version (this machine) | Role |
|---|---|---|
| Python | 3.13.5 (Docker image uses 3.12-slim) | Backend runtime |
| pip | 26.0.1 | Python deps |
| Node.js | 24.12.0 | Frontend build |
| npm | 11.6.2 | Frontend deps |
| Docker | 29.7.2 | Local containers |
| Git | 2.51.0 | Version control |
| GitHub CLI (`gh`) | 2.98.0 | Repo creation/push |
| Bicep (via `az`) | *not installed here* | Azure IaC (validate before deploy) |

---

## 4. Project structure

```
backend/
  config/                 Django project
    settings/             base.py | local.py | production.py | test.py
    urls.py, wsgi.py, asgi.py, celery.py
  apps/
    common/               adapters, analyzer, audit, health, permissions,
                          logging, pagination, exceptions, constants
    accounts/             custom email-login user
    workspaces/           Workspace + Membership + roles
    documents/            upload, extraction, passages/embeddings, deletion
    analysis/             retrieval, jobs, findings, evidence, reports
    privacy/              export + deletion requests
  Dockerfile, docker-entrypoint.sh, requirements.txt, pytest.ini, conftest.py
frontend/
  src/api/                client.ts, types.ts, endpoints.ts
  src/pages/              Login, Workspaces, Documents, Analyses, Findings, Privacy
  src/components/         header, badges, states, loading
  src/session.tsx, src/App.tsx, src/main.tsx, src/styles.css
  vite.config.ts, tsconfig.json, index.html
infra/                    main.bicep, modules/{postgres,container-apps}.bicep,
                          main.parameters.json
docs/                     architecture, security, privacy/*, deployment/*, azure/*
.github/workflows/        ci.yml, deploy.yml
docker-compose.yml, azure.yaml, .env.example, README.md, BUILD.md
```

---

## 5. Docker: what was used and why

### 5.1 Images in `docker-compose.yml`

| Service | Image | Purpose | Host port |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | PostgreSQL 16 **with the `vector` extension** pre-installed (mirrors Azure Database for PostgreSQL Flexible Server) | **5433 → 5432** |
| `redis` | `redis:7-alpine` | Celery broker + result backend | 6379 |
| `api` | built from `./backend` | Django REST API (`runserver` in dev) | 8000 |
| `worker` | built from `./backend` | Celery worker (ingest + analysis) | — |
| `beat` | built from `./backend` | Celery beat scheduler | — |

- **Why port 5433?** A local PostgreSQL already occupied 5432 on this machine, so
  the container is published on **5433** and `DATABASE_URL` points at
  `localhost:5433`. Inside the compose network the API/worker still talk to `db:5432`.
- **Volumes:** `pgdata` (database) and `local_storage` (uploaded files when
  `STORAGE_BACKEND=local`).
- **Health checks:** `pg_isready` for Postgres and `redis-cli ping` for Redis; `api`,
  `worker` and `beat` wait for `service_healthy`.
- **Why pgvector/pgvector:pg16:** it ships the modern `pgvector` extension, so the
  `Passage.embedding` `vector(384)` column and cosine/L2 similarity search work out
  of the box locally, matching the Azure target.

Typical usage during the build:

```powershell
docker compose up -d db redis          # just the infrastructure
docker compose up --build              # api + worker + beat + db + redis
docker compose config --quiet          # validate the compose file
```

### 5.2 `backend/Dockerfile`

- Base: `python:3.12-slim`.
- Installs OS packages: `build-essential`, `libpq-dev` (build/psycopg),
  `tesseract-ocr` + `poppler-utils` (optional local OCR).
- `pip install -r requirements.txt`, then copies the project.
- Creates a non-root `app` user; makes `local_storage`.
- Normalises the entrypoint line endings and marks it executable, then sets
  `ENTRYPOINT ["./docker-entrypoint.sh"]` and
  `CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]`.

### 5.3 `backend/docker-entrypoint.sh`

- Runs `python manage.py migrate --noinput` **only if `RUN_MIGRATIONS=true`** (so
  multiple replicas don't race), then `exec`s the command.
- In production, migrations are run by a dedicated **Container Apps job**
  (`<prefix>-migrate`) triggered by CD — not by the web replicas.

---

## 6. Running locally (host, no Docker for the app)

```powershell
Copy-Item .env.example .env
docker compose up -d db redis

python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt

cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py seed_demo      # demo user + sample data
..\.venv\Scripts\python manage.py runserver       # http://127.0.0.1:8000

# separate terminal
..\.venv\Scripts\python -m celery -A config worker -l info

# frontend
cd ..\frontend
npm install
npm run dev                                        # http://localhost:5173 (proxies /api)
```

Demo credentials from `seed_demo`: `demo@example.test` / `demo-pass-12345`.

---

## 7. Configuration (environment variables)

All configuration is environment-driven (`backend/config/settings/base.py` via
`django-environ`). See `.env.example` for the full list. Key groups:

- **Core:** `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_CORS_ALLOWED_ORIGINS`.
- **Database:** `DATABASE_URL` (local default `postgres://...@localhost:5433/sourcecheck`),
  `EMBEDDING_DIM` (default 384).
- **Queue:** `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
- **Adapters:** `STORAGE_BACKEND` (`local`|`azure`), `VECTOR_STORE` (`pgvector`),
  `OCR_PROVIDER` (`none`|`tesseract`), `ANALYZER_BACKEND`
  (`rules`|`openai_compatible`|`azure_openai`).
- **Azure:** `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER`,
  `AZURE_STORAGE_AUTH`, `AZURE_KEY_VAULT_URL`, `SECRET_PROVIDER` (`env`|`key_vault`),
  `AZURE_OPENAI_*` / `AI_*`.
- **Privacy:** `DATA_REGION`, `DEFAULT_RETENTION_DAYS`, `LOG_DOCUMENT_TEXT` (must
  stay `false`).

---

## 8. Adapters (ports & adapters)

Business logic depends only on interfaces; implementations are selected by env var
and imported lazily:

| Interface | Local default | Azure/other option |
|---|---|---|
| `StorageBackend` | `LocalStorage` (filesystem) | `AzureBlobStorage` (managed identity) |
| `VectorStore` | `PgVectorStore` | pgvector on Azure PostgreSQL |
| `EmbeddingBackend` | `HashingEmbedder` (offline, deterministic) | — |
| `OcrProvider` | `NullOcr` (disabled) | `TesseractOcr` |
| `Analyzer` | `RulesAnalyzer` (offline) | `OpenAICompatibleAnalyzer`, `AzureOpenAIAnalyzer` |
| Secrets | `env` | Key Vault (`key_vault`) |

Because of this, the app boots and its tests pass with **no Azure services**.

---

## 9. Database & search

- PostgreSQL with the **`vector`** extension (pgvector). A
  `VectorExtension()` operation is added to `apps/documents/migrations/0001_initial.py`
  so the extension is created on first migrate.
- Text is chunked into overlapping **Passages** (`~1200` chars, `200` overlap) with
  page + character offsets.
- Retrieval for analysis is **hybrid**: semantic (pgvector) + keyword/fuzzy, scoped
  to the workspace's **source** documents only.
- Every evidence id the analyzer returns is **validated** (exists, same workspace,
  belongs to a source document) before anything is persisted.

---

## 10. Testing & linting

```powershell
cd backend
..\.venv\Scripts\python -m pytest        # 23 tests (settings: config.settings.test)
..\.venv\Scripts\python -m ruff check .  # clean
..\.venv\Scripts\python manage.py check  # no issues
```

- `pytest.ini` uses `config.settings.test`, where Celery runs **eagerly**
  (`CELERY_TASK_ALWAYS_EAGER=True`), so tests need no broker.
- Coverage includes: cross-workspace isolation, evidence-id validation, document
  deletion, task retry, upload→analysis→report flow.

Frontend:

```powershell
cd frontend
npm run build        # tsc --noEmit (strict) && vite build
```

---

## 11. CI/CD (GitHub Actions)

- **`.github/workflows/ci.yml`**
  - Backend job: Python 3.12, Postgres (`pgvector/pgvector:pg16`) + Redis service
    containers, `ruff`, `pytest`.
  - Frontend job: Node 20, `npm ci`, `npm run build`.
- **`.github/workflows/deploy.yml`**
  - Auth to Azure with GitHub **OIDC** (no stored secrets).
  - Build the backend image, push to ACR (tag = git SHA).
  - Run migrations via the Container Apps `-migrate` job.
  - Roll the image out to `web`, `worker`, `beat`.
  - Smoke-test `https://<web-fqdn>/healthz`.

---

## 12. Azure infrastructure (Bicep)

`infra/main.bicep` (resource-group scope) + `infra/modules/`. Resources created:

| Resource | Notes |
|---|---|
| Log Analytics + Application Insights | Logging/metrics; connected to the app env |
| Azure Container Registry | Basic SKU; images pushed by CD |
| PostgreSQL Flexible Server | v16, `azure.extensions=VECTOR` (pgvector), 14-day backups |
| Storage Account + `documents` container | Blob storage for originals/exports |
| Azure Cache for Redis | Celery broker/result |
| Key Vault | RBAC; holds `django-secret-key`, `database-url`, `ai-api-key` |
| Container Apps environment | Backed by Log Analytics |
| Container Apps: `web`, `worker`, `beat` | System-assigned identities |
| Container Apps job: `-migrate` | Runs `manage.py migrate` per release |

Each app identity is granted Key Vault **Secrets User**, ACR **Pull**, and Storage
Blob **Data Contributor**. `azure.yaml` configures `azd provision`.

> The Bicep could **not** be compiled here (`az`/Bicep is not installed on this
> machine). Validate with `az bicep build --file infra/main.bicep` before deploying.

---

## 13. Design principles applied

- **Runs with no cloud credentials** — every external dependency has an offline
  default behind an adapter.
- **Tenant isolation** — every endpoint and task is workspace-scoped; cross-tenant
  access returns 404.
- **Evidence integrity** — analyzer citations are validated before persistence;
  the model cannot invent evidence.
- **Privacy-preserving logs** — document text is never logged.
- **Explicit legal honesty** — the "unsupported ≠ false" distinction is code, and
  legal decisions are listed in `docs/privacy/decisions-needed.md` rather than
  assumed.

---

## 14. Current limitations / next steps

- Bicep not yet validated against a real Azure subscription.
- Automatic retention purge job is a roadmap item (`retention_days` is stored but
  not yet enforced on a schedule).
- No MFA/SSO yet (Entra ID is the documented upgrade path); no upload antivirus.
- The default analyzer is the offline `rules` engine; AI/OCR require an approved
  subprocessor (see `docs/privacy/`).
