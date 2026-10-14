# CEPIO Typed Query Contract

CEPIO v0.4 introduces a typed, repository-neutral object-set query contract for applications, agents and future Microsoft platform bindings.

The contract deliberately does **not** define a CEPIO-specific textual query language. It is a stable semantic request model that reference runtimes can evaluate directly and platform bindings can translate into native query engines.

## Contract

```text
ObjectQuery
├─ object_type
├─ include_subtypes
├─ predicates[]
│  ├─ property
│  ├─ operator
│  └─ value
├─ relationships[]
│  ├─ relationship_type
│  ├─ direction
│  ├─ other_id
│  └─ other_type
├─ valid_at
├─ as_of_transaction
├─ sort[]
├─ offset
└─ limit
```

Supported property operators:

- `eq`
- `ne`
- `gt`
- `gte`
- `lt`
- `lte`
- `in`
- `contains`
- `exists`

Canonical property IRIs and registered aliases are resolved through the CEPIO property registry. Legacy exact property keys remain readable during the v0.3→v0.4 migration period.

## Temporal semantics

`valid_at` asks what was true in the industrial domain at a point in time.

`as_of_transaction` asks what CEPIO had recorded by a point in time.

When both are supplied, CEPIO answers the bitemporal question:

> What was considered valid at `valid_at`, using only knowledge recorded by `as_of_transaction`?

Object snapshots use `get_object_at(...)` / `get_object_valid_at(...)`. Relationship constraints use `relationships_at(...)`. Current payloads are not treated as historical truth.

## Example

```python
from cepio import ObjectQuery, PropertyPredicate, RelationshipPredicate, SortField

result = runtime.query_objects(
    ObjectQuery(
        object_type="Compressor",
        predicates=[
            PropertyPredicate(property="criticality", operator="eq", value="high")
        ],
        relationships=[
            RelationshipPredicate(
                relationship_type="contains",
                direction="in",
                other_id="HCU-01",
            )
        ],
        sort=[SortField(field="riskScore", direction="desc")],
        limit=50,
    )
)
```

The same request is available over HTTP:

```text
POST /query/objects
```

and through the typed Python SDK:

```python
result = client.query_objects(query)
```

## Architectural boundary

```text
UI / Agent / Application
        ↓
CEPIO ObjectQuery
        ↓
Repository-neutral query contract
        ├─ In-memory reference evaluator
        ├─ SQLite reference evaluator
        ├─ Fabric / Fabric IQ translator (v0.4)
        ├─ Graph/search runtime (future)
        └─ other enterprise backends
```

The query model is part of CEPIO. A storage engine's syntax is not.

## Current reference limits

The v0.4 reference evaluator intentionally prioritizes semantic portability over backend-specific optimization. It scans the reference object repository and applies predicates/traversal through CEPIO runtime contracts. Production Fabric/graph/search bindings should translate and push down supported filters while preserving identical query semantics.

Multi-hop declarative path expressions, aggregations, full-text search and a custom textual DSL are outside this issue's scope.
