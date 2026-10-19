# API, SDK and MCP

## Why CEPIO needs multiple interfaces

CEPIO distinguishes its **application contract** from the protocols used to access it.

The application contract is the stable semantic and behavioral promise. REST, SDKs, MCP tools, events and future interfaces are protocol projections over that contract.

```text
                    CEPIO Application Contract
                              |
          +-------------------+-------------------+
          |                   |                   |
        REST              Python SDK         MCP Gateway
          |                   |                   |
   Web / services       Python apps          AI agents
                       notebooks/data        Foundry/Copilot
```

Current envelope specification: [`docs/application-contract-v0.2.md`](../application-contract-v0.2.md). Protocol convergence is specified in [`docs/protocol-convergence-v0.3.md`](../protocol-convergence-v0.3.md).

## Contract vs API

A CEPIO **contract** defines what a capability means, what it requires, what it returns, and the invariants CEPIO guarantees when it is used.

An **API** defines one transport surface for calling those capabilities. OpenAPI therefore remains an important public compatibility contract for REST clients, but REST is not the definition of CEPIO itself.

The layering is:

```text
semantic/runtime contracts
          |
application contract
          |
 REST / MCP / SDK / Events
```

An SDK or MCP tool must not invent new CEPIO semantics. The same rule applies to REST endpoints.

## Application Contract v0.2 execution kernel

v0.1 introduced protocol-neutral envelopes for industrial context, evidence references, Skill invocation/evaluation, Decision proposals, Action intents and trusted execution context.

v0.2 makes the Skill envelope executable through `CEPIOApplicationService.evaluate_skill`:

```text
SkillInvocation + trusted ExecutionContext
                |
                v
        actor-aware preflight
                |
            READY only
                |
                v
       executable Skill binding
                |
                v
       restricted governed host
                |
        +-------+-------+
        |               |
actor-scoped reads   authorized Functions
        |               |
        +-------+-------+
                |
                v
       SkillExecutionOutput
                |
         optional DecisionProposal
                |
                v
          SkillEvaluation
```

`SkillExecutorRegistry` binds stable Skill identity to executable procedure code, while `SkillRegistry` remains authoritative for admission. Duplicate executable bindings fail closed.

Executable procedures receive `SkillExecutionHost`, not raw runtime access. That host exposes actor-scoped reads and policy-authorized deterministic Functions only. A procedure can propose a Decision, but the application service persists it with trusted host identity.

The first executable reference is `cepio.skill.maintenance.assess-maintenance-deferral`. It interprets already-governed Risk evidence through `evaluateMaintenanceDeferralRisk`, may persist a maintenance-deferral Decision, and never executes `DeferWorkOrder` itself.

## Protocol convergence v0.3

v0.3 projects the same executable Skill contract through REST, SDK and MCP without changing the envelope schema. `SkillInvocation` / `SkillEvaluation` therefore remain contract version `0.2.0`.

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
                  SkillEvaluation
```

The shipped composition root is `cepio.application_runtime.build_application_service(runtime)`. Protocol adapters use that builder instead of registering executable Skills independently.

Cross-protocol conformance proves the same synthetic invocation through direct application-service invocation, raw REST, Python SDK over REST, and actual MCP protocol. Generated Decision IDs/timestamps may differ; material Skill, evidence, output, recommendation, Decision and actor-authority semantics must match.

## Public API v1 — implemented REST boundary

CEPIO exposes a versioned public REST contract under `/api/v1` through `cepio.public_api:app`. Existing unversioned routes remain temporarily callable for compatibility, but they are deliberately excluded from the public OpenAPI document.

The v1 surface includes:

```text
/api/v1/health
/api/v1/objects
/api/v1/objects/{object_id}
/api/v1/query/objects
/api/v1/relationships
/api/v1/objects/{object_id}/neighbors
/api/v1/events
/api/v1/objects/{object_id}/events
/api/v1/skills/evaluate
/api/v1/functions/{name}
/api/v1/actions
/api/v1/decisions
/api/v1/decisions/{decision_id}
/api/v1/audit
/api/v1/graph/*
```

`POST /api/v1/skills/evaluate` has operation ID `evaluateSkill`, accepts `SkillInvocation`, injects trusted actor context from the authenticated REST host, and returns `SkillEvaluation`.

`state`, `provenance`, and `schema` are intentionally not declared as independent v1 resources yet. They should join the public REST surface only when their runtime semantics are stable enough for independent clients.

`openapi/cepio-v1.yaml` is the accepted route/method/operation-ID baseline, and CI checks the generated public OpenAPI document against it. See `docs/api-versioning.md`.

## Security inheritance

API v1 reuses the same secured CEPIO endpoint functions as the compatibility routes. It therefore inherits the existing REST security boundary rather than duplicating it:

- authenticated actor context;
- object-type and property read policy;
- graph-role restrictions;
- function authorization;
- governed action execution;
- audit controls.

Caller-visible `SkillInvocation`, `DecisionProposal` and `ActionIntent` payloads do not contain caller-selected identity or roles. Protocol adapters inject trusted execution context separately.

For executable Skills, the same actor context is re-used for READY preflight, actor-scoped object reads, Function authorization and any resulting Decision persistence.

## Object API

Responsibilities:

- retrieve object by stable CEPIO ID;
- read canonical type and properties;
- obtain object version;
- apply authorized updates;
- resolve aliases only when unambiguous.

## Relationship and query APIs

Relationship operations expose governed traversal. The typed query API provides backend-neutral object-set semantics. See [Query Model](07-Query-Model.md).

## State and provenance

CEPIO already supports temporal state and provenance in the runtime/MCP surfaces. Dedicated public REST resources remain a future contract decision rather than being invented prematurely.

## Function and action APIs

Functions and actions are separate API surfaces because they carry different risk semantics. A caller may have permission to invoke a calculation while lacking permission to execute the corresponding action.

The application contract adds `ActionIntent` as the caller-visible protocol-neutral request. Runtime `ActionRequest` remains the internal governed execution form carrying host-injected identity and roles.

Skill execution does not collapse this distinction. A Skill may return a recommendation or Decision that names an Action while direct Action execution remains a separate governed operation.

## Python and TypeScript SDKs

The Python SDK is the natural access path for data engineering, AI/ML workflows, notebooks, backend services, automation and ontology tooling.

The Python client now exposes:

```python
client.evaluate_skill(invocation) -> SkillEvaluation
```

The TypeScript client now exposes:

```ts
client.evaluateSkill(invocation): Promise<SkillEvaluation>
```

Both methods project the accepted REST `evaluateSkill` operation. Neither client contains Skill procedure logic or caller-selected authority semantics.

## MCP

CEPIO now exposes eight governed MCP tools for Microsoft Foundry agents:

```text
cepio_get_object
cepio_query_objects
cepio_get_state_at
cepio_explain_property
cepio_call_function
cepio_evaluate_skill
cepio_recommend_action
cepio_execute_action
```

`cepio_evaluate_skill` accepts the same `SkillInvocation` contract as REST/SDK and delegates through the same shipped application service.

Identity and roles are injected from the authenticated hosting context. They are **not model-callable arguments**.

## Recommendation vs execution

```text
Reasoning permission
      |
      v
Recommend action
      |
      +-- no execution permission -> stop / human approval
      |
      +-- execution allowed -> action policy + preconditions + audit
```

An agent can therefore be broad in reasoning context while remaining constrained in operational authority.

Protocol convergence preserves this explicitly for maintenance deferral: the AI recommender can evaluate the Skill and propose the governed Decision through REST, SDK or MCP, but cannot use any of those surfaces to transition the WorkOrder through Skill execution.

## Remaining API production hardening

The versioned REST contract is established, but API v1 is not yet production-GA. Remaining work includes:

- deeper schema-level OpenAPI compatibility checks;
- generic context assembly behind the application service;
- gradual routing of Decision and ActionIntent operations through the protocol-neutral application service without changing accepted v1 behavior;
- event-driven Skill invocation once trigger semantics are qualified;
- cross-domain protocol qualification with a second executable Skill;
- live Foundry and Copilot consumption proof using `cepio_evaluate_skill`.
