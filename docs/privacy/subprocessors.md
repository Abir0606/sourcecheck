# Subprocessors (template)

List every processor/subprocessor actually used, with location and safeguards.
This file is a **template** — populate it from your real deployment. Do not assume
any row below is in use.

| Subprocessor | Purpose | Data | Location/region | Transfer mechanism | Contract |
|---|---|---|---|---|---|
| Microsoft Azure | Hosting (compute, DB, storage, cache, monitoring) | All service data | Set by deployment region(s) | TBD by controller | Microsoft DPA / product terms |
| AI provider (if `ANALYZER_BACKEND` set) | Claim assessment | Target passage + retrieved evidence | Provider-dependent | TBD by controller | Provider DPA |
| OCR provider (if enabled) | Text extraction for scans | Uploaded document | Provider-dependent | TBD by controller | Provider DPA |
| Email provider (if configured) | Transactional email | Account email | Provider-dependent | TBD by controller | Provider DPA |

## Rules

- The default `rules` analyzer is **offline** and involves **no** AI subprocessor.
- With `OCR_PROVIDER=none` and `ANALYZER_BACKEND=rules`, the only processor is Azure.
- Any enabled third party must be added here, assessed for its own transfers, and
  reflected in the privacy notice before production.

## Azure regional/EU Data Boundary

Azure's regional and EU Data Boundary commitments are **infrastructure facts to
verify per service and per region** (see `../azure/region-verification.md`). They
are not, by themselves, proof of GDPR compliance.
