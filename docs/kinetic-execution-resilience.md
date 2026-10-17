# CEPIO Kinetic Execution Resilience v0.2

## Status

This document describes the second implementation slice of Issue #67. It builds on the durable kinetic workflow kernel by adding bounded retry, timeout, cancellation and compensation semantics without yet introducing asynchronous external-action workers or source-system reconciliation.

The governing principle is:

> computation may be retried when safe; external side effects must not be automatically replayed until CEPIO can prove idempotent source-system execution and reconciliation.

## Execution model

The v0.2 resilience path is:

```text
Workflow step
   |
   +-- Function -----------------------------+
   |       |                                  |
   |       +-- success --------------------> next step
   |       +-- transient failure -> retry ----+
   |       +-- timeout -> retry / terminal failure
   |
   +-- Decision -> single durable execution
   |
   +-- Approval -> durable wait/resume
   |
   +-- Action -> single governed execution
           |
           +-- success -> next step
           +-- rejected/failed -> terminal workflow failure

terminal failure / cancellation
   |
   v
reverse completed compensatable Actions
   |
   v
policy-gated compensation + audit
```

## StepExecutionPolicy

A Function step may declare:

- `max_attempts` — bounded total attempts, including the first attempt;
- `timeout_seconds` — elapsed-time threshold for one synchronous Function attempt;
- `retry_delay_seconds` — bounded delay before the next attempt;
- `compensate_on_terminal_failure` — whether earlier compensatable Actions are rolled back after terminal failure.

The default is one attempt, no timeout and compensation enabled on terminal workflow failure.

### Why automatic Action retry is blocked

Action steps are deliberately restricted to one attempt with no synchronous timeout policy in this slice.

An Action may already have caused an external effect even when the caller observes a timeout or transport failure. Retrying it without source-system idempotency and reconciliation can create duplicate work orders, duplicate schedule changes or duplicate enterprise transactions.

Therefore CEPIO v0.2 fails closed:

- automatic retry/timeout policies are accepted only for `function` steps;
- `decision`, `approval` and `action` steps reject retry/timeout configuration;
- future Action retry belongs with #57 governed writeback/reconciliation and the asynchronous Action state model from #67.

## Retry semantics

Function attempts are recorded separately from the base workflow step state.

`StepResilienceState` persists:

- attempt count;
- last error;
- last attempt duration;
- timeout flag;
- compensation status/result for an Action step if later rolled back.

Retry events are added to immutable workflow history:

- `step_attempt_started`;
- `step_retry_scheduled`;
- `step_failed` with final attempt count.

Authorization, missing workflow inputs, invalid definitions and explicit non-retryable failures fail immediately rather than consuming the retry budget.

## Timeout semantics

v0.2 timeouts are synchronous elapsed-time guards for Function steps. They do not terminate a worker thread or external process. If the Function returns after the configured limit, the attempt is classified as timed out and may be retried according to its policy.

This is intentionally not the long-running Action timeout model. Pending external execution, verification deadlines, worker leases and cancellation tokens belong to a later asynchronous slice.

## Cancellation

`ResilientKineticRuntime.cancel(...)` creates an explicit workflow cancellation boundary.

A cancellation is allowed when:

- the caller is the workflow initiator; or
- one of the caller's roles is listed in the workflow `WorkflowControlPolicy.cancel_roles`.

The caller must also retain authorized visibility of the workflow subject through the normal CEPIO read-policy boundary.

Cancellation records:

- cancellation actor;
- reason;
- immutable `workflow_cancellation_requested` history;
- optional compensation of completed compensatable Actions;
- terminal `workflow_cancelled` history.

A cancelled workflow cannot later resume through the normal workflow engine.

## Compensation orchestration

Compensation walks previously executed Action steps in reverse order.

Only Actions that registered a CEPIO `compensation_handler` participate. For every compensation:

1. CEPIO resolves the current canonical target object.
2. The compensating actor is evaluated against the same governed Action definition.
3. Policy must return `allow`; compensation fails closed otherwise.
4. The registered compensation handler executes.
5. A compensated `ActionResult` is written through the existing immutable Action audit path.
6. A deterministic compensation idempotency key is cached.
7. `step_compensated` is appended to workflow history.

The compensation idempotency key is scoped to:

`workflow instance + compensation + workflow step + actor/action/target`

This protects replay of the local compensation path while preserving the existing CEPIO Action authorization boundary.

`WorkflowResilienceState.compensation_status` is one of:

- `not_required`;
- `pending`;
- `completed`;
- `failed`.

A workflow that failed remains `failed` even if compensation succeeds. A cancelled workflow remains `cancelled`. Compensation status is recorded separately so the original terminal reason is not erased.

## Persistence

Two resilience repositories are provided:

- `InMemoryResilienceRepository` for tests/local development;
- `SQLiteResilienceRepository` for durable reference execution.

The SQLite resilience repository stores:

- per-step execution policies;
- workflow control policies;
- per-step retry/timeout/compensation state;
- per-workflow cancellation and compensation state.

It can share the same SQLite file as the v0.1 workflow repository and CEPIO reference runtime while retaining separate tables.

## Reference usage

```python
from cepio import (
    StepExecutionPolicy,
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowStepType,
    build_resilient_kinetic_runtime,
    build_runtime,
)

runtime = build_runtime(sqlite_path="cepio.db")
kinetic = build_resilient_kinetic_runtime(runtime, sqlite_path="cepio.db")

kinetic.register_resilient_workflow(
    WorkflowDefinition(
        id="risk-assessment",
        name="Risk assessment",
        steps=[
            WorkflowStepDefinition(
                id="risk",
                type=WorkflowStepType.function,
                operation="calculateAssetRisk",
                parameters={"asset_id": "${subject.id}"},
            )
        ],
    ),
    step_policies={
        "risk": StepExecutionPolicy(
            max_attempts=3,
            timeout_seconds=2.0,
            retry_delay_seconds=0.1,
        )
    },
)
```

## Qualification scenarios

The v0.2 regression suite proves:

1. a transient Function failure retries and succeeds on the next bounded attempt;
2. a Function exceeding its timeout retries and reaches explicit terminal failure after exhausting its budget;
3. cancelling a paused workflow reverses an earlier compensatable `EscalateRisk` Action;
4. a later terminal workflow failure automatically compensates an earlier completed Action;
5. unsafe automatic retry configuration on an Action step is rejected at workflow registration;
6. resilience policy and execution state survive SQLite repository restart.

## Still out of scope

The following remain future #67/#57 work:

- asynchronous / pending external Action execution;
- source-system writeback verification and reconciliation;
- safe automatic Action retry after uncertain external outcomes;
- retry scheduling through queues/workers rather than local synchronous delay;
- distributed workflow leases and concurrency control;
- compensation approval workflows for high-risk rollback;
- cancellation of an in-flight external operation;
- dead-letter queues and circuit breakers;
- first-class Outcome records;
- event/state/time trigger subscriptions;
- REST/SDK/MCP workflow control surfaces;
- workflow-level OpenTelemetry instrumentation.

## Next slice

The next kinetic slice should connect the workflow engine to #57 and introduce an asynchronous Action lifecycle such as:

`REQUESTED -> PENDING_EXTERNAL_EXECUTION -> PENDING_VERIFICATION -> VERIFIED | FAILED | UNKNOWN`

Only after that contract exists should CEPIO permit automatic retry of industrial side effects.
