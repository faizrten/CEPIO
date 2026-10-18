# CEPIO Application Contract v0.1

## Purpose

CEPIO needs one stable application contract that survives changes in transport, hosting platform, model provider, and source-system binding.

The contract is the behavioral and semantic promise. REST, MCP, SDKs, event adapters, and future interfaces are projections of that promise.

```text
Applications / agents / workflows
             |
      +------+------+------+
      |      |      |      |
     REST   MCP    SDK   Events
      |      |      |      |
      +------+------+------+
             |
   CEPIO Application Contract
             |
      CEPIO Runtime / Core
             |
  Semantics - Policy - Skills
  Decisions - Actions - Evidence
```

## Version

Current application-contract version: `0.1.0`.

This version is additive. It does not change the accepted `/api/v1` OpenAPI route baseline or existing MCP tools.

## Layering

CEPIO distinguishes three contracts:

1. **Semantic/runtime contracts** define what CEPIO concepts mean and the invariants enforced by Core: identity, relationships, temporal state, provenance, policy, Decision, Action, and Industry IQ capabilities.
2. **Application contracts** define protocol-neutral requests/results used to call those capabilities safely.
3. **Protocol projections** map the application contract onto REST, MCP, SDKs, events, or other interfaces.

A protocol adapter must not invent new CEPIO semantics.

## v0.1 primitives

### `ExecutionContext`

Trusted hosting context containing:

- actor identity;
- governed CEPIO roles;
- tenant identity when available;
- correlation ID.

`ExecutionContext` is **not caller-controlled application payload**. REST derives it from authentication, MCP hosting derives it from the authenticated tool session, and embedded SDK/workflow hosts must supply it from their trusted identity boundary.

### `ContextEnvelope`

Portable industrial context containing:

- a subject CEPIO object;
- related CEPIO objects;
- references to governed evidence;
- references to uncertainty/confidence/other assessment objects;
- contract metadata.

The envelope references governed objects rather than copying source-system payloads into a new CEPIO data model.

### `EvidenceReference`

A reference to a CEPIO object used as evidence. The reference may describe its role as:

- `supporting`;
- `contradicting`;
- `contextual`;
- `assumption`.

The optional `provenance_ref` points to provenance information without making the application contract a second provenance store.

### `SkillInvocation`

Protocol-neutral request to evaluate a Skill:

- stable Skill ID;
- subject object reference;
- parameters;
- evidence references;
- contract metadata.

Actor identity and roles are deliberately absent.

### `SkillEvaluation`

Protocol-neutral Skill result:

- Skill ID and subject;
- `completed`, `blocked`, or `failed` status;
- recommendation;
- typed/structured outputs;
- evidence references;
- assessment references;
- optional persisted CEPIO `Decision`;
- diagnostic messages.

v0.1 defines the invocation/result envelope. Generic Skill execution dispatch will bind to this envelope in a subsequent increment rather than being invented separately by REST or MCP.

### `DecisionProposal`

Caller-visible proposal fields for a CEPIO Decision. `created_by` is not caller-controlled. `CEPIOApplicationService` injects the authenticated actor and preserves existing runtime Decision validation and policy authorization.

### `ActionIntent`

Caller-visible request for a governed Action. It includes the intended action, target, parameters, idempotency/correlation/workflow context, and optional Decision linkage.

It deliberately excludes `actor_id` and `actor_roles`.

## Application service

`CEPIOApplicationService` is the thin protocol-neutral facade over the existing runtime.

Current operations:

```text
read_object
preflight_skill
propose_decision
get_decision
execute_action
```

The service does not reimplement policy, persistence, Decision validation, or Action execution.

For example:

```text
ActionIntent
    +
ExecutionContext  <-- trusted host only
    |
    v
CEPIOApplicationService
    |
    v
ActionRequest     <-- runtime/internal form
    |
    v
existing policy + preconditions + audit + handler
```

## Contract invariants

Application Contract v0.1 establishes these invariants:

1. **Protocol neutrality** — contract models contain no HTTP, MCP, SDK, Fabric, Foundry, Cognite, OSDU, or provider-specific semantics.
2. **Identity injection** — caller payloads cannot select actor identity or roles.
3. **Runtime authority** — the application layer delegates Decision and Action authorization to existing CEPIO policy/runtime behavior.
4. **Causal continuity** — Decision IDs, correlation IDs, workflow IDs, idempotency keys, policy results, and audit records remain runtime-governed.
5. **Evidence by reference** — the contract references governed CEPIO evidence and assessments rather than duplicating source payloads or ontology concepts.
6. **One semantic implementation** — REST, MCP, SDK and events should converge on the same application service rather than duplicating business/industrial logic.
7. **Provider portability** — source bindings may change without changing the application contract consumed by Skills and clients.

## Relationship to the public API

The existing `/api/v1` REST API remains supported and versioned independently.

The direction from v0.1 onward is:

```text
CEPIO semantic/runtime contracts
             |
CEPIO Application Contract
             |
  +----------+----------+----------+
  |          |          |          |
 REST       MCP        SDK       Events
```

REST therefore remains essential, but it is a protocol projection rather than the definition of CEPIO itself.

## Relationship to Industry IQ

Industry IQ packs remain responsible for registering domain-specific Functions, Decisions, Actions and eventually executable Skills.

The application contract provides the stable envelope through which those capabilities can be consumed. A maintenance-deferral Skill and a drilling-NPT Skill should use the same `SkillInvocation` / `SkillEvaluation` shape even though their industrial reasoning differs.

## Next increments

### v0.2 — Skill execution binding

- bind registered executable Skills to `SkillInvocation` / `SkillEvaluation`;
- require READY preflight before dispatch;
- preserve evidence and assessment lineage;
- add deterministic Skill-contract conformance tests.

### v0.3 — Context assembly

- assemble `ContextEnvelope` through source-neutral binding contracts;
- prove equivalent context from synthetic and Fabric providers;
- add temporal and provenance selection rules.

### v0.4 — protocol convergence

- map REST Skill endpoints onto the application service;
- map MCP Skill tools onto the same service;
- expose equivalent Python SDK methods;
- add cross-protocol conformance tests proving equivalent semantic results.
