// PostgreSQL Flexible Server with the pgvector extension enabled.
// pgvector requires `VECTOR` in the server parameter `azure.extensions`.
param location string
param serverName string
param administratorLogin string
@secure()
param administratorLoginPassword string
param databaseName string
param tags object = {}

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'   // Burstable — review SKU for production load
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 14
      geoRedundantBackup: 'Disabled'   // set 'Enabled' for cross-region backups
    }
    highAvailability: {
      mode: 'Disabled'                 // set 'ZoneRedundant' for production HA
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Allow the container apps (which egress via shared IPs) to reach the server.
// For production, prefer private endpoints + a VNet-integrated environment.
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: server
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Enable pgvector. The exact allow-list value is `VECTOR`.
resource pgvector 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  parent: server
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR'
    source: 'user-override'
  }
}

output host string = server.properties.fullyQualifiedDomainName
output serverName string = server.name
