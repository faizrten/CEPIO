@description('Globally unique Azure AI Search service name.')
param searchServiceName string = 'cepio-demo-search'

@description('Azure region for the Search service; pass the App Service region for the reference proof.')
param location string

@description('Principal ID of the existing App Service system-assigned managed identity.')
param appServicePrincipalId string

var searchServiceContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
)
var searchIndexDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
)
var searchIndexDataReaderRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '1407120a-92aa-4202-b7e9-c0e197c71c8f'
)

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    disableLocalAuth: true
    publicNetworkAccess: 'enabled'
  }
}

resource searchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, appServicePrincipalId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: searchServiceContributorRoleId
    principalId: appServicePrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource searchIndexDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, appServicePrincipalId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: searchIndexDataContributorRoleId
    principalId: appServicePrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource searchIndexDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, appServicePrincipalId, searchIndexDataReaderRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: searchIndexDataReaderRoleId
    principalId: appServicePrincipalId
    principalType: 'ServicePrincipal'
  }
}

output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
