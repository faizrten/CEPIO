# CEPIO Memory & Context Architecture v0.1

## Purpose

CEPIO Industry IQ compounds industrial knowledge over time. The memory architecture ensures that this growth improves reasoning quality without causing model context, latency, storage duplication, or customer-data exposure to grow proportionally.

The core invariant is:

> Industry IQ knowledge may compound continuously; runtime working memory remains explicitly bounded.

A second invariant is:

> Storage is authoritative; context is ephemeral.

CEPIO therefore separates durable memory from the temporary context assembled for one reasoning or execution cycle.

## Scope of v0.1

Memory & Context v0.1 implements the first three roadmap phases:

1. **Memory contract** — typed memory classes, provenance, scope and tenant boundaries.
2. **Durable memory MVP** — a source-neutral `MemoryStore` protocol, an in-memory reference implementation, and a durable SQLite reference implementation.
3. **Bounded context assembly** — deterministic ranking, deduplication, tenant/expiry filtering, explicit resource budgets, and fail-closed handling when required context cannot fit.

It deliberately does **not** introduce Redis, Azure AI Search, a vector database, a graph database, or PostgreSQL as a mandatory dependency. Those are later physical-storage and retrieval choices behind the logical contracts.

## Memory model

CEPIO distinguishes four durable memory classes in v0.1:

| Class | Purpose | Typical scope |
| --- | --- | --- |
| Semantic | concepts, qualified capability knowledge, mappings, KPI meaning | global or tenant |
| Procedural | skills, workflows, policies, reasoning procedures | global or tenant |
| Episodic | prior decisions, incidents, observations and outcomes | normally tenant |
| Profile | organization, site, asset, persona and customer-specific context | profile/tenant |

**Working memory is not durable memory.** It is represented by the bounded context assembly result created for a single execution.

### Common memory envelope

A `MemoryRecord` carries:

- stable memory ID;
- memory kind and scope;
- compact summary;
- provenance, including whether the source is customer-specific;
- optional source-system evidence reference rather than copied raw data;
- tenant ownership where applicable;
- classification;
- creation and expiry timestamps;
- confidence;
- capability associations; and
- retrieval tags.

This contract is intentionally compact. CEPIO should persist the intelligence required to interpret and retrieve evidence, while large source data remains authoritative in Fabric, SAP, PI, OSDU, ADX, Cognite, or other bound systems whenever possible.

## Knowledge boundary

The contract enforces the distinction between global Industry IQ and customer memory.

```text
GLOBAL INDUSTRY IQ
  Core / Industrial Common / generalized Domain knowledge
            |
            | governed reuse only
            v
      runtime context
            ^
            |
CUSTOMER MEMORY
  organization / site / asset / persona / episodic evidence
```

A global memory record cannot carry a tenant ID or provenance marked as customer-specific. Tenant/profile memory requires explicit tenant ownership. Profile memory must use both `PROFILE` kind and `PROFILE` scope.

This prevents a customer-specific observation from silently becoming global CEPIO knowledge. Promotion into reusable Industry IQ continues to occur through the Capability Registry and Compounding Intelligence governance path.

## Storage architecture

### Logical contract first

The runtime depends on `MemoryStore`, not a particular database:

```text
CEPIO runtime
     |
     v
MemoryStore protocol
     |
     +-- InMemoryMemoryStore      test/reference
     +-- SQLiteMemoryStore        durable reference
     +-- future PostgreSQL/Azure SQL adapter
     +-- future federated/sovereign adapter
```

The SQLite implementation exists to prove persistence, restart behavior and ownership-boundary semantics without coupling CEPIO Core to a cloud service.

### Storage is not model context

Physical memory may grow from MB to TB or beyond. The assembled working context remains bounded by explicit budgets. Raw industrial evidence should normally remain in its source system, with CEPIO storing compact memory and evidence pointers.

```text
Large durable memory / external evidence
              |
         retrieval/routing
              |
              v
      bounded candidate set
              |
       Context Assembler
              |
              v
      bounded working context
              |
          model/agent
```

## Context assembly

`ContextAssembler` consumes already-discovered candidate memories. Discovery/routing is intentionally a later concern; v0.1 defines what happens after candidates are available.

Candidates carry:

- estimated token cost;
- relevance;
- priority;
- whether the memory is required;
- semantic-node cost;
- evidence-item cost; and
- capability associations.

Ranking is deterministic:

1. required before optional;
2. higher priority first;
3. higher relevance first;
4. stable memory ID as the final tie-breaker.

Before admission, the assembler removes duplicates, memories outside the tenant boundary, and expired memories.

## Context budget

The default v0.1 budget is:

```text
max_tokens          16,000
max_capabilities         5
max_semantic_nodes      150
max_evidence_items       25
max_episodes             10
```

These defaults are typed runtime values, not infrastructure sizing commitments. Applications may provide stricter budgets.

If a **required** memory would exceed any budget dimension, context assembly returns `BLOCKED` with no selected context. This is fail-closed behavior: CEPIO must not silently reason without required evidence.

If an **optional** memory would exceed the budget, it is dropped and the remaining bounded context can proceed.

## Performance invariant

Knowledge-store size must not determine working-context size.

The v0.1 test suite explicitly proves that adding hundreds of irrelevant memories does not increase the selected context or its token usage when the query resolves the same relevant memory.

Future performance qualification should measure:

- capability-routing precision;
- retrieval-set size;
- selected-context size;
- context-budget saturation;
- retrieval and assembly latency;
- cache hit rate; and
- source-system call latency.

## Forgetting, expiry and lifecycle

`MemoryStore.forget()` establishes a logical deletion contract. Tenant memory can only be forgotten within its owning tenant boundary. Global memory requires a global management context.

`expires_at` provides deterministic expiry behavior. Expired records are excluded from reads, queries and working context.

This is only the lifecycle foundation. Later phases should add explicit retention policy, legal hold, archival, consolidation and regional placement without changing the core runtime contract.

## Relationship to Compounding Intelligence

Memory and Compounding Intelligence have different responsibilities:

```text
Operational experience
        |
        v
tenant/profile/episodic memory
        |
   pattern candidate
        |
        v
Generalization Review
        |
cross-domain qualification
        |
human architecture approval
        |
        v
Capability Registry
        |
        v
global reusable Industry IQ memory
```

Memory stores experience. Compounding Intelligence governs what CEPIO may claim as reusable knowledge.

## Infrastructure roadmap

### Phase 3 — retrieval and indexing

Add hybrid textual/vector retrieval and semantic graph projections behind source-neutral interfaces. Keep the authoritative memory contract independent from any search engine.

### Phase 4 — hot cache and compiled Industry IQ

Cache resolved capability bundles, semantic subgraphs, policy bundles and execution plans. Common requests should increasingly avoid repeated graph/retrieval work.

### Phase 5 — episodic decision memory

Introduce a structured industrial episode contract containing situation, objective, evidence, assumptions, uncertainty, authority, decision, action and outcome. Do not treat chat transcripts as the primary episodic representation.

### Phase 6 — consolidation

Consolidate events into episodes, episodes into patterns, and qualified patterns into capability candidates. This should increase knowledge density rather than accumulate unbounded embeddings.

### Phase 7 — storage tiering

Introduce hot/warm/cold lifecycle placement, residency, retention, archival and legal-hold policies. The logical `MemoryStore` boundary should remain stable.

### Phase 8 — federated and sovereign memory

Allow customer- or region-owned memory stores to participate through the same logical interface without centralizing protected data.

## Non-goals of v0.1

- training model weights from customer memory;
- copying complete customer historians or data lakes into CEPIO;
- choosing a universal vector database;
- implementing semantic similarity search;
- implementing capability routing;
- implementing episodic consolidation;
- defining production Azure sizing or HA topology.

Those choices should be made after the memory and context contracts are proven under real domain workloads.

## Qualification

Memory & Context v0.1 is considered qualified when tests demonstrate:

- global/customer knowledge-boundary enforcement;
- tenant-isolated reads, updates and deletion;
- durable SQLite persistence across reopen;
- expiry exclusion;
- deterministic query filtering and ordering;
- deterministic context ranking and deduplication;
- all context budget dimensions;
- fail-closed required-context overflow;
- optional-context shedding; and
- bounded selected context as the underlying memory corpus grows.
