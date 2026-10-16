# Deployment: Azure checklist

Runs the same image locally and on Azure. Infrastructure lives in `infra/`
(Bicep); app delivery in `.github/workflows/deploy.yml`.

> Deploying this software does **not** make the service legally compliant.
> Complete `../privacy/decisions-needed.md` first.

## 0. Decide first
- Region(s) and whether EU/UK separation is required (`../azure/region-verification.md`).
- Whether AI/OCR subprocessors are permitted (`../privacy/subprocessors.md`).
- Retention, lawful basis, transfer mechanism (`../privacy/decisions-needed.md`).

## 1. Provision infrastructure

```powershell
az login
az group create -n rg-sourcecheck-dev -l westeurope
az bicep build --file infra/main.bicep                 # validate
az deployment group create -g rg-sourcecheck-dev -f infra/main.bicep `
  -p infra/main.parameters.json `
  -p postgresAdminPassword='<strong-password>' `
  -p djangoSecretKey='<50+-char-random>'
```

Or with azd (infra-only):

```powershell
azd env new sourcecheck-dev
azd env set AZURE_LOCATION westeurope
azd provision
```

### What gets created
Log Analytics + App Insights, ACR, PostgreSQL Flexible Server (pgvector enabled),
Storage (blob container `documents`), Azure Cache for Redis, Key Vault (RBAC),
Container Apps environment, and Container Apps: `web`, `worker`, `beat`, plus a
`-migrate` job. Each app has a system-assigned identity, granted Key Vault secrets
read, ACR pull, and Storage Blob Data Contributor.

## 2. Wire CI/CD
Create an Entra ID app registration with a **federated credential** for this repo
+ GitHub environment; set repo **variables**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `RESOURCE_PREFIX`
(e.g. `sourcecheck-dev`), `ACR_NAME`. Then run the **Deploy** workflow.

The workflow builds the image, pushes it to ACR, runs the migration job, updates
web/worker/beat, and smoke-tests `/healthz`.

## 3. Configure the SPA
Deploy `frontend/` to Azure Static Web Apps (or any static host). Set
`VITE_API_BASE_URL` to the web app URL and set the API's `allowedOrigin`/
`DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to the SWA URL,
then update `DJANGO_ALLOWED_HOSTS` to the web app FQDN.

## 4. Post-deploy hardening
- [ ] Tighten `DJANGO_ALLOWED_HOSTS` from `*` to the real FQDN.
- [ ] Set `DATA_REGION` to the chosen region label.
- [ ] Confirm `STORAGE_BACKEND=azure` and blob access is managed-identity only.
- [ ] Confirm AI/OCR env is set only if approved; otherwise `ANALYZER_BACKEND=rules`.
- [ ] Enable private networking (VNet-integrated Container Apps env + private
      endpoints for PostgreSQL/Storage/Key Vault) if required.
- [ ] Enable PostgreSQL HA/zone redundancy and geo-redundant backups.
- [ ] Configure alerts (5xx rate, queue depth, DB connections, job failures).
- [ ] Review Key Vault secret rotation (DB password, Django key, AI key).
- [ ] Confirm Log Analytics retention + that no document text is logged.
- [ ] Publish the privacy notice and complete the DPIA sign-off.

## 5. Migrations from now on
Migrations ship automatically: the `-migrate` job runs before rollout. For a
manual run:

```powershell
az containerapp job start -g <rg> -n <prefix>-migrate
```

## 6. Rollback
Container Apps keeps revisions. To roll back the web app:

```powershell
az containerapp revision list -g <rg> -n <prefix>-web -o table
az containerapp revision activate -g <rg> -n <prefix>-web --revision <name>
```

Container images are tagged with the git SHA, so re-deploying a previous SHA is
also possible. **Migrations are not automatically reversible** — plan forward-
compatible migrations.

## 7. Backups & restore
- PostgreSQL: automated backups (retention set in `infra/modules/postgres.bicep`,
  currently 14 days; geo-redundant off — enable for production).
- Storage: enable soft delete + versioning; consider GRS once transfer rules allow.
- **Test a restore** before go-live. Backups contain personal data: include them in
  retention and the ROPA.
