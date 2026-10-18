param location string = resourceGroup().location
param suffix string
param tenantId string
param apiAudience string
param profiles string = ''
param containerImage string = 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'

var acrName = 'acrcepiodev${suffix}'
var planName = 'asp-cepio-dev-${suffix}'
var appName = 'app-cepio-api-dev-${suffix}'
var logName = 'log-cepio-dev-${suffix}'
var appInsightsName = 'ai-cepio-dev-${suffix}'
var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

resource log 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    retentionInDays: 30
  }
  sku: {
    name: 'PerGB2018'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: log.id
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
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
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      healthCheckPath: '/api/v1/health'
      http20Enabled: true
      ftpsState: 'Disabled'
      minimumTlsVersion: '1.2'
      appSettings: [
        { name: 'PORT', value: '8000' }
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'true' }
        { name: 'CEPIO_ENVIRONMENT', value: 'dev' }
        { name: 'CEPIO_DB_URL', value: 'sqlite:////home/data/cepio.db' }
        { name: 'CEPIO_AUTH_MODE', value: 'entra' }
        { name: 'CEPIO_ENTRA_TENANT_ID', value: tenantId }
        { name: 'CEPIO_ENTRA_AUDIENCE', value: apiAudience }
        { name: 'CEPIO_PROFILES', value: profiles }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
      ]
    }
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, app.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    roleDefinitionId: acrPullRoleDefinitionId
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output appName string = app.name
output appUrl string = 'https://${app.properties.defaultHostName}'
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output appPrincipalId string = app.identity.principalId
