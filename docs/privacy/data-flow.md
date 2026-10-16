# Data-flow diagram

```
                    ┌────────────────────────────────────────────────────────────┐
                    │                     Your environment                        │
                    │   (region = DATA_REGION; EU and UK kept separate if needed) │
                    │                                                              │
  User (browser) ──▶│  React SPA ──HTTPS──▶ Django API ──▶ PostgreSQL (+pgvector) │
   [credentials,    │       │                   │                                │
    documents]      │       │                   ├──▶ Object storage (originals,   │
                    │       │                   │        extracted text, exports) │
                    │       │                   │                                │
                    │       │                   └──enqueue──▶ Celery worker ──────┤
                    │       │                                    │               │
                    │       └── poll status ◀── results ──────────┘               │
                    └────────────────────────────────────────────────────────────┘
                                          │ (only if configured)
                                          ▼
                     ┌──────────────────────────────────────────┐
                     │ Optional subprocessors                    │
                     │  • Azure OpenAI / AI provider (analysis)  │
                     │  • Azure AI Document Intelligence (OCR)   │
                     │  • Azure Monitor / Log Analytics (logs)   │
                     └──────────────────────────────────────────┘
```

## Flows and controls

| Flow | Data | Control |
|---|---|---|
| Auth | email, password | Session + CSRF; passwords hashed; throttled login |
| Upload | document bytes | Type/size allow-list; stored under `workspaces/{id}/…` |
| Ingest | extracted text, embeddings | Worker-only; per-workspace scoping |
| Analysis | passages + candidate evidence | Retrieval scoped to workspace source docs; ids validated |
| AI call (optional) | target passage + retrieved evidence only | No whole-document/other-workspace content sent; prompts treat text as untrusted |
| Logs/metrics | ids, counts, timing | **No document text or passage content** |
| Export | full workspace bundle | Explicit request; expires after 24h |
| Deletion | all derived data | Covers blobs, pages, passages, embeddings, findings |

## Cross-border transfers

Transfers occur **only** if a subprocessor outside the chosen region is enabled
(e.g. AI/OCR). Whether a valid transfer mechanism applies is a **decision for the
controller/counsel**, not something this application can assert. Azure's regional
and EU Data Boundary commitments are infrastructure facts to verify per service —
see `../azure/region-verification.md`.
