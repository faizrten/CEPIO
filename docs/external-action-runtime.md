# Governed External Action Runtime

## Status

This document defines the first common CEPIO control plane for external industrial writeback. It advances Issue #57 and the governed write/verify/reconcile subset of Issue #52, and provides the external-action foundation required by the kinetic runtime in Issue #67.

This slice is source-system-neutral. It does **not** claim that SAP, PI, OSDU or P6 production writeback is complete.

## Product boundary

CEPIO already authorizes and audits a canonical Action before this runtime is involved.

The external-action runtime begins from the immutable ID of that successfully executed Action:

```text
Authenticated actor / workflow / agent
        |
        v
CEPIO Action Runtime
  policy + preconditions
  idempotency + audit
        |
        | executed action_id
        v
ExternalActionRuntime
        |
        +--> resolve canonical -> external identity
        |
        +--> derive source binding from CEPIO configuration
        |
        +--> PENDING_EXECUTION
        |
        +--> adapter dispatch
        |
        +--> ACKNOWLEDGED
        |
        +--> PENDING_VERIFICATION
        |
        +--> verify / reconcile source truth
        |
        +--> VERIFIED / FAILED / UNKNOWN
```

No public CEPIO API or MCP tool accepts an arbitrary source-system operation through this control plane. The caller supplies only the CEPIO `action_id`; adapter system, operation and payload are derived from CEPIO-owned action bindings and immutable audit evidence.

## Why verification is separate from acknowledgement

An adapter acknowledgement proves that a source system accepted or received a request. It does not prove that the requested business state exists in the source system.

CEPIO therefore distinguishes:

- `acknowledged` — the source adapter acknowledged the request;
- `pending_verification` — CEPIO is waiting to confirm source-system truth;
- `verified` — the expected source state is confirmed;
- `failed` — the source deterministically confirms rejection or non-application;
- `unknown` — CEPIO cannot safely determine whether the side effect occurred.

This distinction is required before CEPIO can safely retry industrial Actions.

## External identity mapping

`ExternalIdentityMapping` records canonical-to-source identity without placing source-specific identifiers into CEPIO-Core semantics.

A mapping includes:

- canonical CEPIO object ID;
- source system;
- identity type;
- external ID;
- reconciliation status;
- mapping version;
- source timestamp and verification timestamp;
- optional metadata.

Supported reconciliation states are:

```text
matched
ambiguous
missing
stale
conflict
verified
```

Writes fail closed unless exactly one usable identity exists for the required `(canonical object, system, identity type)` tuple. Ambiguous, conflicting, stale or missing identities never leak through to the adapter write boundary.

A CEPIO object may have multiple external identities across systems or identity types. The action binding selects the required system and identity type explicitly.

## Action binding

`ExternalActionBinding` is runtime configuration, not caller input.

It binds:

```text
CEPIO action type
      -> source system
      -> source operation
      -> identity type
      -> optional payload builder
```

Example:

```python
ExternalActionBinding(
    action_type="EscalateRisk",
    system="sap_s4hana_eam",
    operation="update_equipment_risk",
    identity_type="equipment",
)
```

The default external payload contains only the canonical target, CEPIO action type, decision ID and the immutable effects recorded by the Action audit. A deployment may register a deterministic payload builder for a specific binding.

## Adapter contract

The governed write subset added to `cepio.adapters` contains three source-neutral operations:

```text
write_governed(request)
verify_write(request)
reconcile_write(request)
```

Requests carry:

- CEPIO external execution ID;
- system and operation;
- external target ID;
- canonical object ID;
- CEPIO action ID;
- authenticated actor ID for write submission;
- decision ID where present;
- adapter idempotency key;
- expected payload.

The adapter idempotency key is derived by CEPIO from:

```text
source system + source operation + CEPIO action_id
```

It is not supplied by the calling agent/application.

## Async lifecycle

`enqueue_from_action(action_id)` performs no source-system write. It validates the CEPIO action audit, resolves identity and persists a durable `pending_execution` record.

A worker or scheduler can later call:

```text
dispatch(execution_id)
```

which performs one adapter write iteration and returns without performing source verification.

A separate worker iteration calls:

```text
verify(execution_id)
```

or, for uncertain outcomes:

```text
reconcile(execution_id)
```

This is the non-blocking foundation required for long-running kinetic Actions.

## Unknown-outcome safety rule

Transport and timeout failures around an external write are dangerous because the source may have applied the side effect even when CEPIO did not receive an acknowledgement.

Therefore:

```text
write exception / uncertain transport outcome
        -> UNKNOWN
        -> redispatch forbidden
        -> reconcile against source truth
        -> VERIFIED / FAILED / remain UNKNOWN
```

CEPIO deliberately does not infer failure from a missing acknowledgement.

This is the prerequisite for safe future Action retry.

## Audit and provenance linkage

Each `ExternalActionExecution` preserves:

- CEPIO action ID and action type;
- canonical target;
- authenticated actor and roles recovered from immutable Action audit;
- decision ID;
- correlation ID (the kinetic runtime uses workflow instance ID here);
- source system / operation;
- resolved external identity;
- deterministic adapter idempotency key;
- source request ID;
- dispatch / verification counters;
- current lifecycle status and failure reason.

Immutable `ExternalActionHistoryEntry` records lifecycle transitions separately from canonical object state.

The causal path is therefore:

```text
Decision
   -> CEPIO Action
   -> immutable Action audit
   -> ExternalActionExecution
   -> adapter request
   -> source acknowledgement
   -> source verification / reconciliation
```

## Persistence

Two reference repositories are supplied:

- `InMemoryExternalActionRepository` for tests/local development;
- `SQLiteExternalActionRepository` for durable single-writer reference execution.

SQLite persists:

- external identity mappings;
- external action executions;
- immutable external action history.

Adapter registration and action bindings remain deployment configuration and must be re-established when a process restarts.

## Fake adapter qualification

`FakeGovernedWriteAdapter` is a deterministic contract-test adapter. It can model:

- successful write + verification;
- explicit source rejection;
- transport/write exception;
- verification unknown / conflict / not-applied;
- reconciliation of an uncertain outcome;
- adapter-level idempotency.

It is not a production connector.

## Explicit non-goals of this slice

This implementation does not yet provide:

- a live SAP S/4HANA writeback implementation;
- Fabric/Eventstream worker scheduling;
- queues, leases, DLQ, circuit breakers or backpressure;
- automatic retry of external Actions;
- workflow gating that keeps `WorkflowInstance` open until external verification completes;
- cancellation of a source operation already in flight;
- external compensation execution;
- full #52 `discover / subscribe / map` adapter SDK;
- REST/SDK/MCP external-action administration surfaces.

## Next slices

1. Add the kinetic workflow gate: Action -> external verification wait -> Outcome.
2. Implement the SAP S/4HANA maintenance reference writeback through this common runtime.
3. Add retry eligibility only when verification proves `not_applied` or adapter/source idempotency guarantees make replay safe.
4. Add worker leasing/queues, observability and operational SLOs for production deployment.
