# CEPIO Protocol Convergence v0.3

## Status

Implemented reference contract for one executable Industry IQ Skill across CEPIO's direct application layer, REST API v1, Python/TypeScript SDK projection, and Microsoft Foundry MCP surface.

The application-envelope schema remains `0.2.0`. v0.3 is a capability milestone: it projects the already-qualified `SkillInvocation` / `SkillEvaluation` contract through multiple protocols without changing the envelope itself.

## Objective

Prove the following invariant:

> One Skill identity, one SkillInvocation, one trusted actor context, one CEPIOApplicationService execution path, and one SkillEvaluation semantic result regardless of protocol.

```text
                   SkillInvocation
                         |
          +--------------+--------------+
          |              |              |
        REST           Python SDK      MCP
          |              |              |
          |          REST projection    |
          +--------------+--------------+
                         |
              CEPIOApplicationService
                         |
                   evaluate_skill
                         |
                admitted Skill binding
                         |
                  SkillEvaluation
```

## Shared application-service builder

`cepio.application_runtime.build_application_service(runtime)` is the shipped composition root for executable Skills.

It currently registers:

- `cepio.skill.maintenance.assess-maintenance-deferral` admission contract;
- the matching maintenance-deferral executable procedure.

Protocol adapters must use this builder rather than independently constructing Skill registries or executable bindings.

This preserves a single admitted Skill set across REST, MCP, SDK-backed REST calls, and future projections.

## REST projection

Public API v1 adds:

```text
POST /api/v1/skills/evaluate
operationId: evaluateSkill
```

The request body is exactly `SkillInvocation`.

Caller-selected actor identity and roles are not part of the contract. The REST host derives authenticated `ActorContext`, maps it into trusted `ExecutionContext`, and calls:

```python
service.evaluate_skill(invocation, context)
```

The response is exactly `SkillEvaluation`.

Normal Skill admission/authority failures remain semantic results such as `blocked`. Host-level authorization failures outside normal preflight are returned through the existing public API error boundary.

## SDK projection

The Python SDK adds:

```python
client.evaluate_skill(invocation) -> SkillEvaluation
```

The TypeScript client adds:

```ts
client.evaluateSkill(invocation): Promise<SkillEvaluation>
```

SDKs do not implement Skill logic. They serialize the same `SkillInvocation` to `POST /api/v1/skills/evaluate` and validate/return the same `SkillEvaluation` contract.

## MCP projection

The Foundry MCP server adds:

```text
cepio_evaluate_skill
```

Its only semantic argument is `SkillInvocation`. Actor identity/roles remain injected by the authenticated MCP hosting context and are not model-callable tool arguments.

The MCP gateway maps its verified actor into the same `ExecutionContext` and delegates to the same application service.

## Conformance rule

Cross-protocol conformance tests use one synthetic maintenance-deferral case and the same invocation through:

1. direct `CEPIOApplicationService.evaluate_skill`;
2. raw REST `/api/v1/skills/evaluate`;
3. Python SDK calling the REST operation;
4. actual MCP protocol calling `cepio_evaluate_skill`.

Generated Decision IDs and timestamps are intentionally non-deterministic and are excluded from semantic equality comparison. All material semantics must match:

- Skill identity;
- subject;
- completion/block/failure status;
- recommendation;
- deterministic outputs;
- evidence and provenance references;
- assessment references;
- Decision type, subject, recommendation, recommended action and creator identity;
- messages;
- application-contract metadata.

## Authority invariant

Protocol convergence must not collapse reasoning and action authority.

The maintenance-deferral Skill may:

- read actor-authorized governed context;
- call explicitly authorized deterministic Functions;
- evaluate deferral risk;
- return a recommendation;
- persist a governed Decision with host-injected creator identity.

It may not execute `DeferWorkOrder`.

Operational action remains a separate governed operation through the Action Runtime.

## Security invariant

Across every protocol:

- actor identity originates from the trusted host;
- actor roles originate from the trusted host;
- SkillInvocation does not grant authority;
- READY preflight is performed at execution time;
- Skill procedure code receives a restricted host, not raw runtime access;
- Function authorization is rechecked at the application boundary;
- Decision creator identity is host injected;
- Action execution remains separate.

## Scope boundary

v0.3 proves protocol convergence for the executable Skill path only.

It does not yet claim that every legacy REST/MCP operation has been migrated behind the application service. Existing object/query/function/action surfaces remain compatible and can converge incrementally without changing their accepted external contracts.

## Next increments

Recommended follow-on work:

1. add a generic context-assembly application operation so agents/apps do not separately reconstruct industrial context;
2. converge Decision retrieval/proposal and ActionIntent projection behind the same service;
3. add event-driven Skill invocation after trigger semantics are qualified;
4. qualify a second cross-domain Skill to prove the protocol pattern is not maintenance-specific;
5. bind the MCP Skill operation into the live Foundry integration proof and then M365 Copilot consumption path.
