# ADR-0019: Protocol-converged Skill evaluation

- Status: Accepted
- Date: 2026-10-19
- Decision owners: CEPIO Core

## Context

Application Contract v0.2 established executable Skill semantics through `CEPIOApplicationService.evaluate_skill`, including actor-aware preflight, a restricted execution host, governed deterministic Function calls, evidence continuity, Decision proposal/persistence, and separation from operational Action execution.

Before this ADR, that qualified execution path was not yet exposed consistently through CEPIO's external protocol surfaces. REST continued to operate directly on the runtime, the Foundry MCP gateway owned separate governed methods, and SDKs had no Skill method.

If each protocol implemented Skill semantics independently, CEPIO would risk divergent authority, evidence, Decision, and error behavior across humans, applications, and agents.

## Decision

CEPIO will expose executable Skill evaluation as a protocol projection over one shared application-service execution path.

The canonical execution operation is:

```text
CEPIOApplicationService.evaluate_skill(SkillInvocation, ExecutionContext)
    -> SkillEvaluation
```

The shipped executable Skill composition is built by:

```text
cepio.application_runtime.build_application_service(runtime)
```

Protocol adapters must use that composition rather than independently registering executable Skills.

### REST

Public API v1 adds:

```text
POST /api/v1/skills/evaluate
operationId: evaluateSkill
```

The host derives authenticated actor identity and roles, constructs `ExecutionContext`, and delegates to the shared application service.

### SDKs

Python and TypeScript SDKs project the REST operation. They do not implement Skill logic client-side.

### MCP

The Foundry MCP surface adds:

```text
cepio_evaluate_skill
```

The gateway maps its verified host actor into `ExecutionContext` and delegates to the same application service.

Actor identity and roles remain absent from model-callable MCP arguments.

## Contract versioning

The application envelope remains version `0.2.0` because v0.3 introduces protocol projections without changing the `SkillInvocation` or `SkillEvaluation` schema.

`v0.3` therefore names the protocol-convergence capability milestone, not a breaking or additive envelope schema revision.

## Conformance requirement

The same synthetic invocation must produce semantically equivalent results through:

1. direct application-service invocation;
2. raw REST;
3. Python SDK over REST;
4. actual MCP protocol.

Generated Decision IDs and timestamps may differ. Material Skill, evidence, output, recommendation, Decision authority, creator identity, and metadata semantics must match.

## Authority boundary

Protocol convergence does not change the recommend-before-act rule.

A Skill can return a recommendation and may persist a governed Decision where policy permits. It cannot infer operational authority from successful reasoning and cannot execute an Action unless the separate Action Runtime path explicitly permits that action.

For the maintenance-deferral reference Skill, `DeferWorkOrder` remains outside Skill execution.

## Consequences

### Positive

- one execution semantics across agents, apps, and REST consumers;
- protocol adapters become thin identity/serialization projections;
- no duplicated Skill registry or executor composition;
- cross-protocol conformance becomes testable;
- Foundry/MCP can consume Industry IQ without gaining a policy bypass;
- SDK evolution remains aligned to the accepted OpenAPI contract.

### Trade-offs

- the REST Skill endpoint constructs the shipped application-service composition for the active runtime; later scale work may introduce lifecycle-managed composition/caching while preserving behavior;
- only the Skill path is converged in v0.3; legacy object/query/function/action routes are not automatically migrated;
- SDK Skill evaluation is REST-backed, so the SDK is a typed client projection rather than an independent protocol runtime.

## Rejected alternatives

### Implement Skill logic separately in MCP

Rejected because it would create agent-specific execution semantics and a likely authority bypass over time.

### Let SDKs execute Skill procedures locally

Rejected because local execution would not share server-side actor context, policy, evidence, Decision persistence, or runtime state.

### Add actor identity/roles to SkillInvocation

Rejected because authority must come from authenticated host context, never caller-selected application payload.

### Increment application envelope version solely for transport projection

Rejected because the envelope shape and semantics are unchanged.

## Follow-up

- qualify generic context assembly behind the application service;
- converge Decision and ActionIntent projections incrementally;
- prove a second executable Skill from another industrial domain;
- use the MCP projection in live Foundry integration and subsequent Copilot consumption proofs.
