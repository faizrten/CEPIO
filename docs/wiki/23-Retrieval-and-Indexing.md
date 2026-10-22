# Retrieval and Indexing

CEPIO Retrieval & Indexing v0.1 is the control plane between durable Industry IQ memory and bounded model context.

The rule is:

> Route by governed capability, retrieve a small candidate set, then let ContextAssembler decide the final working set.

## Flow

```text
request
  -> CapabilityRouter
  -> RetrievalPlanner
  -> structured / lexical / vector / graph backends
  -> reciprocal-rank fusion
  -> tenant + expiry re-check
  -> bounded candidates
  -> ContextAssembler
  -> model / agent
```

## What is implemented

- deterministic routing against the Capability Registry;
- optional capability-graph expansion;
- selector-required `RetrievalIntent`;
- bounded capability, candidate and backend-request budgets;
- `RetrievalBackend` adapter contract;
- structured MemoryStore backend;
- rebuildable in-memory lexical inverted index;
- replaceable vector/graph backend slots;
- deterministic Reciprocal Rank Fusion;
- defense-in-depth tenant/expiry filtering;
- required-capability evidence fail-closed checks;
- direct Memory v0.1 ContextAssembler integration; and
- retrieval qualification metrics and canary workflow.

The lexical index is a projection, not a source of truth. Durable `MemoryStore` remains authoritative.

## Why no mandatory vector database

Vector search is optional. PostgreSQL full-text and optional future pgvector are preferred for the next adapter, while customer-owned backends can implement the same retrieval contract. CEPIO semantics, tenancy and governance remain above the product layer.

## Safety

A backend is not trusted to enforce the final security boundary. CEPIO checks tenant visibility and expiry again before fusion. Required evidence that cannot be retrieved or cannot fit in working context blocks the request rather than silently disappearing.

See `docs/retrieval-indexing-architecture.md` and `docs/adr/ADR-0030-retrieval-indexing-v0.1.md`.
