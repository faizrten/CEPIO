# Query Model

## Objective

Applications should query **industrial semantics**, not storage schemas.

A CEPIO consumer should not need to know whether the implementation underneath uses an in-memory reference store, SQLite, a future enterprise persistence backend or provider-bound evidence source.

The stable principle is:

> **Typed industrial query, backend-neutral execution.**

## Query vs retrieval

CEPIO now has two deliberately separate concepts:

### Object / relationship query

Used when the caller needs an exact governed set of CEPIO objects/relationships satisfying typed conditions.

### Retrieval & Indexing

Used when a reasoning/agent task needs a **small bounded candidate set** of relevant memory/evidence chosen through capability routing and one or more retrieval backends.

```text
Object Query
= exact governed object-set semantics

Retrieval
= bounded evidence/memory candidate selection for a reasoning task
```

Do not turn search ranking into object-query truth or bypass ContextAssembler/evidence requirements with raw retrieval results.

See [Retrieval and Indexing](23-Retrieval-and-Indexing.md).

## Typed object-set query

The current query contract supports:

- object type/subtype matching;
- typed property predicates;
- relationship constraints;
- valid-time filters;
- transaction-time filters;
- deterministic sorting;
- pagination;
- actor/property authorization inherited from the application/runtime boundary.

## Conceptual query

```json
{
  "type": "industrial:Compressor",
  "where": [
    {"property": "asset:criticality", "op": "eq", "value": "A"},
    {"property": "industrial:operatingState", "op": "eq", "value": "tripped"}
  ],
  "related_to": {
    "relationship": "industrial:installedIn",
    "target": "HC-01"
  }
}
```

The exact public JSON/API contract remains versioned; the semantic intent remains backend-neutral.

## Relationship traversal

Typical traversal patterns include:

```text
Asset -> WorkOrder
Asset -> FailureMode
Asset -> ProcessUnit
WorkOrder -> SparePart
SparePart -> Supplier
ProcessUnit -> KPI
Decision -> Action
Action -> Outcome
```

Multi-hop/reverse traversal supports cross-domain reasoning without exposing source-system joins to the caller.

Traversal remains governed by actor/object/property policy and declared relationship semantics.

## Temporal query

CEPIO supports valid-time and transaction-time questions separately.

Examples:

- What was K-201's actual operating state at 10:15?
- What did CEPIO know about K-201's state at 10:20?
- Which work orders were related to K-201 at that valid time?
- Which evidence was available when a Decision was made?

## Deterministic behavior

Queries should provide deterministic sorting, pagination and bounded execution so applications, tests and agents receive stable behavior across logical backends.

Opaque cursor semantics and query budgets prevent callers from depending on physical database offsets/implementation details.

## Backend boundary

The logical query contract is isolated from physical storage:

```text
CEPIO Query Contract
       |
       +-- in-memory evaluator
       +-- SQLite repository/query implementation
       +-- future enterprise persistence/query adapters
```

Fabric, OSDU, Cognite, SAP or PI are normally integrated through CEPIO bindings/evidence contracts rather than assumed to be direct implementations of the CEPIO object-query engine.

A future backend may push query execution into a provider where semantics can be preserved, but provider syntax must not become the public CEPIO query language.

## Retrieval backend boundary

Retrieval has its own replaceable backend contract:

```text
RetrievalIntent
 -> CapabilityRouter
 -> RetrievalPlan
 -> structured MemoryStore
 -> lexical index
 -> future PostgreSQL full-text / optional vector and graph adapters
 -> deterministic rank fusion
 -> tenant/expiry re-check
 -> ContextAssembler
```

Indexes are **retrieval projections**, not an object-query or semantic authority layer; PostgreSQL is the preferred next implementation.

## Graph analytics vs object query vs retrieval

These interfaces serve different purposes:

- **Object query** — find/filter exact governed CEPIO object sets.
- **Relationship traversal** — navigate typed semantic edges.
- **Graph analytics** — calculate structural properties such as centrality, communities or blast radius.
- **Retrieval** — select bounded task-relevant evidence/memory candidates.

They can cooperate, but one should not silently substitute for another.

## Security invariant

Query/retrieval behavior must preserve:

```text
physical backend capability
        !=
permission to expose data
```

Authorization, tenant scope, evidence requirements and CEPIO semantic validation remain authoritative regardless of backend pushdown or retrieval ranking.
