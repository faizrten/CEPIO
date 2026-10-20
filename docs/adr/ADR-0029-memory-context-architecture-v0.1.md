# ADR-0029: Memory & Context Architecture v0.1

- Status: Accepted
- Date: 2026-10-20

## Context

CEPIO now has governed Domain Onboarding and Compounding Industrial Intelligence. As Industry IQ accumulates reusable knowledge and customer-specific operating experience, the runtime needs a durable memory model that does not force all accumulated knowledge into model context and does not allow customer memory to silently mutate global Industry IQ.

The infrastructure choice must also remain portable. CEPIO may run with Azure-native services, customer-owned stores, or sovereign/federated deployments. Choosing a vector database, graph database or cloud persistence service as the memory abstraction would couple semantics and governance to a physical implementation too early.

## Decision

CEPIO adopts a logical Memory & Context architecture with these invariants:

1. Durable memory and ephemeral working context are separate concerns.
2. Global memory cannot contain tenant/customer-specific knowledge.
3. Tenant/profile memory is explicitly owned and cannot cross tenant boundaries during update, access or deletion.
4. Raw industrial evidence should remain in authoritative source systems where practical; CEPIO stores compact memory and evidence references.
5. Runtime context is assembled under explicit multi-dimensional budgets and does not scale with the total memory corpus.
6. Missing required budget capacity fails closed; optional context may be shed.
7. Physical persistence is hidden behind the `MemoryStore` protocol.
8. Customer memory cannot enter global Industry IQ except through the governed Compounding Intelligence promotion path.

v0.1 provides:

- typed memory/provenance/reference/query contracts;
- `MemoryStore` protocol;
- `InMemoryMemoryStore` reference backend;
- `SQLiteMemoryStore` durable reference backend;
- deterministic `ContextAssembler` and explicit `ContextBudget`.

## Alternatives considered

### Vector-database-first memory

Rejected. Vector retrieval is useful for later unstructured retrieval but is not an authoritative tenancy, provenance, lifecycle or governance model.

### PostgreSQL/Azure SQL as the public abstraction

Rejected. A relational production backend is likely useful, but binding the core contract to it would make sovereign and federated deployments unnecessarily difficult. The storage service should implement `MemoryStore`, not define it.

### Copy customer source data into CEPIO memory

Rejected. This increases storage duplication, residency burden and customer-data risk. CEPIO should own the intelligence and evidence linkage, not automatically duplicate historians, ERP systems or customer lakes.

### Unbounded retrieval followed by LLM truncation

Rejected. This makes latency and response quality increasingly sensitive to corpus size and can silently omit required evidence. Context budgets must be explicit before model invocation.

## Consequences

Positive:

- Industry IQ can grow independently from model context size.
- customer/global knowledge boundaries are testable in code;
- future physical stores can evolve without changing the memory contract;
- storage, retrieval, caching and model inference remain separable;
- required evidence failures are visible rather than silently truncated.

Trade-offs:

- v0.1 does not provide semantic/vector retrieval;
- SQLite is a reference proof, not the production scale recommendation;
- applications must estimate candidate context cost before assembly;
- later lifecycle work must add retention, residency, legal hold and archival policy contracts.

## Validation

The contract suite must cover tenant isolation, global-memory restrictions, persistent SQLite reopen, expiry, logical forget, deterministic query filtering, deterministic context ranking/deduplication, every budget dimension, required-context fail-closed behavior, optional shedding and a corpus-growth test proving selected working context remains bounded.

The repository Quality Gate remains authoritative for coverage, formatting, compatibility and regression requirements.
