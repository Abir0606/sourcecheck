# Deployment: local

See the root `README.md` for the full quick start. Summary:

1. `Copy-Item .env.example .env`
2. `docker compose up -d db redis` (PostgreSQL+pgvector on host port 5433, Redis on 6379)
3. Backend: create venv, `pip install -r backend/requirements.txt`, `migrate`, `runserver`
4. Worker: `celery -A config worker -l info`
5. Frontend: `npm install`, `npm run dev` (proxies `/api` to the API)

Or `docker compose up --build` to run api + worker + beat + db + redis.

## Things that are local-only
- Filesystem object storage (`local_storage/`).
- Django session auth without SSO.
- Offline `rules` analyzer / no OCR (unless `OCR_PROVIDER=tesseract`).
- `.env` secrets.

## Health checks
- `GET /healthz` — liveness.
- `GET /readyz` — checks DB and storage; returns 503 when degraded.

## Backups (local)
Local Postgres data lives in the `sourcecheck_pgdata` volume. It is **not** backed
up automatically. This is intentional: local is for development.
