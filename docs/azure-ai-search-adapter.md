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

## Scale qualification and throttle recovery

`CEPIO Azure AI Search Scale Qualification` is manually triggered, uses **synthetic
data only**, and resets the designated **development-only** `cepio-memory-v1` index.
Never run it against a customer or production index. It uses GitHub `azure-demo`
OIDC; no Search admin keys or client secrets are required.

Default progression:

```text
5,000 -> 50,000 (hard cap in the workflow)
```

The workflow deliberately does **not** run 500K by default or scale up Azure
capacity. Each indexing upload contains at most **100 documents**, separated by
a **0.5 second** pacing delay. The adapter retries transient indexing HTTP
429/500/502/503/504 with bounded exponential backoff (7 total attempts, 30s
maximum delay per retry, honoring numeric Retry-After). Permanently rejected
uploads (including 401/403) fail immediately. Partial batch results retry **only**
the transiently rejected documents; incomplete or malformed result sets fail closed.

Each size must retrieve global and same-tenant target evidence and **zero**
foreign-tenant target evidence; query results stay bounded to the configured
retrieval limit. This test captures a single query latency per size; it does
**not** establish production p95 or a throughput SLO.

The workflow emits `evidence/azure-search-scale-qualification.json` on both
success **and failure**, with indexed-document count, batch count, retry count,
elapsed time, per-size retrieval evidence and a bounded error diagnostic.
No customer source values are included. Azure request throttling is an
operational constraint, not permission to disable tenant checks or increase
quota automatically.

Manual operating sequence:

1. Cancel **old waiting** qualification attempts before launching a new one;
   they may otherwise reset the same development index after delayed approval.
2. Dispatch the workflow from `main` with `5000` for the first live smoke.
3. Approve `azure-demo` in GitHub's deployment review.
4. Inspect the uploaded JSON artifact and job logs. Only advance to
   `5000,50000` after the 5K evidence is green.
5. If 429 persists, inspect batch progress and retry counts before deciding
   whether to change pacing or Azure capacity. Capacity increases require
   separate expenditure approval.

This is infrastructure qualification, not a production SLO. Production
capacity/SLO needs a defined region, replica/partition count, index size,
query workload, and tenant/residency topology.

## Vector search

v0.1 intentionally proves lexical plus structured-filter integration first. It does not choose an embedding model or require vector search.

A later adapter revision may add vector/hybrid queries behind the same `RetrievalBackend` contract after embedding governance, customer-data boundaries and frozen retrieval evals are defined.
