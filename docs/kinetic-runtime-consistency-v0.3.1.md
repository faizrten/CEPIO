# Kinetic Runtime Consistency v0.3.1

This slice hardens CEPIO's kinetic and external-action runtimes before workflow progression is allowed to depend on source-system verification.

## Why this exists

Long-running industrial workflows can remain paused while definitions, identity mappings and source-system state change. CEPIO therefore needs deterministic answers to five questions before the external verification gate is introduced:

1. Which exact workflow definition does a paused instance resume?
2. Can one business trigger create more than one workflow instance?
3. Is workflow identity distinct from generic tracing correlation?
4. Is the external identity captured at enqueue still valid when dispatch actually occurs?
5. Can two workers dispatch the same external side effect concurrently?

v0.3.1 makes those guarantees explicit.

## Immutable workflow definitions

`WorkflowDefinition` identity is the pair `(id, version)`.

A definition registered at an existing `(id, version)` may be re-read or registered again only when its content is identical. Different content under the same identity is rejected.

Every `WorkflowInstance` already stores `definition_id` and `definition_version`; the runtime now resolves the exact pair for approval lookup, resume, execution, decision observation and Action execution.

```text
WorkflowDefinition A@1.0.0 -----> WorkflowInstance X
                                      |
register A@2.0.0                     |
                                      v
                               resume A@1.0.0
```

Registering a newer version never changes the executable contract of an existing instance.

SQLite automatically migrates the earlier `workflow_definitions(id PRIMARY KEY, version, payload)` reference schema to the composite `(id, version)` key while retaining the stored definition.

## Atomic trigger creation

The old pattern performed `find(trigger_key)` followed by `save(instance)`. That sequence was replay-safe under sequential calls but not atomic under concurrency.

Repositories now expose atomic create-or-get semantics:

```text
create_instance_if_absent(candidate)
  -> (instance, created)
```

In-memory repositories protect the trigger index with one lock. SQLite uses a write transaction (`BEGIN IMMEDIATE`) around trigger lookup and insertion. Competing callers therefore converge on one persisted workflow instance.

Only the caller that actually creates the instance records `workflow_started` and advances execution.

## Version-scoped resilience policy

Retry, timeout, cancellation and compensation policies are part of a workflow version's executable contract.

They are now stored under a version-scoped definition key:

```text
workflow-id@version
```

A v2 policy cannot silently change the retry or cancellation behavior of a paused v1 instance.

Resilience policy validation also occurs before the workflow definition is persisted. An invalid policy therefore cannot leave a partially registered executable definition behind.

Failed or timed-out Function attempts clear any intermediate `step.result` so a terminal failure cannot expose stale successful-looking output.

## Explicit workflow lineage

`correlation_id` remains a distributed tracing identifier. It no longer implies workflow identity.

The Action contract now carries:

```text
ActionRequest.workflow_instance_id
        |
        v
AuditEntry.workflow_instance_id
        |
        v
ExternalActionExecution.workflow_instance_id
```

Kinetic Actions and compensation requests set this value explicitly. An API caller may still use `correlation_id` for request or incident tracing without being interpreted as a workflow.

This gives the future verification gate an unambiguous lineage chain:

```text
WorkflowInstance
 -> Decision
 -> Action
 -> immutable Audit
 -> ExternalActionExecution
```

## Identity revalidation before dispatch

An external execution captures the selected identity mapping at enqueue:

- mapping id;
- mapping version;
- external id;
- system and identity type.

Immediately before source dispatch CEPIO resolves the identity again and verifies that the selected mapping is still uniquely valid and unchanged.

A change to mapping identity, mapping version, external id, or reconciliation state blocks the write before the adapter is called.

```text
ENQUEUE
  identity EQ-201 / mapping v1
       |
       | time passes
       v
DISPATCH
  re-resolve identity
       |
       +-- unchanged -> claim dispatch
       |
       +-- changed/stale/conflict -> FAILED / reconciliation required
```

## Optimistic external-action transitions

`ExternalActionExecution` now has a monotonic `revision` and a transient `dispatching` state.

A worker must atomically compare-and-set:

```text
pending_execution@revision=N
        |
        | CAS
        v
dispatching@revision=N+1
        |
        v
adapter.write_governed(...)
```

Only the worker that wins the revision claim may call the adapter. A competing worker returns or fails closed without sending a second command.

SQLite persists the revision as a dedicated column and migrates earlier execution tables by adding the column when missing.

`dispatching` is deliberately conservative. If a worker dies while the source outcome is uncertain, CEPIO does not blindly redispatch. The operation must be reconciled before another source write can be considered.

## What v0.3.1 does not add

This hardening slice does not yet introduce:

- a workflow step that waits for external verification;
- first-class `Outcome` records;
- automatic Action retry;
- distributed leases or queue scheduling;
- dead-letter queues or circuit breakers;
- live SAP S/4HANA writeback.

Those capabilities can now be built on deterministic workflow identity, trigger, lineage, external identity and dispatch semantics.

## Next kinetic slice

The next intended step is the external verification gate:

```text
Function
 -> Decision
 -> Approval
 -> Action
 -> ExternalActionExecution
 -> WAIT_FOR_VERIFICATION
 -> VERIFIED / FAILED / UNKNOWN
 -> Outcome
 -> next workflow step
```

A workflow must not progress past an externally material Action until the source-side outcome is verified or explicitly handled through reconciliation policy.