// Opt-in existing-infrastructure-only Azure Container Apps Job.
// Does not provision identities, storage accounts, registries, roles or secrets.
// authorized=false is the default: plan/CI must never deploy a running job.
@description('Explicit release gate; false results in no job resource')
param authorized bool = false

@description('Existing Azure Container Apps managed environment ID')
param containerAppsEnvironmentId string

@description('Existing user-assigned identity resource ID; needs AcrPull, Key Vault secret get and scoped blob RBAC')
param executionIdentityResourceId string

@description('Client ID of the same user-assigned identity, used for Azure Blob authentication')
param executionIdentityClientId string

@description('Existing ACR server, without https://')
param registryServer string

@description('Image built from reviewed commit; no latest tags')
param containerImage string

@description('Existing Blob Storage account endpoint (not a connection string)')
param storageAccountUrl string

@description('Existing private container for evidence manifests')
param storageContainer string

@description('Approved Cognite M2M authority tenant, distinct from the public interactive app identity')
param cogniteM2MTenantId string

@description('Approved Cognite M2M client ID, not the public OID interactive client ID')
param cogniteM2MClientId string

@description('Versioned Key Vault secret URI for Cognite M2M client secret; never a plaintext secret')
param cogniteM2MKeyVaultSecretUrl string

param location string = resourceGroup().location
param jobName string = 'cepio-cognite-oid-m0'

resource job 'Microsoft.App/jobs@2024-03-01' = if (authorized) {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${executionIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 0
      replicaTimeout: 900
      registries: [
        {
          server: registryServer
          identity: executionIdentityResourceId
        }
      ]
      secrets: [
        {
          name: 'cognite-m2m-client-secret'
          keyVaultUrl: cogniteM2MKeyVaultSecretUrl
          identity: executionIdentityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'cognite-oid-inventory'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'COGNITE_OID_PROJECT', value: 'publicdata' }
            { name: 'COGNITE_OID_AUTH_MODE', value: 'client-credentials' }
            { name: 'COGNITE_M2M_TENANT_ID', value: cogniteM2MTenantId }
            { name: 'COGNITE_M2M_CLIENT_ID', value: cogniteM2MClientId }
            { name: 'COGNITE_M2M_CLIENT_SECRET', secretRef: 'cognite-m2m-client-secret' }
            { name: 'AZURE_IDENTITY_CLIENT_ID', value: executionIdentityClientId }
            { name: 'AZURE_BLOB_ACCOUNT_URL', value: storageAccountUrl }
            { name: 'AZURE_BLOB_CONTAINER', value: storageContainer }
            { name: 'COGNITE_OID_FOCUS', value: 'compressor' }
            { name: 'COGNITE_OID_LIMIT', value: '100' }
            { name: 'COGNITE_OID_FOCUS_LIMIT', value: '20' }
          ]
        }
      ]
    }
  }
}

output jobName string = jobName
output deployAuthorized bool = authorized
