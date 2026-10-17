# Functions, Decisions and Actions

## Why CEPIO models kinetics

A useful industrial ontology must represent not only what things **are**, but what the enterprise can **calculate, decide and do**.

This is the kinetic dimension of CEPIO.

## Function

A function is a typed operation that derives information.

Examples:

- calculate expected production loss from compressor downtime;
- evaluate remaining margin exposure;
- calculate reliability risk score;
- identify dependencies within N hops;
- determine material shortage impact.

Functions should have explicit contracts:

```text
Function
  - name
  - input types
  - output type
  - allowed target types
  - authorization policy
  - implementation binding
```

## Decision

A decision links evidence and reasoning to a recommendation or selected course of action.

A decision record can capture:

- target object;
- evidence references;
- relevant state and time context;
- function outputs;
- recommended action;
- actor/agent;
- confidence or rationale;
- approval state.

### Named decision capability contracts

CEPIO can register a `DecisionDefinition` separately from persisted `Decision` records. A definition gives a stable runtime capability name plus allowed subject types and allowed governed actions. A typed Decision that violates that contract fails closed before persistence.

This does **not** make Decision types ontology classes and does not grant action authority. Existing Decisions without `decision_type` remain backward-compatible. The first registered capability is `maintenance-intervention-recommendation`, constrained to `Equipment` subjects and the governed `CreateWorkOrder`, `CreateInspection` and `EscalateRisk` action vocabulary.

See [Skill-facing runtime capability contracts](../skill-runtime-capabilities.md) for the first end-to-end binding slice.

## Action

An action changes CEPIO state or invokes an external effect.

Examples:

- create work order;
- request inspection;
- approve maintenance scope;
- issue a procurement request;
- trigger a schedule change;
- acknowledge an alarm workflow.

## Action execution boundary

```text
Request action
   |
Resolve actor + target + action
   |
Policy evaluation
   |
Authorized?
   +-- no -> deny + audit
   |
   v
Idempotency check
   |
Preconditions
   |
Execute CEPIO effect
   |
External adapter if applicable
   |
Record acknowledgement/reconciliation
   |
Immutable audit
```

## Preconditions

Actions may require conditions such as:

- object is in a specific state;
- actor has specific role;
- an approval exists;
- expected object version matches;
- related work item exists;
- maintenance window is active;
- risk threshold is satisfied.

## Idempotency

External enterprise actions must be safe against retries.

Idempotency keys are scoped so one actor cannot reuse another actor's prior successful result to bypass authorization.

## Compensation and reconciliation

Enterprise actions are not always atomic across systems.

CEPIO therefore needs explicit metadata for:

- external acknowledgement;
- retry state;
- reconciliation status;
- compensation guidance where applicable;
- dead-letter handling in production integrations.

## Workflow and orchestration layer

Individual Functions, Decisions and Actions are execution primitives. The kinetic runtime adds durable process state around those primitives.

The first workflow kernel introduces:

```text
WorkflowDefinition
        |
        v
WorkflowInstance
        |
        +--> Function
        |
        +--> Decision
        |
        +--> ApprovalTask -- pause / durable wait
        |
        +--> Action -- existing CEPIO policy + idempotency + audit
        |
        v
Completed / Failed
```

Workflow state is deliberately separate from canonical industrial semantic state. A workflow may operate on a Compressor or WorkOrder, but its execution cursor, approval state and step history are runtime process records rather than properties of that industrial object.

The reference implementation provides in-memory and SQLite workflow repositories. SQLite can restore a workflow that is paused for approval and resume it through a new runtime process.

Agent authority does not flow through the workflow implicitly. An agent may run authorized functions and persist a recommendation, but a human approval task can transfer active execution identity to an authenticated human before the subsequent governed Action executes.

Workflow trigger keys deduplicate repeated starts, while Action steps receive deterministic workflow-step idempotency keys. This gives the first kernel replay protection at both process-start and side-effect boundaries.

See [Kinetic Runtime](../kinetic-runtime.md) for the focused contract and current non-goals.

## Execution resilience

The next kinetic slice adds durable execution-resilience state around the workflow kernel:

```text
Function
  +-- success -> next
  +-- transient failure -> bounded retry
  +-- timeout -> retry / terminal failure

terminal failure or cancellation
  -> reverse completed compensatable Actions
  -> policy check
  -> compensation handler
  -> Action audit
```

Retries and synchronous timeout guards are deliberately limited to side-effect-free Function steps. CEPIO does **not** automatically retry governed Action steps until the live-integration layer can prove source-system idempotency and reconciliation. A transport failure after creating a work order, for example, must not cause CEPIO to blindly create a second work order.

Workflow cancellation is an explicit governed control operation. The workflow initiator or a role declared in the workflow control policy can cancel, subject to normal visibility of the workflow subject. Cancellation may reverse earlier compensatable Actions in reverse execution order.

Compensation does not bypass Action governance. The compensating actor is evaluated against the same Action definition, and successful compensation is written through the immutable Action audit path with a deterministic compensation idempotency key.

The original terminal state remains authoritative: a failed workflow stays `failed` even if rollback succeeds, and a cancelled workflow stays `cancelled`. Compensation status is tracked separately as `not_required`, `pending`, `completed` or `failed`.

See [Kinetic Execution Resilience v0.2](../kinetic-execution-resilience.md) for the detailed retry, timeout, cancellation, persistence and compensation contract.

## Governed external action lifecycle

External enterprise writes are now modeled separately from the synchronous CEPIO Action result. A successfully authorized and audited CEPIO Action can be queued into the external-action control plane by its immutable `action_id`.

```text
CEPIO Action executed
        |
        v
resolve canonical -> external identity
        |
        v
PENDING_EXECUTION
        |
        v
adapter write
        |
        v
ACKNOWLEDGED
        |
        v
PENDING_VERIFICATION
        |
        +--> VERIFIED
        +--> FAILED
        +--> UNKNOWN -> reconcile source truth
```

The calling application does not provide the source system, source operation, actor, decision or arbitrary write payload. Those values are recovered from the CEPIO Action audit and from CEPIO-owned `ExternalActionBinding` configuration. This keeps adapters behind the same identity, policy and audit boundary as the original Action.

Canonical-to-source identity is explicit and fail-closed. A write requires exactly one usable mapping for the required source system and identity type; missing, stale, conflicting or ambiguous mappings never reach the adapter write call.

A source acknowledgement is not treated as proof of business completion. CEPIO persists `pending_verification` until `verify_write(...)` confirms the expected source state. If a transport failure makes the write outcome uncertain, CEPIO records `unknown` and forbids blind redispatch. `reconcile_write(...)` must resolve source truth first.

The adapter idempotency key is derived from source system, source operation and CEPIO `action_id`, preserving the causal chain from Decision -> Action -> Action audit -> adapter request -> verification/reconciliation.

See [Governed External Action Runtime](../external-action-runtime.md) for the focused writeback contract and current limitations.

## Human and AI operating model

A useful pattern is progressively increasing authority:

```text
Observe
 -> Explain
 -> Recommend
 -> Request approval
 -> Execute bounded action
 -> Observe outcome
```

AI agents should earn operational authority through explicit policy rather than obtain it implicitly because they can access an MCP tool.
