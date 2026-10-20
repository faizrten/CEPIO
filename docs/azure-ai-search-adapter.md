# Azure AI Search Adapter v0.1

## Purpose

Phase 3.1 binds CEPIO's source-neutral Retrieval & Indexing contracts to a real Azure AI Search service without making Azure AI Search authoritative for CEPIO semantics.

Demo service:

`https://cepio-search-dev-31d48.search.windows.net`

Demo index:

`cepio-memory-v1`

The governing rule remains:

> The Capability Registry and MemoryStore define CEPIO knowledge; Azure AI Search is a rebuildable retrieval projection.

## Runtime architecture

```text
CEPIO App Service
  system-assigned managed identity
          |
          v
Azure AI Search
          |
          v
AzureSearchMemoryBackend
          |
          v
RetrievalEngine
          |
          v
ContextAssembler
```

No API key, client secret, or Search admin key is stored in CEPIO.

## Authentication and roles

The adapter uses `DefaultAzureCredential` and therefore resolves the App Service system-assigned managed identity in Azure.

Recommended runtime assignment on the Search service:

- `Search Index Data Reader` when the CEPIO runtime only queries;
- `Search Index Data Contributor` when CEPIO also maintains the rebuildable memory projection.

Index creation or schema changes are deployment/admin operations and require `Search Service Contributor`. Keep that permission out of normal runtime unless the environment explicitly requires runtime-managed indexes.

The synthetic scale-qualification workflow uses the existing `azure-demo` GitHub OIDC identity. That identity needs `Search Service Contributor` and `Search Index Data Contributor` scoped only to the development Search service while the qualification workflow is being used.

## Package boundary

Azure dependencies are optional:

```text
pip install 'cepio[azure-search]'
```

CEPIO Core remains importable and testable without the Azure SDK.

The Azure demo container opts into this extra through:

```text
CEPIO_RUNTIME_EXTRAS=azure-search
```

## Search document

Each Search document is a projection of a compact `MemoryRecord`:

- memory ID;
- summary;
- tenant/scope;
- memory kind;
- capability IDs;
- tags;
- source-system and resource-type metadata;
- creation/expiry timestamps; and
- canonical serialized `MemoryRecord`.

The adapter does not index raw historian streams, SAP tables, customer documents, or other large source data by default.

## Tenant boundary

Tenant isolation is enforced in two layers.

1. The Azure AI Search OData filter requests only reusable GLOBAL memory plus the requested tenant.
2. The adapter parses every returned `MemoryRecord` and re-checks tenant visibility and expiry before returning a `BackendHit`.

`RetrievalEngine` then performs its existing third boundary check before fusion.

Therefore a malformed or over-broad Search result cannot reach context merely because it ranked highly.

## Filters

The adapter translates CEPIO selectors into Azure AI Search filters for tenant/global scope, expiry, memory kind, tags, and capability IDs.

Collection filters use `any(...)` and `search.in(...)` where safe. Literal values are OData escaped.

## Index ownership

The index is a projection and can be deleted/rebuilt without changing CEPIO authority.

The portable App Service Bicep exposes `azureSearchEndpoint` and `azureSearchIndex` parameters. The existing demo-specific deployment workflow binds the development endpoint directly and installs the optional Azure Search runtime extra.

## Scale qualification

`CEPIO Azure AI Search Scale Qualification` is a manually triggered workflow. It uses synthetic data only and can run the progression:

```text
50,000 -> 500,000
```

For each corpus size it requires reusable global target evidence and same-tenant target evidence to be found, foreign-tenant target evidence to be absent, result count to remain bounded, and measured query latency to be captured.

The workflow resets the dedicated development index before the run, uploads synthetic records in batches of at most 1,000, and emits `evidence/azure-search-scale-qualification.json`.

This is an infrastructure qualification, not a production SLO. Production SLOs should be established per deployment region, replica/partition count, index size, query mix and customer residency topology.

## Vector search

v0.1 intentionally proves lexical plus structured-filter integration first. It does not choose an embedding model or require vector search.

A later adapter revision may add vector/hybrid queries behind the same `RetrievalBackend` contract after embedding governance, customer-data boundaries and frozen retrieval evals are defined.
