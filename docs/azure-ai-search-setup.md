# Azure AI Search reference setup

This reproducible setup creates a Basic Azure AI Search service for the existing
`cepio-demo-rg` demo and grants the system-assigned managed identity of
`cepio-demo-31d48` the Search roles needed to manage the service and read/write
index data. It disables local/API-key authentication. It does not change the
App Service deployment workflow or add a CEPIO search adapter.

## Prerequisites

- Azure CLI logged in to the intended tenant and subscription.
- The `Microsoft.Search` resource provider registered in that subscription.
- Permissions to create Azure AI Search services in `cepio-demo-rg` and to
  create role assignments at the Search service scope (for example, Resource
  Group Contributor plus Role Based Access Control Administrator).
- The existing App Service has a system-assigned managed identity.
- `cepio-demo-search` is available as a globally unique Search service name.

The Bicep deployment enables public network access for this engineering proof.
Use network restrictions/private endpoints before using sensitive data or
promoting beyond the demo environment.

## Deploy

From the repository root, select the same subscription as the App Service and
register the provider if needed:

```bash
az account show --output table
az account set --subscription <subscription-id>
az provider register --namespace Microsoft.Search --wait
az provider show --namespace Microsoft.Search --query registrationState --output tsv
```

Get the App Service identity and region, then deploy the Bicep template:

```bash
resource_group=cepio-demo-rg
app_name=cepio-demo-31d48
app_principal_id="$(az webapp identity show \
  --resource-group "$resource_group" \
  --name "$app_name" \
  --query principalId \
  --output tsv)"
search_location="$(az webapp show \
  --resource-group "$resource_group" \
  --name "$app_name" \
  --query location \
  --output tsv)"

test -n "$app_principal_id" || {
  echo "The App Service system-assigned managed identity is not enabled." >&2
  exit 1
}

az deployment group create \
  --resource-group "$resource_group" \
  --name cepio-demo-search-rbac \
  --template-file deploy/search/main.bicep \
  --parameters appServicePrincipalId="$app_principal_id" location="$search_location"
```

The deployment output `searchEndpoint` is the service endpoint. It can also be
read independently:

```bash
az deployment group show \
  --resource-group cepio-demo-rg \
  --name cepio-demo-search-rbac \
  --query properties.outputs.searchEndpoint.value \
  --output tsv
```

The endpoint has the form
`https://cepio-demo-search.search.windows.net`. The suggested name may already
be taken because Search service names are globally unique; if so, pass an
available name with `--parameters searchServiceName=<globally-unique-name>`.

## Assigned roles and identity boundary

The Bicep template assigns these built-in roles at the Search service scope:

| Role | Purpose |
|---|---|
| Search Service Contributor | Manage Search service objects and configuration |
| Search Index Data Contributor | Load, update and delete index documents |
| Search Index Data Reader | Query index documents |

`disableLocalAuth: true` prevents CEPIO from relying on Search admin/query API
keys. The managed identity authenticates the App Service workload to Search;
it does not replace CEPIO's Entra-authenticated caller identity or its
authorization checks. Role assignment propagation can take several minutes.

This setup provisions infrastructure only. It does not configure an endpoint
on the App Service, create indexes, ingest data, or claim that Azure AI Search
is a required CEPIO backend. See [Retrieval & Indexing](retrieval-indexing-architecture.md)
for the source-neutral adapter boundary.
