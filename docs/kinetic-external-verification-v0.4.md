# Kinetic External Verification Gate v0.4

CEPIO Kinetic v0.4 connects durable workflow progression to the governed external-action control plane introduced in v0.3.

## Product capability

A workflow can execute a governed CEPIO Action, pause without blocking a request thread, wait for the corresponding source-system effect to become verified, persist a terminal Outcome, and then continue.

The workflow definition remains source-neutral. An `external_verification` step references an earlier CEPIO Action step by `action_step_id`; it does not name SAP, PI, OSDU, P6, an adapter, an endpoint, or a source operation.

```text
Function -> Decision -> Approval -> Action
                                  |
                                  v
                         External Verification
                                  |
                    +-------------+-------------+
                    |             |             |
                 verified       failed        unknown
                    |             |             |
                 Outcome       Outcome       WAIT
                    |             |             |
                 continue       fail       reconcile
```

## Core semantics

### Action execution is not source completion

A CEPIO Action becoming `executed` means CEPIO policy allowed the Action and its governed Action handler completed. If the Action has an external binding, this does not mean the source system has applied the corresponding business change.

### Acknowledgement is not verification

An adapter acknowledgement moves the external execution to `pending_verification`. The workflow remains in `waiting_for_external_verification` until source truth returns `verified` or `failed`.

### Unknown is not failure and is not retryable

A transport failure after submit can leave the source-side outcome uncertain. CEPIO records `unknown`, keeps the workflow waiting, and refuses blind redispatch. An explicit reconciliation tick is required to resolve source truth.

### Outcome is terminal evidence

`WorkflowOutcome` is immutable and unique per `(workflow_instance_id, verification_step_id)`. It links:

- workflow instance and exact definition version;
- workflow subject;
- governed CEPIO Action id;
- external execution id;
- terminal status (`verified` or `failed`);
- source verification evidence.

No terminal Outcome is recorded while the external execution is pending or unknown.

## Workflow contract

```python
WorkflowStepDefinition(
    id="verify-enterprise-write",
    type=WorkflowStepType.external_verification,
    action_step_id="create-inspection",
)
```

Validation requires the referenced step to be an earlier `Action` step. `operation` is forbidden on the verification step to prevent source-specific commands from leaking into the workflow model.

## Worker/tick model

`tick_external_verification(instance_id)` performs at most one external control-plane iteration:

1. `pending_execution` -> governed dispatch;
2. `pending_verification` / `acknowledged` -> verify;
3. `unknown` / `dispatching` -> remain waiting unless `reconcile_unknown=True`;
4. `verified` -> persist Outcome and resume workflow;
5. `failed` -> persist failed Outcome and fail workflow closed.

A normal `resume()` call cannot advance a workflow that is waiting for external verification.

## Persistence and restart

The workflow step persists `external_execution_id` and terminal `outcome_id`. SQLite reference persistence stores workflow state, external-action state, and immutable outcomes independently. After restart, adapters and bindings are re-registered as deployment configuration; the workflow resumes against the same external execution rather than enqueueing or dispatching a replacement.

## Resilient runtime

`ExternalResilientKineticRuntime` combines v0.2 Function retry/cancellation/compensation behavior with the external verification gate. The gate itself does not inherit Function retry semantics. External dispatch, verification, reconciliation, and idempotency remain owned by `ExternalActionRuntime`.

## Safety invariants

1. Source acknowledgement never advances the workflow as business completion.
2. Verification steps never call source adapters directly.
3. Unknown outcomes never trigger automatic redispatch.
4. Generic workflow resume cannot bypass the verification wait.
5. One workflow Action maps to at most one external execution through the existing external idempotency contract.
6. One verification step records at most one immutable terminal Outcome.
7. Workflow definition version and explicit workflow lineage remain pinned across restart.

## Deliberate boundaries

v0.4 does not add:

- background worker scheduling or distributed leases;
- automatic Action redispatch;
- external compensation execution;
- public REST/SDK/MCP workflow administration;
- live SAP S/4HANA writeback;
- a general event/time trigger engine.

The next integration milestone can place the first real SAP S/4HANA maintenance writeback beneath this control plane without changing workflow semantics.
