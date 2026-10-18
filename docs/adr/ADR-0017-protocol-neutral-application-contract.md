# ADR-0017: Protocol-neutral CEPIO Application Contract

Status: Proposed

## Context

CEPIO already has several mature runtime contracts: typed objects and relationships, temporal state, provenance, policy, Decisions, governed Actions, Skill preflight, source-system bindings, and Industry IQ packs. It also exposes multiple access surfaces through REST, MCP, and SDK code.

Historically, documentation described the public API as the product contract. That framing is now too narrow for the CEPIO North Star: thin infrastructure, thick Industry IQ, portable across data platforms, agent hosts, and user experiences.

If REST, MCP, SDKs, or future event interfaces each become independent semantic implementations, CEPIO will accumulate protocol-specific behavior and lose portability. The risk is especially high around identity, evidence, Skills, Decisions, Actions, and policy.

## Decision

Introduce a versioned, protocol-neutral **CEPIO Application Contract** between runtime/Core semantics and access protocols.

The contract does not replace existing semantic/runtime contracts. It provides stable request/result envelopes and a thin service facade over them.

Application Contract v0.1 adds:

- `ExecutionContext`;
- `ContractMetadata`;
- `EvidenceReference`;
- `ContextEnvelope`;
- `SkillInvocation`;
- `SkillEvaluation`;
- `DecisionProposal`;
- `ActionIntent`;
- `CEPIOApplicationService`.

REST, MCP, SDKs, and future event interfaces are treated as protocol projections over this contract.

## Identity and authority

Caller-visible `DecisionProposal`, `ActionIntent`, and `SkillInvocation` payloads do not contain actor identity or roles.

Trusted hosting code supplies an `ExecutionContext`. The application service then injects that identity into existing runtime models such as `ActionRequest` and persisted `Decision.created_by`.

This preserves the principle:

> identity comes from the trusted host; industrial authority comes from CEPIO policy and runtime semantics.

## Reuse of existing runtime semantics

The application layer does not introduce a second Decision engine, Action engine, policy engine, evidence store, or provenance store.

`CEPIOApplicationService` delegates to the existing runtime for:

- object visibility;
- Decision capability validation;
- Decision authorization;
- Decision persistence;
- Action policy evaluation;
- Action preconditions;
- idempotency;
- execution;
- audit.

Evidence and uncertainty are represented by governed object references so CEPIO Core remains the semantic authority.

## Skill boundary

v0.1 defines stable `SkillInvocation` and `SkillEvaluation` envelopes but does not invent a new generic Skill execution engine.

The existing Skill preflight contract remains authoritative for admission. A subsequent increment will bind executable Industry IQ Skills to the application contract and require READY preflight before dispatch.

This sequencing avoids duplicating the current `SkillRegistry` and `IndustryIQPackRegistry` before their execution boundary is deliberately composed.

## Provider neutrality

No v0.1 application-contract type contains Fabric, Foundry, Azure, Cognite, OSDU, SAP, PI, HTTP, or MCP-specific fields.

Source-system and platform bindings remain below the application contract. A provider may change while the application contract remains stable.

## Consequences

Positive:

- CEPIO gains a stable semantic application boundary independent of transport;
- REST, MCP, and SDK convergence becomes testable;
- authenticated actor identity cannot be supplied in Action or Decision caller payloads;
- provider portability becomes an explicit architecture property;
- Industry IQ can deepen without expanding protocol-specific implementations;
- existing API v1 remains compatible because v0.1 is additive.

Trade-offs:

- there is temporarily an additional application layer while existing REST/MCP functions still call runtime methods directly;
- `SkillInvocation`/`SkillEvaluation` are defined before generic Skill execution dispatch is complete;
- some existing public API request models will later need adapters into application-contract types.

## Validation

The v0.1 change is acceptable only if:

1. existing REST/MCP/OpenAPI behavior is unchanged;
2. contract caller payloads do not expose actor identity or roles;
3. Decision proposals receive `created_by` from trusted execution context;
4. Action intents receive actor identity/roles from trusted execution context;
5. existing Decision -> Action audit causality is preserved;
6. existing runtime policy continues to deny unauthorized Decision/Action operations;
7. contract models serialize without protocol-specific semantics;
8. the full CEPIO CI, quality, security, and architecture gates remain green.

## Follow-up

1. Add executable Skill registration/dispatch over `SkillInvocation` / `SkillEvaluation`.
2. Add source-neutral `ContextEnvelope` assembly.
3. Map REST endpoints onto `CEPIOApplicationService` without changing public v1 behavior.
4. Map MCP tools onto the same application service.
5. Add SDK methods over the same contract.
6. Add cross-protocol conformance tests.
7. Prove equivalent Skill behavior across synthetic and Fabric bindings, then a second non-Fabric provider.
