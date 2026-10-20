# CEPIO Foundry Agent + MCP Binding

CEPIO exposes a governed Model Context Protocol (MCP) surface for Microsoft Foundry, Copilot and generic MCP clients while preserving CEPIO as the industrial operating abstraction and authorization boundary.

## Canonical hosted surface

A deployed CEPIO host exposes three protocol surfaces over the same governed runtime:

```text
https://<cepio-host>/api/v1          REST Application Contract
https://<cepio-host>/management/v1   Management Contract (read-only remote projection)
https://<cepio-host>/mcp             MCP Streamable HTTP agent surface
```

The MCP endpoint is not a second industrial runtime. It is a protocol projection over the same CEPIO policy, Skills, Decisions, Functions and Action Runtime used by REST/SDK callers.

## Architectural rule

```text
Foundry / Copilot / MCP client
        |
        | authenticated Streamable HTTP
        v
CEPIO MCP Gateway (/mcp)
        |
        | verified ActorContext
        v
CEPIO Policy
        |
        +-- typed ObjectQuery
        +-- temporal state
        +-- provenance
        +-- deterministic functions
        +-- Skill evaluation
        +-- recommendations
        +-- governed actions
        |
        v
CEPIO Runtime
        |
        +-- Fabric / Fabric IQ binding
        +-- reference repositories
        +-- future SAP / PI / OSDU / P6 adapters
```

Foundry authentication does not replace CEPIO authorization. A valid Entra identity proves who is calling; CEPIO policy still decides what that principal can read, calculate, recommend, evaluate or execute.

An agent must never receive direct Fabric, SQL, repository, SAP, PI, P6 or other adapter handles as CEPIO tools.

## MCP tools

The MCP server publishes exactly eight governed tools:

| Tool | Purpose | Side effect |
| --- | --- | --- |
| `cepio_get_object` | Read one CEPIO object | none |
| `cepio_query_objects` | Run typed CEPIO ObjectQuery | none |
| `cepio_get_state_at` | Read valid-time / transaction-time state | none |
| `cepio_explain_property` | Explain property provenance | none |
| `cepio_call_function` | Run a policy-authorized CEPIO function | deterministic CEPIO function only |
| `cepio_evaluate_skill` | Evaluate an admitted executable CEPIO Skill | may persist a governed Decision according to the Skill contract |
| `cepio_recommend_action` | Evaluate recommendation/execute policy | none |
| `cepio_execute_action` | Execute a governed CEPIO action | possible enterprise-state change |

`cepio_evaluate_skill` uses the same `SkillInvocation` / `SkillEvaluation` Application Contract as REST and SDK clients.

`cepio_recommend_action` and `cepio_execute_action` are deliberately separate tools. A role such as `ai_agent_recommender` can receive a `recommend_only` policy decision without gaining execution permission.

## Identity contract

MCP tool arguments never contain `actor_id`, `actor_roles`, bearer tokens or other authority assertions.

The production hosted path reuses CEPIO's existing REST authentication configuration and `EntraTokenValidator`:

```text
Authorization: Bearer <Entra token>
          |
          v
CEPIO EntraTokenValidator
  issuer / audience / JWKS
          |
          +-- oid/sub -> actor subject
          +-- tid     -> tenant
          +-- roles   -> CEPIO application roles
          +-- groups  -> CEPIO_GROUP_ROLE_MAP
          |
          v
request-scoped ContextVarActorProvider
          |
          v
MCP tools
```

If the authenticated principal has no CEPIO role, the MCP request fails closed before protocol dispatch.

The transport-neutral `EntraClaimsMapper` remains available for hosting integrations that receive already-verified Entra claims from an upstream identity layer. Both paths terminate in the same MCP `ActorContext` contract.

### Foundry authentication modes

The CEPIO actor model supports Foundry remote-tool identity patterns including:

- `agentic-identity` — recommended for a published agent requiring its own least-privilege identity;
- `project-managed-identity` — shared project identity for controlled service-to-service scenarios;
- `oauth2` — per-user identity passthrough when CEPIO must preserve end-user authorization context;
- `user-entra-token` — supported by the actor model for Microsoft Entra user-token flows where the downstream service requires it.

For industrial write actions, use explicit CEPIO roles and keep Foundry tool approval enabled as defense in depth.

## Foundry registration contract

The repository includes:

`deployments/foundry/cepio-mcp-toolbox.yaml`

This is a CEPIO deployment contract rather than a Microsoft-importable file format. It captures the intended Foundry configuration independently from preview API/schema changes.

Recommended remote MCP connection:

```text
server_url: https://<cepio-host>/mcp
server_label: cepio
authentication: agentic-identity
audience: api://<cepio-api-app-registration>
```

The hosted MCP surface intentionally uses the same CEPIO Entra audience as the REST API so identity policy does not drift by protocol.

Equivalent Azure Developer CLI shape:

```bash
azd ai connection create cepio-mcp \
  --kind remote-tool \
  --target https://<cepio-host>/mcp \
  --auth-type agentic-identity \
  --audience "api://<cepio-api-app-registration>"
```

Foundry approval policy should keep execution gated:

```json
{
  "always": ["cepio_execute_action"]
}
```

The read/query/explain/evaluate/recommend tools can normally be configured without Foundry approval because CEPIO still performs authorization on every call. A customer can require additional approval for any tool.

## Hosting and Streamable HTTP

CEPIO Core keeps the MCP SDK optional:

```bash
pip install -e '.[mcp]'
```

The production CEPIO container installs the MCP runtime dependency because `cepio.host_api` exposes `/mcp` alongside REST and Management.

The hosted composition uses the official MCP Python SDK `streamable_http_app()` with:

```text
path             /mcp
stateless_http   true
json_response    true
authentication   CEPIO bearer-token validation
session manager  owned by outer CEPIO application lifespan
```

Mounted MCP sub-applications do not start their own lifespan automatically. CEPIO therefore explicitly enters `mcp.session_manager.run()` in the outer hosted application lifespan before accepting MCP traffic.

DNS-rebinding protection remains enabled. Azure App Service `WEBSITE_HOSTNAME` is allowlisted automatically. Other custom hostnames can be supplied through:

```text
CEPIO_MCP_ALLOWED_HOSTS=host1.example.com,host1.example.com:*
```

Browser Origins are denied unless explicitly supplied through:

```text
CEPIO_MCP_ALLOWED_ORIGINS=https://app.example.com
```

Foundry, Copilot and normal server-side MCP clients do not normally send browser Origin headers.

## Local/development server

A standalone development example remains available at:

`examples/foundry_mcp_server.py`

It uses a fixed development actor only for local protocol exercise. Do not deploy that fixed-actor pattern to a multi-user endpoint.

## Policy behavior

### Reads

`cepio_get_object`, `cepio_query_objects`, `cepio_get_state_at`, and `cepio_explain_property` use CEPIO read policy and property filtering.

Agent-facing object-set queries require an explicit `object_type`. CEPIO checks that requested type before running the query. This prevents broad pagination/count behavior from becoming an information side channel for hidden object classes.

### Functions

Functions are explicitly allowlisted per CEPIO role using the existing policy document:

```yaml
ai_agent_recommender:
  functions:
    - calculateProductionLoss
    - calculateAssetRisk
    - calculateMarginImpact
```

A function that is not explicitly allowed is denied.

### Skills

`cepio_evaluate_skill` delegates to the same `CEPIOApplicationService` used by REST and SDK protocol projections. READY preflight, actor-scoped reads, function authorization, evidence requirements and Decision persistence therefore remain protocol-neutral.

A Skill may produce a recommendation or governed Decision. It does not gain implicit permission to execute the associated Action.

### Recommendations

`cepio_recommend_action` calls the same CEPIO action policy evaluator used by runtime execution but never invokes the action handler.

Example response semantics:

```text
allow             -> recommendation permitted; actor could execute
recommend_only    -> recommendation permitted; actor cannot execute
approval_required -> recommendation permitted; human approval role required
deny              -> recommendation not permitted
```

### Execution

`cepio_execute_action` always constructs the `ActionRequest` from authenticated actor context and calls the normal CEPIO runtime. Existing policy, preconditions, idempotency, audit, compensation metadata and human-approval semantics remain in force.

Foundry approval cannot override a CEPIO deny.

## Tool-schema generation

The MCP server is built with the official MCP Python SDK. Tool JSON Schemas are generated from typed Python/Pydantic contracts, including `ObjectQuery` and `SkillInvocation`.

Actor identity is intentionally absent from those schemas. This prevents a model from self-asserting identity or privilege.

## Qualification

CEPIO CI uses the official MCP SDK to perform real MCP discovery/invocation in-process and separately qualifies the hosted Streamable HTTP boundary.

Tests verify:

- the exact eight-tool surface;
- generated tool schemas;
- actor fields are absent from tool arguments;
- policy-filtered object reads;
- governed object queries;
- explicit function authorization;
- Skill protocol convergence;
- Entra-claim-to-CEPIO-role mapping;
- request-scoped hosted actor binding;
- mounted MCP session-manager lifecycle;
- anonymous hosted MCP access fails closed;
- recommend-only agent behavior;
- separate human-role execution behavior;
- REST OpenAPI remains a separate contract and does not absorb `/mcp`.

Azure deployment additionally verifies that anonymous `POST /mcp` returns HTTP 401.

## Security invariants

1. No MCP tool accepts caller-supplied CEPIO roles.
2. No source adapter/repository is an MCP tool.
3. Every object/property read passes CEPIO policy.
4. Function calls are explicitly allowlisted by CEPIO role.
5. Skill evaluation does not grant Action authority.
6. Recommendation does not execute.
7. Execution always uses `CEPIORuntime.execute_action`.
8. Foundry approval is additive; it cannot bypass CEPIO policy.
9. Unmapped/unauthenticated identities fail closed.
10. REST and MCP reuse the same CEPIO authentication configuration and runtime policy.
11. CEPIO canonical semantics remain independent of Foundry and the MCP SDK.

## Microsoft references

- Foundry Agent Service overview and tool/toolbox model: https://learn.microsoft.com/azure/foundry/agents/overview
- MCP authentication: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
- Build/register custom MCP server: https://learn.microsoft.com/azure/foundry/mcp/build-your-own-mcp-server
- Azure Functions MCP + Foundry: https://learn.microsoft.com/azure/azure-functions/functions-mcp-foundry-tools
