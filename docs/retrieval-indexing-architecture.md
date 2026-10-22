# CEPIO Retrieval & Indexing Architecture v0.1

## Purpose

Memory & Context v0.1 established a critical separation: Industry IQ knowledge may compound continuously while runtime working context remains bounded. Retrieval & Indexing v0.1 supplies the control plane between those two layers.

The primary invariant is:

> CEPIO retrieves a small, governed candidate set before context assembly; corpus size must not become model context size.

A second invariant is:

> Retrieval is capability-routed and source-neutral. Search products implement the contract; they do not define CEPIO semantics or governance.

## Scope

v0.1 implements:

1. deterministic capability routing over the evidence-backed Capability Registry;
2. a bounded backend-independent retrieval plan;
3. a rebuildable lexical search index reference implementation;
4. structured MemoryStore retrieval;
5. a generic backend contract for lexical, vector and graph adapters;
6. deterministic multi-backend fusion;
7. defense-in-depth tenant and expiry filtering;
8. required-capability evidence checks;
9. direct integration into the Memory v0.1 ContextAssembler; and
10. qualification metrics and a synthetic corpus-growth canary.

It does not make PostgreSQL extensions, graph databases, Redis or other physical services mandatory; PostgreSQL is the preferred next implementation behind the logical contract.

## End-to-end control flow

```text
Industrial request
      |
      v
RetrievalIntent
      |
      v
CapabilityRouter  <---- Capability Registry
      |
      v
RetrievalPlanner  <---- optional capability graph projection
      |
      v
bounded RetrievalPlan
      |
      +------ structured MemoryStore backend
      +------ lexical index backend
      +------ future vector backend
      +------ future graph backend
      |
      v
backend hits
      |
      v
policy boundary re-check + deterministic rank fusion
      |
      v
bounded RetrievedMemory candidates
      |
      v
ContextAssembler  <---- explicit context budget
      |
      v
bounded working context
      |
      v
model / agent / workflow
```

The model never receives the whole memory corpus.

## Capability routing

`CapabilityRouter` is intentionally deterministic in v0.1. It matches request language, tags and explicit capability hints against reusable capability metadata such as:

- title and description;
- semantic terms and relationships;
- personas and competencies;
- evidence requirements;
- reasoning patterns;
- skills and decisions.

Explicit and required capability IDs take precedence. Every route is returned with a normalized score and human-readable reasons.

Required capability IDs that do not exist in the Capability Registry block retrieval before any backend call. This makes the Capability Registry the authoritative statement of what CEPIO claims it can route to.

The reference router is not intended to be the final natural-language router. A learned or frontier-model router may later propose routes, but any such implementation must still resolve against the governed Capability Registry and preserve deterministic fallback, explainability and required-capability failure semantics.

## Capability graph projection

`RegistryCapabilityGraph` provides a small source-neutral graph projection over the Capability Registry. Related capabilities are inferred from shared reusable semantic terms, semantic relationships, reasoning patterns and evidence requirements.

This is deliberately a projection, not a second source of truth. It exists to demonstrate the graph-routing boundary without requiring a graph database.

A future implementation may bind the same `CapabilityGraphProjector` contract to NetworkX, nx-cugraph, a graph service or a customer-owned graph projection.

## Retrieval planning

A `RetrievalIntent` must contain at least one selector:

- natural-language query text;
- memory kind;
- tag;
- capability hint; or
- required capability.

Selector-less broad retrieval is rejected.

The intent also carries explicit limits:

```text
max_capabilities       default 5
max_candidates         default 50
max_backend_requests   default 4
```

The planner never schedules more backend requests than allowed. It prefers structured retrieval first, then lexical, vector and graph strategies when those adapters are available and query text exists.

Backend availability is discovered through the runtime configuration. The planner therefore does not contain product-specific code.

## Retrieval backends

The common `RetrievalBackend` contract is:

```text
strategy + search(RetrievalStep) -> ranked BackendHit[]
```

Each hit carries:

- a compact `MemoryRecord`;
- backend strategy;
- backend-local score;
- rank; and
- explanation/reasons.

v0.1 includes two reference backends.

### StructuredMemoryBackend

Executes typed `MemoryQuery` filters through the existing `MemoryStore` contract. It is appropriate for exact capability, tag, memory-kind and tenant filtering.

### LexicalIndexBackend

Uses `InMemoryLexicalIndex`, a rebuildable inverted index over compact memory summaries, tags and evidence-reference metadata.

The index is **not authoritative**. `MemoryStore` remains the durable source of memory truth. Search indexes are projections that may be rebuilt.

The reference lexical index deliberately does not index capability IDs as free text. Capability membership is applied as a structured filter, preventing capability identifiers from creating accidental text relevance.

## Vector and graph retrieval

`VECTOR` and `GRAPH` are first-class strategy values but have no mandatory storage product in v0.1.

PostgreSQL full-text / optional pgvector, Fabric, custom embedding services, graph engines or customer-owned implementations can participate by implementing `RetrievalBackend`. The engine does not need to change.

This avoids the common failure mode where a vector database becomes the architecture rather than an implementation detail.

## Fusion

Different retrieval engines produce scores on incompatible scales. v0.1 therefore does not compare raw backend scores directly.

Instead, `RetrievalEngine` uses deterministic Reciprocal Rank Fusion (RRF):

```text
fused_score(memory) = sum(1 / (k + backend_rank))
```

The result is normalized against the highest fused score for context relevance.

RRF gives CEPIO three useful properties:

1. deterministic ranking;
2. resilience to heterogeneous backend scoring scales; and
3. a clean path to add or replace retrieval products without retraining a score calibration layer.

Backend-local scores are still useful diagnostics, but rank is the interoperability contract in v0.1.

## Security and tenancy

Tenant isolation is enforced twice.

First, each backend receives the tenant scope and is expected to filter before retrieval. Second, `RetrievalEngine` re-checks every returned `MemoryRecord` before fusion.

```text
backend filter
     |
     v
returned hit
     |
     v
CEPIO tenant/expiry re-check
     |
     +-- invalid -> drop + metric
     |
     v
fusion
```

A buggy or misconfigured backend therefore cannot rely on ranking to hide a cross-tenant hit; the record is discarded before it can influence fused results or context.

Required capability evidence also fails closed. If a request declares a capability as required but the final candidate set contains no memory associated with that capability, retrieval returns `BLOCKED`.

## Failure behavior

Retrieval steps may be required or optional.

- a required backend failure blocks the request;
- an optional backend failure becomes a warning and retrieval may continue;
- a missing required capability blocks before backend execution;
- missing required capability evidence blocks after fusion;
- optional candidates may later be shed by ContextAssembler;
- required context that exceeds the Memory v0.1 budget remains fail-closed.

This means CEPIO can degrade gracefully when enrichment search is unavailable without silently ignoring required industrial evidence.

## Context integration

`RetrievalContextPipeline` converts fused retrieval candidates directly into Memory v0.1 `ContextCandidate` objects.

Required capability evidence is marked required. Evidence references count toward the evidence-item budget. The reference token estimator is intentionally simple and replaceable; production applications may use a model-specific tokenizer without changing the retrieval contract.

Retrieval bounds and context bounds are separate:

```text
large corpus
   -> bounded retrieval candidates
   -> bounded context candidates
   -> bounded model context
```

Both layers are necessary. A 50-document retrieval result can still be too large for a particular reasoning task, so ContextAssembler remains authoritative for the final working-set budget.

## Metrics

`RetrievalMetrics` currently records:

- route count;
- backend requests;
- backend failures;
- raw hits;
- fused hits;
- selected hits; and
- boundary/expiry drops.

Future production qualification should add:

- route precision@k and recall@k;
- retrieval precision@k and recall@k;
- mean reciprocal rank / nDCG for frozen retrieval evals;
- required-evidence miss rate;
- cross-tenant leakage rate, which must remain zero;
- backend latency and timeout rate;
- candidate-budget saturation;
- context conversion rate;
- cache hit rate; and
- per-capability retrieval quality.

These measurements should be evaluated on frozen synthetic and standards-derived scenarios before customer deployment.

## Corpus-growth invariant

The v0.1 qualification canary loads two valid target memories, one foreign-tenant memory and 500 irrelevant memories.

The expected behavior is:

- the target capability routes first;
- tenant and reusable global evidence are retrieved;
- foreign tenant evidence never enters candidates;
- irrelevant corpus growth does not increase lexical raw hits;
- candidate count stays within the configured retrieval budget; and
- final working context stays within ContextAssembler budgets.

This is the first executable proof that CEPIO can let Industry IQ knowledge grow without putting that growth directly into the model prompt.

## Relationship to existing CEPIO query infrastructure

CEPIO already has a governed `QueryEngine` for typed ontology objects, predicate/relationship traversal, cursor pagination and query budgets.

Retrieval & Indexing does not replace it.

The responsibilities are different:

```text
QueryEngine
  exact governed object-set queries
  canonical object/relationship semantics

RetrievalEngine
  find the small memory/evidence candidate set relevant to a reasoning task
  capability routing + heterogeneous search + fusion
```

A future structured retrieval adapter may use `QueryEngine` or external source bindings to hydrate evidence referenced by memory. Raw source-system data should not be copied into the search index by default.

## Production adapter direction

The contracts now allow several physical deployments without changing CEPIO Core:

- PostgreSQL full-text search plus an optional future pgvector extension;
- Fabric SQL/search patterns for customer-owned memory projections;
- NetworkX or nx-cugraph capability/semantic graph projections;
- customer-owned sovereign search services; and
- local/offline indexes for disconnected deployments.

No adapter becomes mandatory until performance, security, cost and sovereignty evidence justify it.

## Non-goals of v0.1

- production embedding model selection;
- universal vector database selection;
- raw industrial historian replication;
- learned query rewriting;
- unrestricted graph traversal;
- customer-specific route training;
- model-weight training from customer memory;
- public REST/API exposure of the retrieval contract.

The contract is qualified internally first. Public API surface should follow once retrieval behavior is stable under multiple domains and physical adapters.

## Exit criteria

Retrieval & Indexing v0.1 is qualified when repository tests and the dedicated canary demonstrate:

- deterministic capability routing;
- missing required-capability fail-closed behavior;
- bounded graph expansion;
- bounded backend fan-out;
- selector-less query rejection;
- structured and indexed lexical retrieval;
- index update/delete behavior;
- tenant and expiry filtering at index and engine layers;
- deterministic multi-backend fusion;
- optional-backend degradation and required-backend blocking;
- required capability evidence checks;
- direct bounded ContextAssembler integration;
- vector/graph adapter substitutability; and
- stable candidate size as the irrelevant corpus grows.
