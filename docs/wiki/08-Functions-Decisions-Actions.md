# Functions, Decisions, Actions and Workflows

## Why CEPIO models kinetics

A useful Industrial Operating Intelligence layer must represent not only what the enterprise **is**, but what it can **calculate, decide, authorize, do and verify**.

This is the kinetic dimension of CEPIO.

The governing chain is:

```text
Evidence
 -> Function / Skill reasoning
 -> Recommendation
 -> Decision
 -> Authorization
 -> Action
 -> External execution
 -> Verification / reconciliation
 -> Outcome
```

The boundaries in that chain are deliberate:

```text
Knowledge != Authority
Recommendation != Execution
Source acknowledgement != Verified Outcome
```

## Function

A Function is a typed operation that derives information without itself implying an external side effect.

Examples:

- calculate production exposure;
- evaluate maintenance-deferral risk;
- compute performance variance;
- identify dependencies/blast radius;
- quantify information gain;
- determine material-shortage impact.

Function contracts should define:

```text
Function
  - stable identity
  - input types
  - output type
  - applicable target types
  - authorization policy
  - implementation binding
  - deterministic/evidence expectations
```

## Skill

A Skill packages a bounded industrial procedure rather than one calculation.

```text
Skill dependencies
 -> runtime binding
 -> actor-aware preflight
 -> READY / BLOCKED
 -> restricted SkillExecutionHost
 -> governed reads / Functions
 -> optional Decision proposal
 -> SkillEvaluation
```

Important boundaries:

- declaration does not create missing capability;
- only READY Skills dispatch;
- Skills do not receive raw runtime/source-client access by default;
- Skill-generated Decision capability does not grant Action authority;
- a host can expose recommendation/Decision-only Skill behavior without execution tools.

See [Skill Runtime Capability Contracts](../skill-runtime-capabilities.md) and [Skill Runtime Preflight](../skill-runtime-preflight.md).

## Decision

A Decision connects governed evidence/reasoning to a selected conclusion or course of action.

A Decision can capture:

- target/subject;
- evidence references;
- temporal context;
- Function/Skill outputs;
- recommendation;
- selected option;
- actor/agent identity;
- confidence/rationale;
- authority/approval context.

### Named Decision capability contracts

`DecisionDefinition` gives a stable capability name plus allowed subject types and governed Action vocabulary.

A typed Decision violating the registered capability fails closed before persistence.

Decision type does **not** create an ontology class and does **not** grant execution authority.

The reliability slice includes `maintenance-intervention-recommendation` over `Equipment` with bounded Action vocabulary such as `CreateWorkOrder`, `CreateInspection` and `EscalateRisk`.

## Action

An Action changes CEPIO state or invokes an external effect.

Examples:

- create a work order;
- request inspection;
- issue procurement request;
- change an approved schedule;
- perform a governed source-system transaction.

## Action execution boundary

```text
Action intent / request
 -> resolve authenticated actor
 -> resolve target + Action definition
 -> policy / authority
 -> authorized idempotency replay check
 -> preconditions
 -> CEPIO Action audit/effect
 -> external-action binding if applicable
 -> source acknowledgement/read-back
 -> verification
 -> reconciliation
 -> Outcome
```

Policy occurs before replay so an old successful idempotent result cannot become an authorization bypass.

## Preconditions

Actions may require conditions such as:

- target state;
- actor role/authority;
- Decision linkage;
- explicit approval;
- expected version;
- maintenance/production window;
- required evidence;
- allowed risk/guardrail state.

## Idempotency

Side effects must be safe against retry/replay.

CEPIO scopes idempotency to the appropriate actor/Action/target/external operation context and uses deterministic workflow/external-action keys where appropriate.

Idempotency does not substitute for source verification.

## Durable workflow runtime

Current mainline workflow capability is materially beyond the original kernel.

```text
WorkflowDefinition
        |
        v
WorkflowInstance
        |
        +--> Function
        +--> Decision
        +--> ApprovalTask -- durable pause / resume
        +--> Action
        +--> external verification wait
        |
        v
WorkflowOutcome
```

Current foundations include:

- durable/versioned workflow definitions and instances;
- Function, Decision, Approval and Action steps;
- restart-safe state;
- human pause/resume;
- trigger-key deduplication foundations;
- bounded Function retry/timeout;
- workflow cancellation;
- supported reverse compensation;
- async external Action lifecycle;
- identity revalidation;
- external verification wait;
- exact workflow policy-version lineage;
- immutable terminal Outcome.

Workflow execution state remains distinct from canonical industrial object state.

## Execution resilience

Side-effect-free Function steps may use bounded retries/timeouts.

Governed Action retries require stronger proof because a transport error can occur after the external source already committed the write.

For unknown external write state:

```text
transport uncertainty
 -> UNKNOWN
 -> no blind redispatch
 -> reconcile authoritative source truth
 -> verified / failed / still unresolved
```

Cancellation and compensation remain governed operations. Compensation does not erase the historical failure/cancellation; the original terminal state remains auditable while compensation status is recorded separately.

See [Kinetic Execution Resilience](../kinetic-execution-resilience.md).

## External Action lifecycle

The external action control plane recovers trusted source system/operation/identity from CEPIO-owned binding configuration and Action audit rather than accepting arbitrary client write payload authority.

```text
CEPIO Action
    |
resolve canonical -> external identity
    |
PENDING_EXECUTION
    |
source write
    |
ACKNOWLEDGED
    |
PENDING_VERIFICATION
    |
    +--> VERIFIED
    +--> FAILED
    +--> UNKNOWN -> reconcile
```

Canonical-to-source identity is explicit and fail-closed. Missing, stale, conflicting or ambiguous identities do not reach source execution.

A source acknowledgement is not proof of business completion. `verify_write(...)` checks the expected source state; `reconcile_write(...)` resolves uncertain outcomes.

See [Governed External Action Runtime](../external-action-runtime.md) and [Kinetic External Verification Gate](../kinetic-external-verification-v0.4.md).

## Outcome

`WorkflowOutcome` records verified terminal meaning rather than treating dispatch success as the end of the industrial loop.

Outcomes support:

- execution result;
- verification/reconciliation status;
- workflow/Decision/Action lineage;
- policy evidence;
- future evaluation of whether the intervention actually worked.

This completes the current conceptual loop:

```text
Observe -> Understand -> Reason -> Decide
 -> Authorize -> Act -> Verify -> Learn
```

"Learn" means generating governed outcome/evaluation evidence. It does **not** mean silently training global CEPIO from customer operational data.

## Performance-triggered response

Performance Contracts can identify KPI/KR/guardrail deviation and bind a **recommend-only** response pathway toward a governed workflow/Decision.

A performance deviation does not automatically execute an operational Action. Normal authority/policy still applies.

## Human and AI operating model

A useful authority ladder is:

```text
Observe
 -> Explain
 -> Evaluate Skill / Function
 -> Recommend
 -> Persist Decision
 -> Request approval
 -> Execute bounded Action
 -> Verify source Outcome
```

AI agents gain operational authority only through explicit authenticated policy, not because an MCP tool exists or a model can generate a plausible Action request.

For Microsoft-hosted agents:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

The initial Reliability Foundry G1 path deliberately exposes Decision-oriented tools while excluding Action execution at the host profile level.

## Current product claim boundary

The workflow/Action foundation is substantial on `main`, but **v0.5 CONNECT is still open** until real SAP/PI + third-source context and one governed verified/reconciled writeback complete the release gate.

Likewise, **v0.6 EXECUTE** remains a future product gate until a serious reference application demonstrates the full loop over qualified live integrations.

See [Current State](../current-state.md) and [Roadmap](17-Roadmap.md).
