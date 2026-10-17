# CEPIO Kinetic Runtime

## Status

The kinetic runtime is an incremental v0.6 capability under Issue #67. The first kernel introduces durable workflow execution over CEPIO's existing governed Functions, Decisions and Actions. It does **not** yet claim the complete #67 orchestration scope.

## Product boundary

CEPIO already provides governed individual operations:

`Function -> Decision -> Action`

The kinetic runtime adds a durable process state machine around those operations:

`Trigger -> WorkflowInstance -> Function -> Decision -> Approval -> Action -> Completion`

Workflow execution state is deliberately separate from canonical industrial semantic state. A `WorkflowInstance` describes process execution; it does not redefine the industrial object that the workflow acts upon.

## First kernel contracts

### WorkflowDefinition

A versioned process definition containing ordered steps. The initial step types are:

- `function` — invoke a registered CEPIO typed function;
- `decision` — persist a CEPIO Decision tied to the workflow subject;
- `approval` — create a durable human approval task and pause execution;
- `action` — invoke the existing CEPIO governed Action Runtime.

### WorkflowInstance

A durable execution record containing:

- workflow definition and version;
- canonical CEPIO subject;
- workflow inputs;
- current step;
- per-step execution state and outputs;
- initiating actor and roles;
- most recent authenticated actor and roles;
- trigger idempotency key;
- lifecycle timestamps and terminal status.

### ApprovalTask

A durable approval record with required roles, request time, decision time, authenticated approver and optional comment. Approval changes the active execution identity: subsequent governed actions execute under the approving human's actor identity and roles rather than inheriting an agent's authority.

### WorkflowHistoryEntry

An immutable execution-history record for workflow starts, step starts/completions/failures, approval requests/decisions and workflow completion.

## Persistence

Two reference repositories are provided:

- `InMemoryWorkflowRepository` for tests and local development;
- `SQLiteWorkflowRepository` for durable reference execution.

SQLite stores workflow definitions, instances, approvals and immutable history independently from CEPIO object state. A workflow paused for approval can therefore be restored by a new kinetic-runtime process using the same database.

SQLite remains a reference single-writer persistence topology. This kernel does not introduce distributed workflow storage or workers.

## Identity and policy invariants

1. Starting a workflow requires authorized visibility of the canonical workflow subject.
2. Function steps enforce CEPIO function authorization for the active actor roles.
3. Approval steps require an authenticated actor whose roles intersect the declared approval roles.
4. After approval, the approving actor becomes the active actor for subsequent governed steps.
5. Action steps always call `CEPIORuntime.execute_action(...)`; workflows cannot bypass CEPIO action policy, preconditions, idempotency or audit.
6. Agent-initiated workflows therefore do not inherit action authority merely because the agent could start or reason about the workflow.

## Replay safety

Workflow start accepts an optional `trigger_key`. Replaying the same trigger returns the existing workflow instance instead of creating a second process.

Every action step also receives a deterministic CEPIO Action idempotency key scoped to:

`workflow instance + workflow step`

This is important for recovery. If an action completed but the workflow coordinator failed before advancing its local step state, re-execution reaches the existing CEPIO Action idempotency boundary rather than intentionally issuing a second side effect.

## Reference flow

The regression scenario demonstrates an agent-assisted reliability workflow:

```text
AI recommender
   |
   v
calculateAssetRisk
   |
   v
persist Decision: inspect asset
   |
   v
ApprovalTask ----------------------+
   |                               |
   | human maintenance engineer    |
   +-------------------------------+
   |
   v
CreateInspection through CEPIO Action Runtime
   |
   v
Workflow completed
```

The workflow pauses before the side effect. The subsequent `CreateInspection` action executes with the human approver's identity and remains subject to the existing CEPIO action policy and audit controls.

## Minimal usage

```python
from cepio import (
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowStepType,
    build_kinetic_runtime,
    build_runtime,
)
from cepio.model import ObjectRef

runtime = build_runtime(sqlite_path="cepio.db")
kinetic = build_kinetic_runtime(runtime, sqlite_path="cepio.db")

kinetic.register_workflow(
    WorkflowDefinition(
        id="asset-risk-inspection",
        name="Asset risk inspection",
        steps=[
            WorkflowStepDefinition(
                id="risk",
                type=WorkflowStepType.function,
                operation="calculateAssetRisk",
                parameters={"asset_id": "${subject.id}"},
            ),
            WorkflowStepDefinition(
                id="decision",
                type=WorkflowStepType.decision,
                decision_recommendation="Inspect the asset.",
                recommended_action="CreateInspection",
            ),
            WorkflowStepDefinition(
                id="approval",
                type=WorkflowStepType.approval,
                approval_roles={"maintenance_engineer"},
            ),
            WorkflowStepDefinition(
                id="inspection",
                type=WorkflowStepType.action,
                operation="CreateInspection",
            ),
        ],
    )
)

instance = kinetic.start_workflow(
    "asset-risk-inspection",
    subject=ObjectRef(id="K-201", type="Compressor"),
    actor_id="agent-1",
    actor_roles={"ai_agent_recommender"},
    trigger_key="trip:K-201:1234",
)

approval = kinetic.pending_approval(instance.id)
kinetic.decide_approval(
    approval.id,
    actor_id="engineer-1",
    actor_roles={"maintenance_engineer"},
    approved=True,
)
```

Workflow parameters support exact-value references for `${subject.id}`, `${subject.type}`, `${input.<name>}` and prior step results through `${step.<step-id>...}`.

## Explicit non-goals of the first kernel

The following remain part of the broader #67 program and are **not** claimed by this implementation:

- event/state/time trigger subscriptions;
- asynchronous or long-running action workers;
- retries, timeouts and cancellation policies;
- automatic compensation/rollback orchestration;
- first-class Outcome records;
- external SAP/PI/OSDU/P6 writeback verification and reconciliation;
- queueing, backpressure, DLQ or circuit-breaker behavior;
- distributed workflow locking, leasing or horizontally scaled workers;
- workflow REST/SDK/MCP public surfaces;
- workflow-level OpenTelemetry instrumentation.

Those capabilities should build on the durable contracts in this kernel rather than move process state into UI, agent or source-system-specific orchestration.

## Recommended next slices

1. Add durable retry/timeout/cancellation state and safe step retry semantics.
2. Add explicit compensation execution over completed compensatable Action steps.
3. Integrate #57 external writeback verification and pending external-action states.
4. Add event/state/manual trigger contracts and durable trigger deduplication.
5. Add workflow telemetry and public API/SDK surfaces after the runtime contract stabilizes.
6. Qualify the full reliability-maintenance reference workflow required by #67.
