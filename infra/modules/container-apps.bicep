// Container Apps: web (ingress), worker, beat — sharing one environment.
param location string
param environmentId string
param namePrefix string
param tags object = {}
param containerImage string
param acrLoginServer string

@secure()
param redisKey string

param redisHostName string
param storageAccountName string
param databaseUrlSecretUri string
param djangoSecretUri string
param aiKeySecretUri string

param allowedOrigin string
param dataRegion string
param storageBackend string
@allowed(['rules', 'openai', 'azure_openai'])
param analyzerBackend string
param aiEndpoint string
param applicationInsightsConnectionString string
param keyVaultUri string

var secrets = [
  { name: 'database-url', keyVaultUrl: databaseUrlSecretUri, identity: 'system' }
  { name: 'django-secret-key', keyVaultUrl: djangoSecretUri, identity: 'system' }
  { name: 'ai-api-key', keyVaultUrl: aiKeySecretUri, identity: 'system' }
]

var commonEnv = [
  { name: 'DJANGO_SETTINGS_MODULE', value: 'config.settings.production' }
  { name: 'DJANGO_DEBUG', value: 'false' }
  { name: 'DJANGO_ALLOWED_HOSTS', value: '*' }            // tighten to the app FQDN
  { name: 'DJANGO_CORS_ALLOWED_ORIGINS', value: allowedOrigin }
  { name: 'DJANGO_CSRF_TRUSTED_ORIGINS', value: allowedOrigin }
  { name: 'DJANGO_SECURE_SSL_REDIRECT', value: 'false' } // ingress terminates TLS
  { name: 'SECRET_PROVIDER', value: 'key_vault' }
  { name: 'AZURE_KEY_VAULT_URL', value: keyVaultUri }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'DJANGO_SECRET_KEY', secretRef: 'django-secret-key' }
  { name: 'CELERY_BROKER_URL', value: 'rediss://:${redisKey}@${redisHostName}:6380/0' }
  { name: 'CELERY_RESULT_BACKEND', value: 'rediss://:${redisKey}@${redisHostName}:6380/1' }
  { name: 'STORAGE_BACKEND', value: storageBackend }
  { name: 'AZURE_STORAGE_ACCOUNT_URL', value: 'https://${storageAccountName}.blob.core.windows.net' }
  { name: 'AZURE_STORAGE_CONTAINER', value: 'documents' }
  { name: 'AZURE_STORAGE_AUTH', value: 'managed_identity' }
  { name: 'ANALYZER_BACKEND', value: analyzerBackend }
  { name: 'AI_API_KEY', secretRef: 'ai-api-key' }
  { name: 'AZURE_OPENAI_ENDPOINT', value: aiEndpoint }
  { name: 'AI_BASE_URL', value: aiEndpoint }
  { name: 'DATA_REGION', value: dataRegion }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
]

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-web'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [ { server: acrLoginServer, identity: 'system' } ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'web'
          image: containerImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/healthz', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/readyz', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 15
            }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource workerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-worker'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      registries: [ { server: acrLoginServer, identity: 'system' } ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: containerImage
          command: ['celery']
          args: ['-A', 'config', 'worker', '-l', 'info']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 4 }
    }
  }
}

resource beatApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-beat'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      registries: [ { server: acrLoginServer, identity: 'system' } ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'beat'
          image: containerImage
          command: ['celery']
          args: ['-A', 'config', 'beat', '-l', 'info']
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: commonEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 } // beat must be a singleton
    }
  }
}

// Manual-trigger job used by CD to run `manage.py migrate` once per release.
resource migrateJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${namePrefix}-migrate'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      registries: [ { server: acrLoginServer, identity: 'system' } ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: containerImage
          command: ['python']
          args: ['manage.py', 'migrate', '--noinput']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonEnv
        }
      ]
    }
  }
}

output webName string = webApp.name
output workerName string = workerApp.name
output beatName string = beatApp.name
output migrateJobName string = migrateJob.name
output webPrincipalId string = webApp.identity.principalId
output workerPrincipalId string = workerApp.identity.principalId
output beatPrincipalId string = beatApp.identity.principalId
output migrateJobPrincipalId string = migrateJob.identity.principalId
