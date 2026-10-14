# Query Model

## Objective

Applications should query **industrial semantics**, not storage schemas.

A CEPIO consumer should not need to know whether the implementation underneath uses SQLite, Fabric, graph storage or an in-memory test repository.

## Typed object-set query

The current query contract supports:

- object type/subtype matching;
- typed property predicates;
- relationship constraints;
- valid-time filters;
- transaction-time filters;
- deterministic sorting;
- pagination.

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

The exact public v1 JSON contract should remain versioned and documented, but the semantic principle is stable: **typed industrial query, backend-neutral execution**.

## Relationship traversal

Typical traversal patterns include:

```text
Asset -> WorkOrder
Asset -> FailureMode
Asset -> ProcessUnit
WorkOrder -> SparePart
SparePart -> Supplier
ProcessUnit -> KPI
```

Multi-hop traversal enables cross-domain reasoning without exposing source-system join logic to the caller.

## Temporal query

CEPIO supports two independent time dimensions.

Example conceptual questions:

- What was K-201's actual operating state at 10:15?
- What did CEPIO believe K-201's state was at 10:20?
- Which work orders were related to K-201 at that valid time?

## Deterministic behavior

Queries should provide deterministic sorting and pagination so applications and agents receive stable results across backends.

## Backend translation

The query contract can be translated into different execution systems:

```text
CEPIO Query Contract
       |
       +-- In-memory evaluator
       +-- SQLite translator
       +-- future Fabric translator
       +-- future graph execution
```

The backend may change; the application contract should not.

## Graph analytics vs object query

Object-set query and graph analytics serve different purposes.

**Object query:** find or filter industrial objects according to typed conditions.

**Graph analytics:** calculate structural properties such as centrality, dependency reach, communities or blast radius.

Both operate over CEPIO semantics but should remain distinct interfaces.
