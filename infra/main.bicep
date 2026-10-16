// ---------------------------------------------------------------------------
// SourceCheck — Azure infrastructure (Bicep)
//
// Scope: resource group (create it first, or let `azd` target an existing one):
//   az group create -n rg-sourcecheck-dev -l westeurope
//   az deployment group create -g rg-sourcecheck-dev -f infra/main.bicep \
//     -p infra/main.parameters.json
//
// Validate before deploying:  az bicep build --file infra/main.bicep
//
// This template provisions infrastructure only. It does NOT make the service
// legally compliant — see ../docs/privacy/decisions-needed.md.
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

@description('Azure region for all regional resources. Verify service availability — see docs/azure/region-verification.md.')
param location string = resourceGroup().location

@description('Short environment name (dev | staging | prod).')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Name prefix for resources.')
param prefix string = 'sourcecheck'

@description('Logical data region label persisted for the app (e.g. eu | uk).')
param dataRegion string = 'eu'

@minLength(3)
param postgresAdminLogin string = 'sourcecheckadmin'

@secure()
@minLength(8)
param postgresAdminPassword string

@secure()
@minLength(16)
param djangoSecretKey string

@description('Container image for web/worker. Used by CD (azd) or manual deploy.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Allowed CORS origin for the SPA (Static Web App URL).')
param allowedOrigin string = 'http://localhost:5173'

@description('Analyzer backend: rules (offline) | openai | azure_openai.')
@allowed(['rules', 'openai', 'azure_openai'])
param analyzerBackend string = 'rules'

@description('Storage backend: local | azure. Azure is required in production.')
@allowed(['local', 'azure'])
param storageBackend string = 'azure'

@description('Optional AI endpoint/key. Leave empty to disable AI.')
param aiEndpoint string = ''
@secure()
param aiKey string = ''

param tags object = {
  application: 'sourcecheck'
  'data-region': dataRegion
}

var suffix = uniqueString(resourceGroup().id, environmentName)
var nameBase = '${prefix}-${environmentName}'
var acrName = '${prefix}${environmentName}${suffix}'      // alphanumeric, <=50
var storageName = '${prefix}${environmentName}${suffix}'  // lowercase alnum, <=24
var kvName = '${prefix}-${environmentName}-${suffix}'     // <=24 chars
var redisName = '${nameBase}-${suffix}'
var pgServerName = '${nameBase}-pg-${suffix}'
var pgDatabaseName = 'sourcecheck'

// ------------------------------------------------------------------ monitoring
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${nameBase}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${nameBase}-ai'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ------------------------------------------------------------------- registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// ------------------------------------------------------------------- postgres
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    serverName: pgServerName
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    databaseName: pgDatabaseName
    tags: tags
  }
}

// -------------------------------------------------------------------- storage
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'documents'
  properties: { publicAccess: 'None' }
}

// ---------------------------------------------------------------------- redis
resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: redisName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// ------------------------------------------------------------------- key vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
  }
}

resource kvSecretDjango 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'django-secret-key'
  properties: { value: djangoSecretKey }
}

resource kvSecretDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgres://${postgresAdminLogin}:${postgresAdminPassword}@${pgServerName}.postgres.database.azure.com:5432/${pgDatabaseName}?sslmode=require'
  }
}

resource kvSecretAiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'ai-api-key'
  properties: { value: aiKey }
}

// ------------------------------------------------------- container apps env
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${nameBase}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ------------------------------------------------------------ container apps
module containerApps 'modules/container-apps.bicep' = {
  name: 'containerApps'
  params: {
    location: location
    environmentId: containerEnv.id
    namePrefix: nameBase
    tags: tags
    containerImage: containerImage
    acrLoginServer: acr.properties.loginServer
    keyVaultUri: keyVault.properties.vaultUri
    redisKey: redis.listKeys().primaryKey
    databaseUrlSecretUri: '${keyVault.properties.vaultUri}secrets/database-url'
    djangoSecretUri: '${keyVault.properties.vaultUri}secrets/django-secret-key'
    aiKeySecretUri: '${keyVault.properties.vaultUri}secrets/ai-api-key'
    allowedOrigin: allowedOrigin
    analyzerBackend: analyzerBackend
    storageBackend: storageBackend
    storageAccountName: storage.name
    redisHostName: redis.properties.hostName
    dataRegion: dataRegion
    aiEndpoint: aiEndpoint
    applicationInsightsConnectionString: appInsights.properties.ConnectionString
  }
}

// ---------------------------------------------- Key Vault access for the apps
// Grants each container app's system-assigned identity read access to secrets.
resource kvSecretsUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
}

resource grantWebKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerApps.outputs.webPrincipalId, 'kv-secrets-user')
  properties: {
    roleDefinitionId: kvSecretsUserRole.id
    principalId: containerApps.outputs.webPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource grantWorkerKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerApps.outputs.workerPrincipalId, 'kv-secrets-user')
  properties: {
    roleDefinitionId: kvSecretsUserRole.id
    principalId: containerApps.outputs.workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource grantBeatKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerApps.outputs.beatPrincipalId, 'kv-secrets-user')
  properties: {
    roleDefinitionId: kvSecretsUserRole.id
    principalId: containerApps.outputs.beatPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ------------------------------- image pull + blob access for the app identities
var appPrincipals = [
  { name: 'web', id: containerApps.outputs.webPrincipalId }
  { name: 'worker', id: containerApps.outputs.workerPrincipalId }
  { name: 'beat', id: containerApps.outputs.beatPrincipalId }
  { name: 'migrate', id: containerApps.outputs.migrateJobPrincipalId }
]

// AcrPull (7f951dda-4ed3-4680-a7ca-43fe172d538d) so Container Apps can pull images.
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for p in appPrincipals: {
  name: guid(acr.id, p.id, 'acrpull')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: p.id
    principalType: 'ServicePrincipal'
  }
}]

// Storage Blob Data Contributor (ba92f5b4-2d11-453d-a403-e96b0029c9fe) for managed-identity blob access.
resource storageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for p in appPrincipals: {
  name: guid(storage.id, p.id, 'blobcontrib')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: p.id
    principalType: 'ServicePrincipal'
  }
}]

// ---------------------------------------------------------------- outputs
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = acr.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_APP_ENV_ID string = containerEnv.id
output WEB_APP_NAME string = containerApps.outputs.webName
output WORKER_APP_NAME string = containerApps.outputs.workerName
output BEAT_APP_NAME string = containerApps.outputs.beatName
output MIGRATE_JOB_NAME string = containerApps.outputs.migrateJobName
output POSTGRES_HOST string = postgres.outputs.host
output STORAGE_ACCOUNT string = storage.name
output KEY_VAULT_NAME string = keyVault.name
