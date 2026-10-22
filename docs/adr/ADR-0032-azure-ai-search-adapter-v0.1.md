# ADR-0032: Azure AI Search Physical Retrieval Adapter v0.1

- Status: Superseded by ADR-0039 (2026-10-22); historical record only
- Date: 2026-10-20

## Context

CEPIO Retrieval & Indexing v0.1 deliberately made search products replaceable. Memory & Context v0.1 also established that durable knowledge can grow while working context remains bounded.

The next qualification step requires a real external retrieval service at materially larger corpus sizes without allowing the external service to become CEPIO's source of semantic truth.

A development Azure AI Search service is available at `https://cepio-search-dev-31d48.search.windows.net`.

## Decision

Add an optional Azure AI Search physical adapter implementing CEPIO's existing lexical retrieval/index projection contract.

The adapter authenticates keylessly through `DefaultAzureCredential`, uses managed identity in App Service, keeps Azure dependencies in the optional `azure-search` package extra, projects compact `MemoryRecord` objects rather than raw industrial source data, pushes tenant/capability/tag/kind/expiry constraints into OData filters, re-checks tenant and expiry boundaries after Search returns results, treats the Search index as rebuildable and non-authoritative, keeps index management separate from normal query/data-plane access, and provides a synthetic 50K to 500K scale-qualification workflow.

## Security boundary

No Search API keys or client secrets are accepted as CEPIO configuration in this adapter.

Runtime querying uses Search data-plane RBAC. Index schema management remains an administrative/deployment concern.

Foreign-tenant records must be excluded by the Search filter and are still rejected in the adapter and RetrievalEngine if returned.

## Consequences

Positive consequences are validation of CEPIO's backend-neutral retrieval architecture against a managed cloud search engine, a real scalable retrieval projection for the Azure App Service deployment, preserved bounded context and Capability Registry authority, and repeatable corpus-growth measurements.

Trade-offs are that the Azure demo container includes optional Azure Search SDK dependencies, live qualification requires explicit Azure RBAC assignments, index lifecycle and cost become deployment concerns, and vector/hybrid retrieval remains deferred until embedding governance is specified.

## Rejected alternatives

### Make Azure AI Search mandatory

Rejected because sovereign, disconnected, Fabric-native and non-Azure deployments must remain possible.

### Store Search keys in GitHub/App Service

Rejected. Managed identity and Entra RBAC are the required authentication path.

### Copy source-system data into Search

Rejected. CEPIO owns the intelligence projection and evidence references, not necessarily the underlying industrial data.

### Add vectors immediately

Rejected. The first live proof should isolate storage/index scale and tenant-filter behavior before introducing embedding/model variables.
