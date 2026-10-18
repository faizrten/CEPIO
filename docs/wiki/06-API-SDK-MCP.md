# API, SDK and MCP

## Why CEPIO needs multiple interfaces

CEPIO now distinguishes its **application contract** from the protocols used to access it.

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

See [`docs/application-contract-v0.1.md`](../application-contract-v0.1.md).

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

An SDK or MCP tool must not invent new CEPIO semantics. The same rule now applies to REST endpoints.

## Application Contract v0.1

The first protocol-neutral application contract introduces stable envelopes for:

- industrial context and evidence references;
- Skill invocation and evaluation;
- Decision proposals;
- Action intents;
- trusted execution context.

`CEPIOApplicationService` is the thin facade that maps those requests onto existing runtime semantics. It injects trusted actor identity and delegates policy, persistence, Decision validation, Action execution and audit to the existing CEPIO runtime.

Existing REST/MCP surfaces are not migrated in this increment; v0.1 is additive. Subsequent increments will converge those interfaces onto the same service with cross-protocol conformance tests.

## Public API v1 — implemented REST boundary

CEPIO exposes a versioned public REST contract under `/api/v1` through `cepio.public_api:app`. Existing unversioned routes remain temporarily callable for compatibility, but they are deliberately excluded from the public OpenAPI document.

The initial v1 surface includes:

```text
/api/v1/health
/api/v1/objects
/api/v1/objects/{object_id}
/api/v1/query/objects
/api/v1/relationships
/api/v1/objects/{object_id}/neighbors
/api/v1/events
/api/v1/objects/{object_id}/events
/api/v1/functions/{name}
/api/v1/actions
/api/v1/decisions
/api/v1/decisions/{decision_id}
/api/v1/audit
/api/v1/graph/*
```

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

The application-contract direction strengthens this boundary: caller-visible `SkillInvocation`, `DecisionProposal` and `ActionIntent` payloads do not contain caller-selected identity or roles. Protocol adapters inject trusted execution context separately.

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

## Python and TypeScript SDKs

The Python SDK is the natural access path for data engineering, AI/ML workflows, notebooks, backend services, automation and ontology tooling.

A TypeScript SDK is strategically important for CEPIO web applications, visualization clients and React-based industrial applications. Both SDKs should converge on the CEPIO application contract and remain synchronized with supported protocol surfaces rather than becoming separate semantic layers.

## MCP

CEPIO currently exposes seven governed MCP tools for Microsoft Foundry agents:

```text
cepio_get_object
cepio_query_objects
cepio_get_state_at
cepio_explain_property
cepio_call_function
cepio_recommend_action
cepio_execute_action
```

Identity and roles are injected from the authenticated hosting context. They are **not model-callable arguments**.

Future Skill-oriented MCP tools should map onto the same `SkillInvocation` / `SkillEvaluation` application contract used by REST and SDK clients.

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

## Remaining API production hardening

The versioned REST contract is established, but API v1 is not yet production-GA. Remaining P0 hardening includes:

- standard public error envelope;
- ETag / `If-Match` concurrency semantics;
- HTTP idempotency conventions;
- repository query pushdown;
- cursor pagination;
- deeper schema-level OpenAPI compatibility checks;
- gradual routing of REST operations through the protocol-neutral application service without changing accepted v1 behavior.
