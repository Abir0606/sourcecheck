# Azure region & service verification

Do **not** assume a service or feature is available in a region, and do **not**
treat a region choice as proof of GDPR compliance. Verify each item below before
claiming a deployment is ready. The default region in `infra/` parameters is
`westeurope`; change it and re-verify.

## Why this matters
- Not every service/SKU is available in every region.
- pgvector requires the `vector` extension to be permitted on the PostgreSQL
  Flexible Server engine version you pick.
- Azure OpenAI model deployments vary by region and are subject to quota.
- Container Apps, Service Bus tiers, and zone redundancy vary by region.

## Verification commands

```powershell
# Available regions + service availability (examples)
az provider show --namespace Microsoft.App --query "resourceTypes[?resourceType=='managedEnvironments'].locations" -o tsv
az postgres flexible-server list-skus --location westeurope -o table
az containerapp list -o table

# PostgreSQL extensions: check `azure.extensions` server parameter includes VECTOR
az postgres flexible-server parameter show --resource-group <rg> --server-name <server> --name azure.extensions

# Container Apps region availability
az provider show --namespace Microsoft.App --query "resourceTypes[].locations" -o tsv
```

For Azure OpenAI, check regional model availability and quota in the Azure portal
(the CLI availability surface is limited and changes frequently).

## Checklist (fill in)

| Item | Value for your deployment | Verified? |
|---|---|---|
| Primary region | (e.g. `westeurope`) | ☐ |
| Secondary/paired region (HA/backups) | | ☐ |
| Container Apps available | | ☐ |
| PostgreSQL Flexible Server + pgvector | engine version + `azure.extensions` includes VECTOR | ☐ |
| Azure Cache for Redis tier available | | ☐ |
| Azure OpenAI deployment (if used) | model + region + quota | ☐ |
| Key Vault available | | ☐ |
| EU vs UK separation required? | decision (see `../privacy/decisions-needed.md`) | ☐ |

## EU / UK separation

If the organisation's residency or transfer requirements demand it, deploy
**separate** environments (separate resource groups/subscriptions, in an EU region
and a UK region) with distinct data, keys, and monitoring. The application supports
this through `DATA_REGION` and fully separate infrastructure — but the requirement
itself is a decision, not a default.
