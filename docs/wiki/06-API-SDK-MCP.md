# API, SDK and MCP

## Why CEPIO needs multiple interfaces

The CEPIO **API** is the product contract. SDKs and MCP tools are convenient access layers over that contract.

```text
                      CEPIO API / Runtime Contract
                                |
            +-------------------+-------------------+
            |                   |                   |
          REST              Python SDK         MCP Gateway
            |                   |                   |
     Web / services       Python apps          AI agents
                         notebooks/data        Foundry/Copilot
```

## API vs SDK

An API defines *what operations are available and how they behave*.

An SDK packages those operations into language-native developer ergonomics. An SDK must not invent new CEPIO semantics; it is a client-side wrapper over the same product contract.

## Public API v1 — implemented contract boundary

CEPIO now exposes a versioned public REST contract under `/api/v1` through `cepio.public_api:app`. Existing unversioned routes remain temporarily callable for compatibility, but they are deliberately excluded from the public OpenAPI document.

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

`state`, `provenance`, and `schema` are intentionally not declared as independent v1 resources yet. They should join the public contract only when their runtime semantics are stable enough for independent clients.

`openapi/cepio-v1.yaml` is the accepted route/method/operation-ID baseline, and CI checks the generated public OpenAPI document against it. See `docs/api-versioning.md`.

## Security inheritance

API v1 reuses the same secured CEPIO endpoint functions as the compatibility routes. It therefore inherits the existing REST security boundary rather than duplicating it:

- authenticated actor context;
- object-type and property read policy;
- graph-role restrictions;
- function authorization;
- governed action execution;
- audit controls.

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

## Python and TypeScript SDKs

The Python SDK is the natural access path for data engineering, AI/ML workflows, notebooks, backend services, automation and ontology tooling.

A TypeScript SDK is strategically important for CEPIO web applications, visualization clients and React-based industrial applications. Both SDKs should remain synchronized with the public OpenAPI contract rather than becoming separate semantic layers.

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

The versioned public contract is now established, but API v1 is not yet production-GA. Remaining P0 hardening includes:

- standard public error envelope;
- ETag / `If-Match` concurrency semantics;
- HTTP idempotency conventions;
- repository query pushdown;
- cursor pagination;
- deeper schema-level OpenAPI compatibility checks.
