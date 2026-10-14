# CEPIO temporal history and deterministic state projection

## Purpose

CEPIO must represent not only the current enterprise state, but also what CEPIO knew at a historical point, what was valid in the industrial domain, and which immutable events produced a derived state.

## Bitemporal semantics

CEPIO distinguishes two time axes.

### Transaction time

**When CEPIO recorded the fact.**

Every object version and relationship revision is append-only in the temporal history. `get_object_at(id, T)` reconstructs the latest object version CEPIO had recorded by transaction time `T`.

Ordinary domain APIs never mutate historical snapshots.

### Valid time

**When the fact is considered true in the industrial domain.**

Objects may declare canonical `core#validFrom` / `core#validTo` (or migration aliases `validFrom` / `validTo`). If no source-domain valid time is supplied, valid time starts at transaction time.

Relationships already carry `valid_from` and `valid_to`. The valid interval is half-open: `[valid_from, valid_to)`.

`get_object_valid_at(id, valid_time, as_of_transaction=...)` and `relationships_at(...)` support bitemporal questions such as:

> What relationship did CEPIO believe was valid on 1 February, based only on information CEPIO had received by 15 January?

A later correction does not rewrite the earlier transaction record. It appends a new version/revision with a later transaction time and potentially earlier domain valid time.

## Deterministic event ordering

Source operational events are immutable. Projection ordering is always:

1. `occurred_at` ascending;
2. event `id` ascending as the stable tie-breaker.

This guarantees that replay of the same event set produces the same derived state even when ingestion order differs.

## Projection separation

Source events and projection metadata are intentionally separate:

```text
Immutable source events
        |
        v
 deterministic projector
        |
        +--> derived ontology properties
        |
        `--> projection checkpoint
             - projector name/version
             - event count
             - last event id/time
             - derived state hash
             - rebuild time
```

Deleting a projection checkpoint or derived state does not delete or alter source events. The projection can be rebuilt from the event history.

## Reference compressor projector

`CompressorOperatingStateProjector` is the first reference projector. It derives:

- `operatingState`;
- `lastStateEventId`;
- `lastStateChangedAt`.

Reference transitions include `TripEvent -> tripped`, `RecoveryEvent -> running`, `StartEvent -> running`, `StopEvent -> stopped`, degradation/condition alerts, and maintenance transitions. An explicit event `operatingState` property takes precedence.

The projector is intentionally simple: it proves the runtime contract before CEPIO adds PI/AVEVA/Eventstream-specific ingestion adapters.

## Storage

Both in-memory and SQLite reference backends support:

- immutable object version snapshots;
- relationship revision history;
- transaction-time object reconstruction;
- valid-time object and relationship queries;
- deterministic event retrieval;
- projection checkpoints stored separately from events.

## Next extensions

1. expose temporal filters through the typed query API;
2. carry source-event provenance into projection provenance;
3. add projector dependency/version migration rules;
4. map event ingestion to Fabric Eventstreams / Real-Time Intelligence and AVEVA PI;
5. support multi-object projections and causal dependency graphs.
