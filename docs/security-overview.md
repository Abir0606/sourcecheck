# Security overview

Technical controls in the application. Infrastructure controls live in `infra/`
and the deployment checklist. This is a description of what the code does, not a
certification.

## Identity & sessions
- Email/password auth; passwords hashed (Argon2/PBKDF2 via Django).
- Session cookies: `HttpOnly`, `SameSite=Lax`, `Secure` in production.
- CSRF protection on all state-changing requests (SPA reads the `csrftoken` cookie
  and sends `X-CSRFToken`).
- Login throttled (`anon` scope); password validators enforced.

## Authorization
- Workspace-scoped on **every** API endpoint and background task
  (`apps/common/permissions.py`).
- Roles: owner, admin, editor, viewer. Writes require editor+; admin actions
  (settings, deletion) require admin+.
- Cross-tenant access returns **404** (no existence leak).
- Evidence IDs validated to belong to the same workspace before persistence.

## Input & file handling
- Extension allow-list and max size; empty/corrupt/unsupported files produce clear
  statuses, not crashes.
- Storage keys are sanitised (`workspaces/{id}/documents/{doc_id}/{name}`); path
  traversal rejected.
- Untrusted document text never overrides system instructions and cannot trigger
  tools (prompt-injection containment).

## Abuse & resource limits
- DRF throttling scopes: `anon`, `user`, `uploads`, `analyses`.
- Celery time limits and bounded retries.

## Data protection
- TLS in transit (platform ingress); encryption at rest by Azure services.
- Deletion flow removes originals, pages, passages, embeddings, findings; export
  bundles expire after 24h.
- Privacy-preserving logs: no document text, no passage content; only ids/counts/status.

## Secrets
- Local: `.env`. Production: Azure Key Vault via managed identity
  (`SECRET_PROVIDER=key_vault`). Rotation plan in `deployment/azure-checklist.md`.

## Auditing
- `AuditEvent` records auth, uploads, deletions, analysis requests, reviews, exports,
  and settings changes (actor, action, object, IP, UA, timestamp).

## Out of scope / to add before production
- MFA / SSO (Entra ID) — documented upgrade path.
- Antivirus scanning of uploads.
- Automatic retention purge job.
- WAF / rate limiting at the edge.
- Penetration test.
