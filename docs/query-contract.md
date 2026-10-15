# CEPIO Typed Query Contract

CEPIO v0.4 exposes a typed, repository-neutral object-set query contract for applications, agents and Microsoft platform bindings.

The contract deliberately does **not** define a CEPIO-specific textual query language. It is a stable semantic request model that CEPIO can evaluate directly or translate into a native repository query while preserving the same authorization and ontology semantics.

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
├─ cursor
├─ include_total
├─ offset        (legacy compatibility)
└─ limit
```

`ObjectQueryResult` returns:

```text
items[]
total | null
offset
limit
next_cursor | null
has_more
```

Supported property operators are `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`, and `exists`.

Canonical property IRIs and registered aliases are resolved through the CEPIO property registry. Legacy exact property keys remain readable during migration periods. Storage-specific query syntax is never part of the public CEPIO contract.

## Public API v1

The supported public route is:

```text
POST /api/v1/query/objects
```

Unversioned `POST /query/objects` remains a temporary compatibility surface.

## Cursor pagination

API v1 clients should use `cursor`, not `offset`, for continuation.

A cursor is opaque and contains no supported client-editable fields. CEPIO binds every cursor to a fingerprint of the semantic query excluding pagination controls. Reusing a cursor with a different object type, predicate, relationship constraint, temporal context, or sort contract fails with:

```text
400 invalid_query_cursor
```

Cursor ordering is deterministic when the requested sort keys remain stable. CEPIO always uses object identity as the final deterministic tie-breaker. If the cursor object no longer belongs to the caller's authorized result set, continuation fails closed rather than leaking hidden result position.

`offset` is retained only for legacy compatibility and cannot be combined with `cursor`.

## Authorization ordering

Authorization is part of query semantics, not a post-processing decoration.

CEPIO applies this order:

```text
repository filter/pushdown
        ↓
semantic re-validation
        ↓
actor object visibility
        ↓
property filtering
        ↓
authorized count / cursor position
        ↓
page result
```

Therefore:

- unreadable objects cannot inflate `total`;
- unreadable objects cannot consume page slots;
- hidden properties are removed before application/agent consumption;
- a cursor from a more privileged actor cannot be used to navigate hidden topology or object position.

## Query budgets

The reference v0.4 runtime applies explicit guardrails so expensive queries fail predictably rather than consuming unbounded runtime resources.

Current default reference budgets are:

- maximum page size: `200`;
- maximum property predicates: `32`;
- maximum relationship predicates: `8`;
- maximum candidate rows scanned: `10,000`;
- maximum execution time: `5,000 ms`.

Budget exhaustion on API v1 returns:

```text
429 query_budget_exceeded
```

These are reference defaults, not permanent product SLOs. Production backends may expose tighter or backend-specific budgets while preserving the stable public error contract.

`include_total=false` allows an execution backend to stop after enough authorized rows are found for the requested page plus continuation detection. This avoids an unnecessary full authorized count when clients only need pagination.

## Repository execution and pushdown

```text
UI / Agent / Application
        ↓
CEPIO ObjectQuery
        ↓
CEPIO QueryEngine
        ├─ in-memory semantic oracle
        ├─ temporal reference evaluator
        └─ repository query backend
              ├─ SQLite SQL pushdown
              ├─ Fabric SQL / Warehouse extension point
              ├─ Eventhouse / KQL extension point
              ├─ Fabric Graph extension point
              └─ other enterprise backends
```

For current-state SQLite queries, CEPIO pushes supported object-type, property, relationship-existence and sort operations into SQLite. The returned candidates are still rechecked by the CEPIO semantic evaluator and policy engine. Pushdown may reduce work; it may never redefine semantics or bypass policy.

A normal filtered current-state SQLite query therefore does **not** call `runtime.list_objects()`.

Temporal `valid_at` / `as_of_transaction` queries remain on the reference temporal evaluator in v0.4 until a backend explicitly implements equivalent bitemporal pushdown semantics.

## Temporal semantics

`valid_at` asks what was true in the industrial domain at a point in time.

`as_of_transaction` asks what CEPIO had recorded by a point in time.

When both are supplied, CEPIO answers:

> What was considered valid at `valid_at`, using only knowledge recorded by `as_of_transaction`?

Object snapshots use `get_object_at(...)` / `get_object_valid_at(...)`. Relationship constraints use `relationships_at(...)`. Current payloads are not treated as historical truth.

## Example

```python
from cepio import ObjectQuery, PropertyPredicate, RelationshipPredicate, SortField

query = ObjectQuery(
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
    include_total=False,
)

first = runtime.query_objects(query)
second = runtime.query_objects(query.model_copy(update={"cursor": first.next_cursor}))
```

Multi-hop declarative path expressions, aggregations, full-text search and a custom textual DSL remain outside the v0.4 query contract.
