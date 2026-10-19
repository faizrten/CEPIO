# CEPIO Application Contract v0.2

## Purpose

Application Contract v0.2 makes the v0.1 `SkillInvocation` / `SkillEvaluation` envelope executable without introducing transport-specific Skill logic.

The canonical flow is now:

```text
SkillInvocation
      +
ExecutionContext  <- trusted host identity
      |
      v
actor-aware Skill preflight
      |
  READY / BLOCKED
      |
      v
identity-matched executable Skill binding
      |
      v
restricted SkillExecutionHost
      |
      +--> actor-scoped object reads
      +--> policy-authorized CEPIO Functions
      |
      v
SkillExecutionOutput
      |
      +--> optional DecisionProposal
      |          |
      |          v
      |   governed Decision persistence
      |
      v
SkillEvaluation
```

Current application-contract version: `0.2.0`.

## New v0.2 contracts

### `SkillExecutorRegistry`

A host-local mapping from stable Skill identity to executable procedure. It does not decide admission. `SkillRegistry` remains authoritative for static/runtime Skill capability and actor-aware READY preflight.

Duplicate executable bindings fail closed.

### `SkillExecutionHost`

Executable Skill code receives a restricted host rather than direct CEPIO runtime access. The v0.2 host exposes only:

- actor-scoped object reads;
- policy-authorized registered CEPIO Function calls.

The host does not expose direct Action execution, policy mutation, repository mutation, identity mutation, or source-system writeback.

### `SkillExecutionOutput`

An internal procedure result containing:

- recommendation;
- structured outputs;
- additional evidence references;
- additional assessment references;
- an optional `DecisionProposal`;
- diagnostic messages.

The procedure cannot assign the Decision creator. `CEPIOApplicationService` persists any proposal with trusted host identity.

### `SkillInvocation.assessment_refs`

v0.2 adds protocol-neutral assessment references to the invocation so existing uncertainty/risk/assessment lineage can survive Skill execution without copying assessment payloads into the application contract.

## `evaluate_skill`

`CEPIOApplicationService.evaluate_skill(invocation, context)` is the v0.2 execution entry point.

It must:

1. re-run actor-aware preflight for every invocation;
2. dispatch only a READY, identity-matched executable binding;
3. fail closed when the Skill is unknown, BLOCKED, or not executable;
4. execute through `SkillExecutionHost` rather than exposing the runtime directly;
5. preserve input evidence and assessment references in the result;
6. merge additional evidence/assessment references deterministically;
7. persist an optional Decision through the existing governed Decision path;
8. preserve host correlation context;
9. never execute an operational Action merely because a Skill recommended one.

`completed`, `blocked`, and `failed` remain the protocol-neutral result states.

## Reference executable Skill: maintenance deferral

The first bound reference is:

`cepio.skill.maintenance.assess-maintenance-deferral`

It uses the already-qualified maintenance-deferral runtime capabilities:

- governed Equipment, WorkOrder and Risk context;
- `evaluateMaintenanceDeferralRisk`;
- `maintenance-deferral-decision`;
- `DeferWorkOrder` as recommendation/handoff only for the AI recommender role.

The reference procedure requires:

```text
subject = Equipment
parameters.work_order_id
parameters.risk_id
parameters.proposed_deferral_hours
```

The deterministic runtime function validates the Equipment→WorkOrder and Equipment→Risk graph and interprets governed Risk evidence. The Skill does not manufacture a new engineering risk model.

When the proposed window is supported, the Skill may persist a Decision recommending `DeferWorkOrder`. When the window is unsupported or constrained, it persists a do-not-defer Decision with no recommended Action.

In both cases the Skill itself does **not** execute `DeferWorkOrder`.

## Authority boundary

The intended reference identity is `ai_agent_recommender`.

```text
AI recommender
     |
     +--> read governed context
     +--> call approved deterministic functions
     +--> propose maintenance-deferral Decision
     +--> recommend DeferWorkOrder
     X--> execute DeferWorkOrder
```

An over-authorized maintenance manager is intentionally BLOCKED by this Skill's preflight because the Skill contract declares recommendation/handoff authority, not direct execution authority.

This preserves the existing recommend-before-act boundary.

## Evidence and assessment lineage

v0.2 preserves caller-supplied evidence and assessment references and allows a procedure to add the governed objects it actually consumed. Duplicate references are removed deterministically.

The maintenance reference adds the governed Risk and WorkOrder objects it used. The typed risk assessment returned by `evaluateMaintenanceDeferralRisk` is included as structured output; it is not falsely represented as a persisted CEPIO object unless a later runtime capability explicitly persists it.

## Failure semantics

- unknown Skill identity → `blocked`;
- preflight not READY → `blocked` with blocker codes;
- READY but executable binding absent → `blocked`;
- governed procedure validation failure → `failed`;
- successful procedure → `completed`;
- operational Action execution remains a separate application-contract operation.

Unexpected programming errors are not intentionally converted into successful or blocked evaluations.

## Protocol status

v0.2 still does not add or change REST, MCP, or SDK endpoints. Those surfaces continue to operate as before.

The next protocol-convergence milestone will project this same `evaluate_skill` operation onto REST, MCP and SDK and then prove cross-protocol semantic equivalence.

## Qualification requirements

The v0.2 reference tests must prove:

- READY preflight is mandatory;
- an over-authorized actor is BLOCKED before procedure execution;
- an executable binding is required;
- invalid governed evidence fails without persisting a Decision;
- the successful Skill Decision creator is host-injected;
- evidence and assessment references survive execution;
- supported and unsupported deferral windows produce deterministic outcomes;
- Skill evaluation never changes WorkOrder state;
- direct Function calls are re-authorized at the application-service boundary;
- duplicate executable Skill registrations fail closed.
