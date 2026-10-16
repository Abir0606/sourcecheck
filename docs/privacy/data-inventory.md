# Data inventory

This is a **technical** inventory of what the application stores. It is not a
record of the controller's lawful basis or retention decisions — see
`decisions-needed.md`.

## Personal data likely present

| Category | Where | Notes |
|---|---|---|
| Account data | `accounts.User` | Email, hashed password, name (optional), last login. |
| Membership/roles | `workspaces.Membership` | Who can access which workspace. |
| Audit events | `common.AuditEvent` | Actor, action, object id, IP, user agent, timestamp. |
| Uploaded documents | Object storage + `documents.Document` | May contain **any** personal data (special category included) — content is controller-determined. |
| Extracted text | `documents.DocumentPage`, `documents.Passage` | Full text, page numbers, embeddings. |
| Analysis results | `analysis.Finding`, `FindingEvidence`, `WritingSuggestion` | Derived from document content. |
| Exports | Object storage (`ExportJob`) | Full bundle of the above; time-limited. |

## Special-category / high-risk note

Uploaded documents are free-form. They **may** contain special-category data
(Art. 9 UK/EU GDPR) or criminal-offence data. The controller must decide whether
an Art. 9 condition applies and whether a DPIA is required (see `dpia-input-pack.md`).

## What the application does NOT store

- No public-internet search results.
- No document contents in application logs (enforced by convention + review;
  `LOG_DOCUMENT_TEXT` exists only to *prohibit* this and must stay `false`).

## Data subjects

Typically workspace users (staff) and any individuals appearing inside uploaded
documents (potentially data subjects with no relationship to the service).
