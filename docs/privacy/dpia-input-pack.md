# DPIA input pack (draft for expert review)

This pack gathers the factual/technical inputs a DPIA needs. It deliberately does
**not** conclude on necessity, proportionality, or risk acceptance — those require
the controller, DPO, and qualified counsel.

## 1. Describe the processing

- **Purpose:** verify claims/citations in a target document against user-supplied
  source documents. Secondary feature: general writing feedback.
- **Nature:** upload, text extraction (OCR optional), semantic + keyword retrieval,
  rule-based or AI assessment, human review, export/deletion.
- **Scope:** free-form documents that may contain any personal data, including
  special-category data.
- **Context:** B2B/organisational document review; internal users.
- **Recipients:** within the controller's environment; optionally an AI/OCR
  subprocessor if enabled.

## 2. Necessity & proportionality (questions for the controller)

- What is the lawful basis (and, if relevant, Art. 9 condition)? *(Not assumed.)*
- Is there a less intrusive way to achieve the purpose?
- Is AI-assisted assessment necessary, or would exact/fuzzy matching suffice?
- Could documents be minimised/redacted before upload?

## 3. Risks to assess

| Risk | Technical facts relevant to the assessment |
|---|---|
| Unauthorised access | Workspace-scoped authz; roles; sessions/CSRF; 404 on cross-tenant. |
| Accidental disclosure to AI subprocessor | Only target passage + retrieved evidence are sent; prompts treat text as untrusted; provider retention must be verified. |
| Over-retention | Manual deletion + export TTL exist; **automatic retention purge is not yet implemented**. |
| Data in logs | Application logs exclude document text; platform/telemetry logs must be reviewed. |
| Re-identification in findings | Findings quote passages; access is workspace-scoped. |
| Transfer outside region | Only if non-regional subprocessors enabled. |

## 4. Measures already implemented (technical)

- Least-privilege roles; server-side workspace authorization on every endpoint/task.
- CSRF + secure cookie settings; rate-limit scopes (`uploads`, `analyses`).
- File type/size allow-list; safe storage keys; content hashing.
- Evidence-ID validation before persistence.
- Deletion/export flows covering originals, extracted text, embeddings, results.
- Encryption in transit; encryption at rest (platform-managed by Azure services).
- Privacy-preserving structured logs.

## 5. Open decisions (must be resolved before production)

See `decisions-needed.md`. The DPIA cannot be finalised without them.

## 6. Sign-off

| Role | Name | Date |
|---|---|---|
| Controller | | |
| DPO | | |
| Security | | |
