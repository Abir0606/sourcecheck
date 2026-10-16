# Decisions needed before production (do not invent these)

These are **legal/operational decisions for the controller, DPO, and qualified
counsel**. The software must not assume answers. Resolve each and record where it
lives (ROPA, DPIA, privacy notice, contracts, deployment config).

1. **Lawful basis** for each processing purpose (verification; writing feedback;
   audit; security logging).
2. **Special-category condition** (Art. 9 EU/UK GDPR) if documents may contain such data.
3. **Controller / processor roles** — who is the controller for uploaded document
   content, and what processor terms apply.
4. **Retention periods** per data class (see `retention-schedule.md`).
5. **Cross-border transfer mechanism** if any subprocessor processes data outside
   the chosen region (SCCs / IDTA / adequacy — decide and document).
6. **Data residency** requirements: whether the organisation needs **separate EU and
   UK environments**, and the exact Azure region(s) (see `../azure/region-verification.md`).
   A region choice alone does not guarantee compliance.
7. **AI/OCR subprocessor approval** (security/privacy review, provider retention,
   no-training settings, DPIA impact).
8. **Whether a DPIA is required** and its outcome.
9. **Privacy notice** content (purposes, recipients, rights, contact).
10. **Deletion vs backups vs legal hold** reconciliation.
11. **Access control policy** — who may create workspaces, invite members, export.
12. **Incident response / breach notification** ownership and timelines.
13. **Audit retention** and who reviews audit events.
14. **Acceptability of uploading any given document corpus** (contracts, client data,
    privileged material).

Until these are decided, treat the deployment as **development only**.
