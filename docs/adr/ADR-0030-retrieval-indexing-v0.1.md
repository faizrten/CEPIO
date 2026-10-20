# ADR-0030: Capability-Routed Retrieval & Indexing v0.1

- Status: Accepted
- Date: 2026-10-20

## Context

Memory & Context v0.1 separated durable memory from bounded working context. That alone does not solve retrieval: as Industry IQ grows, CEPIO needs a governed way to identify which small subset of memory is relevant to a task without loading or scanning the entire corpus into model context.

The repository also already contains a typed object `QueryEngine`, Capability Registry, graph capabilities and customer-data boundaries. Retrieval must compose these abstractions rather than create a product-specific parallel architecture.

## Decision

CEPIO adopts a capability-routed retrieval control plane with these invariants:

1. every retrieval request must contain a selector;
2. the Capability Registry is authoritative for routable reusable capabilities;
3. required capabilities that are not registered fail closed;
4. retrieval plans have explicit capability, candidate and backend-request limits;
5. physical search engines implement `RetrievalBackend` and remain replaceable;
6. search indexes are rebuildable projections, not memory truth;
7. heterogeneous backend results are fused deterministically by rank rather than incomparable raw scores;
8. tenant visibility and expiry are re-checked after backend retrieval and before fusion;
9. required capability evidence that is absent after retrieval fails closed; and
10. final model context is still governed by Memory v0.1 `ContextAssembler` budgets.

v0.1 provides:

- deterministic `CapabilityRouter`;
- `RegistryCapabilityGraph` projection;
- typed `RetrievalIntent`, `RetrievalPlan`, `RetrievalStep` and result contracts;
- generic `RetrievalBackend` and `MemorySearchIndex` protocols;
- `StructuredMemoryBackend`;
- `InMemoryLexicalIndex` + `LexicalIndexBackend`;
- Reciprocal Rank Fusion in `RetrievalEngine`;
- `RetrievalContextPipeline`; and
- a dedicated synthetic retrieval qualification workflow.

## Alternatives considered

### Vector-database-first retrieval

Rejected. It would collapse routing, tenancy, lifecycle, evidence semantics and retrieval into a storage product. Vector retrieval remains a supported adapter strategy, not the architecture.

### LLM-only routing

Rejected for v0.1. A model may later propose capability routes, but CEPIO requires deterministic registry resolution, explainability and fail-closed behavior independent of model availability.

### Raw backend-score fusion

Rejected. Lexical, vector, graph and structured systems produce scores with different meanings and ranges. Reciprocal Rank Fusion provides a deterministic product-neutral interoperability layer.

### Trust backend tenant filtering

Rejected. Backends should filter correctly, but CEPIO must re-check memory visibility before a hit can influence ranking or context.

### Unbounded fan-out across every search system

Rejected. Backend requests and candidate counts are explicit budgets. Retrieval cost and latency should not increase simply because more adapters are installed.

## Consequences

Positive:

- CEPIO can add Azure AI Search, pgvector, graph or sovereign search adapters without changing core semantics;
- retrieval quality becomes measurable independently from model reasoning quality;
- capability promotion immediately creates a governed routing target;
- search indexes can be rebuilt from authoritative memory;
- cross-tenant leakage is defended at multiple layers; and
- context size remains independent from corpus size.

Trade-offs:

- the reference router is lexical/deterministic rather than learned;
- the reference lexical index is in-memory and not a production HA recommendation;
- backend latency budgets/timeouts remain adapter-specific in v0.1;
- graph expansion is derived from current Capability Registry metadata rather than a full semantic graph service; and
- evidence hydration from source systems remains separate from retrieval candidate selection.

## Validation

The contract suite must cover routing, missing required capabilities, graph expansion, plan limits, selector validation, structured retrieval, lexical indexing, tenant/expiry filtering, deterministic fusion, backend failure semantics, required-evidence checks, context assembly integration, adapter substitutability and corpus-growth bounds.

The dedicated canary must load a target capability corpus plus hundreds of irrelevant memories and prove that target routing/candidate count remain bounded and cross-tenant memory never enters retrieval candidates.
