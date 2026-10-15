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

An SDK packages those operations into language-native developer ergonomics.

Example conceptual REST operation:

```http
GET /v1/objects/PU-204A
```

Equivalent Python SDK style:

```python
pump = cepio.objects.get("PU-204A")
```

An SDK must not invent new CEPIO semantics. It is a client-side wrapper over the same product contract.

## Recommended v1 API resource families

The current codebase exposes API capabilities, but the long-term public contract should be organized around a stable `/v1` boundary:

```text
/v1/objects
/v1/relationships
/v1/query
/v1/functions
/v1/actions
/v1/state
/v1/provenance
/v1/schema
```

Potential later additions:

```text
/v1/events
/v1/decisions
/v1/spatial
/v1/audit
/v1/capabilities
```

## Object API

Responsibilities:

- retrieve object by stable CEPIO ID;
- read canonical type and properties;
- obtain object version;
- apply authorized updates;
- resolve aliases only when unambiguous.

## Relationship API

Responsibilities:

- list typed relationships;
- traverse direct and multi-hop relationships;
- support temporal relationship views;
- enforce domain/range semantics.

## Query API

The query API provides backend-neutral object-set semantics. See [Query Model](07-Query-Model.md).

## State and provenance API

Consumers should be able to ask:

- current state;
- valid-time state;
- transaction-time state;
- relationship state at time T;
- provenance for a property.

## Function and action APIs

Functions and actions are separate API surfaces because they carry different risk semantics.

A caller may have permission to invoke a calculation while lacking permission to execute the corresponding action.

## Python SDK

The Python SDK is the natural access path for:

- data engineering;
- AI/ML workflows;
- notebooks;
- backend services;
- automation;
- ontology tooling.

## TypeScript SDK

A TypeScript SDK is strategically important for:

- CEPIO web applications;
- visualization clients;
- React-based domain apps;
- browser/server TypeScript services.

It should be generated or kept contract-synchronized with OpenAPI rather than implemented as a separate semantic layer.

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

## MCP security principle

Identity and roles are injected from the authenticated hosting context. They are **not model-callable arguments**.

```text
Microsoft Foundry Agent
          |
          | authenticated identity
          v
     CEPIO MCP Gateway
          |
          +-- read policy
          +-- property filtering
          +-- function authorization
          +-- action policy
          +-- preconditions
          +-- audit
          |
          v
      CEPIO Runtime
```

## Recommendation vs execution

This separation is intentional:

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

## API v1 stabilization work

Before CEPIO is considered a mature developer platform, the API contract should be frozen around:

- OpenAPI as the machine-readable contract;
- consistent resource naming;
- versioning/deprecation policy;
- standard error model;
- pagination conventions;
- idempotency conventions;
- ETag/version concurrency behavior;
- auth scopes/roles;
- generated Python and TypeScript clients;
- compatibility tests.
