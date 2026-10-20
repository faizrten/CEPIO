param location string = resourceGroup().location
param appName string
param containerImage string
param tenantId string
param apiAudience string
param profiles string = ''

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'P1v3'
    tier: 'PremiumV3'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource app 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerImage}'
      alwaysOn: true
      healthCheckPath: '/api/v1/health'
      appSettings: [
        { name: 'PORT', value: '8000' }
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'true' }
        { name: 'CEPIO_ENVIRONMENT', value: 'production' }
        { name: 'CEPIO_DB_URL', value: 'sqlite:////home/data/cepio.db' }
        { name: 'CEPIO_AUTH_MODE', value: 'entra' }
        { name: 'CEPIO_ENTRA_TENANT_ID', value: tenantId }
        { name: 'CEPIO_ENTRA_AUDIENCE', value: apiAudience }
        { name: 'CEPIO_PROFILES', value: profiles }
      ]
    }
  }
}

resource webConfig 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: app
  name: 'web'
  properties: {
    ftpsState: 'Disabled'
    minTlsVersion: '1.2'
    http20Enabled: true
    alwaysOn: true
  }
}

output appUrl string = 'https://${app.properties.defaultHostName}'
output principalId string = app.identity.principalId
