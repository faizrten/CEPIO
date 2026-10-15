# Temporal State and Provenance

## Why time matters

Industrial data is rarely just "current" or "historical". Corrections, late-arriving events and backdated facts mean two different questions must be distinguishable:

1. What was true in the industrial world at time T?
2. What did CEPIO know at time T?

CEPIO therefore uses **bitemporal semantics**.

## Valid time

Valid time describes when a fact is true in the domain.

Example:

```text
Compressor operatingState = tripped
valid from 10:02 to 10:18
```

## Transaction time

Transaction time describes when CEPIO stored or learned a fact.

A late-arriving event may have:

```text
occurred_at       10:02
recorded_by_CEPIO 10:07
```

Both are meaningful.

## Object history

CEPIO can reconstruct prior object versions and state views.

Conceptually:

```python
runtime.get_object_at("K-201", transaction_time)
runtime.get_object_valid_at("K-201", valid_time)
```

## Relationship history

Relationships also change over time.

Examples:

- equipment moved to another functional location;
- supplier contract changed;
- person assigned to different team;
- work order reassigned;
- asset ownership changed.

Temporal relationship queries allow graph structure itself to be reconstructed historically.

## Event-to-state projection

Events are immutable source facts. Derived state can be replayed.

```text
Immutable events
     |
     v
Deterministic projector
     |
     v
Derived state
```

Advantages:

- reproducibility;
- explainability;
- debugging;
- recovery;
- ability to rebuild after logic changes.

## Property provenance

CEPIO records provenance at property level.

A value explanation may contain:

```text
property: asset:criticality
value: A
source_system: SAP
source_entity: Equipment
source_field: ABCINDIC
source_record: 10001234
mapping_version: sap-eam-v3
transformation_run: run-2026-10-14-001
observed_time: ...
ingestion_time: ...
source_value_hash: ...
```

## Operational lineage vs enterprise catalogue lineage

CEPIO provenance is intentionally precise and runtime-oriented.

Enterprise catalogue systems such as Purview may later receive lineage publications, but catalogue lineage should not replace CEPIO's operational provenance model.

## Explainability for AI

Provenance allows an agent to say:

```text
I believe K-201 is criticality A because CEPIO received that value
from SAP equipment record 10001234 using mapping version X at time Y.
```

That is materially safer than grounding an AI answer in an untraceable flattened dataset.
