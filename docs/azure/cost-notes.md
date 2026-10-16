# Cost notes (estimates only — verify current prices)

Prices and SKUs change. Use the Azure Pricing Calculator for real numbers. This
lists **which settings affect cost**, not dollar amounts.

## Main cost drivers

| Resource | Affects cost because… | Levers |
|---|---|---|
| Container Apps (web, worker, beat) | Per-vCPU-second/memory-second + replicas | min/max replicas, scale-to-zero, CPU/memory per revision |
| PostgreSQL Flexible Server | Compute tier + storage + backups + HA | SKU (Burstable/GP/Memory), storage GB, retention days, zone-redundant HA on/off |
| Azure Cache for Redis | Tier + size (Basic/Standard/Premium) | cache size, HA, persistence |
| Blob Storage | Storage GB + operations + egress | redundancy (LRS/ZRS/GRS), lifecycle rules, soft-delete retention |
| Container Registry | Per-GB storage | image retention/cleanup |
| Key Vault | Per-operation (cheap) | negligible |
| AI provider | Per-token (analysis) | model choice, passages per claim, batching, caching |
| OCR | Per page (if enabled) | enable only for scanned docs |
| Log Analytics / App Insights | Ingest GB + retention | log verbosity, retention days, sampling |

## Cost-reducing defaults
- Container Apps scale to zero when idle (consider for `worker`/`beat` carefully —
  scale-to-zero can delay async work).
- Use Burstable PostgreSQL for dev/staging; General Purpose for production.
- LRS Blob for dev; ZRS/GRS only where required (and note transfer implications).
- Keep the offline `rules` analyzer in dev/staging to avoid AI token spend.
- Set Log Analytics retention deliberately.

## Environment strategy
Separate dev / staging / prod with **separate** resource groups and parameters so
cost and blast radius are isolated. Tag resources (`env`, `owner`, `data-region`)
for cost reporting.
