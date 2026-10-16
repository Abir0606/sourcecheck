# Retention schedule (template — values are decisions to make)

The application **stores** a configurable `retention_days` per workspace and
provides deletion/export flows. The **values** below must be set by the controller
(and recorded in the ROPA/retention policy). None are legal advice.

| Data class | Suggested default (EDIT) | Enforcement mechanism |
|---|---|---|
| Account data | TBD | Manual / admin deprovision |
| Uploaded originals | TBD | `DeletionRequest` (scope=documents) |
| Extracted text + passages + embeddings | TBD | Cascade with document deletion |
| Analysis results (findings) | TBD | `DeletionRequest` (scope=analysis) |
| Exports | 24 hours (implementation default) | `ExportJob.expires_at` |
| Audit events | TBD (often longer, for accountability) | Not auto-deleted by app |
| Backups | TBD | Depends on DB backup configuration — see deployment docs |
| Logs/telemetry | TBD | Set at the monitoring layer |

## Notes

- `retention_days=0` currently means **"retain until deleted"**. A scheduled purge
  job driven by `retention_days` is a **roadmap item**, not yet implemented — do not
  assume automatic deletion happens yet.
- Deletion must be reconciled with **backups** and **legal-hold** obligations; that
  reconciliation is an operational decision.
- Logs and telemetry can contain personal data (IP addresses); include them in the
  retention policy.
