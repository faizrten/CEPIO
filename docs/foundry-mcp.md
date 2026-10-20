# CEPIO Foundry Agent + MCP Binding

CEPIO v0.4 exposes a governed Model Context Protocol (MCP) surface for Microsoft Foundry agents while preserving CEPIO as the industrial operating abstraction and authorization boundary.

## Architectural rule

```text
Foundry Agent / Toolbox
        |
        | authenticated remote MCP
        v
CEPIO MCP Gateway
        |
        | authenticated ActorContext
        v
CEPIO Policy
        |
        +-- typed ObjectQuery
        +-- temporal state
        +-- provenance
        +-- deterministic functions
        +-- executable Skills
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

Foundry authentication does not replace CEPIO authorization. A valid Foundry or Entra identity proves who is calling; CEPIO policy still decides what that principal can read, calculate, recommend, or execute.

An agent must never receive direct Fabric, SQL, repository, SAP, PI, P6, or other adapter handles as CEPIO tools.

## MCP tool profiles

The backward-compatible `build_mcp_server(runtime, actor_provider)` surface publishes the **full eight-tool** CEPIO MCP profile:

| Tool | Purpose | Side effect |
| --- | --- | --- |
| `cepio_get_object` | Read one CEPIO object | none |
| `cepio_query_objects` | Run typed CEPIO ObjectQuery | none |
| `cepio_get_state_at` | Read valid-time / transaction-time state | none |
| `cepio_explain_property` | Explain property provenance | none |
| `cepio_call_function` | Run a policy-authorized CEPIO function | deterministic CEPIO function only |
| `cepio_evaluate_skill` | Evaluate an admitted executable CEPIO Skill | may persist a governed Decision; no external Action |
| `cepio_recommend_action` | Evaluate recommendation/execute policy | none |
| `cepio_execute_action` | Execute a governed CEPIO action | possible enterprise-state change |

For recommendation-only agent scenarios, `build_mcp_server_with_profile(..., tool_profile="recommendation-only")` publishes the first seven tools and deliberately omits `cepio_execute_action`.

`cepio_recommend_action` and `cepio_execute_action` are deliberately separate tools. A role such as `ai_agent_recommender` can receive a `recommend_only` policy decision without gaining execution permission. Tool-profile restriction is defense in depth; CEPIO policy remains authoritative.

## Identity contract

MCP tool arguments never contain `actor_id` or `actor_roles`.

The production remote host validates the Microsoft Entra bearer token, then supplies verified claims to `EntraClaimsMapper`. The mapper converts explicitly configured Entra application roles and/or groups into CEPIO roles and builds an `ActorContext`:

```text
Microsoft Entra verified claims
  oid/sub -> CEPIO actor subject_id
  tid     -> tenant_id
  azp     -> client_id
  roles   -> deployment role_map -> CEPIO roles
  groups  -> group_role_map      -> CEPIO roles
```

If no CEPIO role is mapped, the request fails closed.

### Foundry authentication modes

The CEPIO actor model supports the current Foundry remote-tool identity patterns:

- `agentic-identity` — recommended for a published agent requiring its own least-privilege identity;
- `project-managed-identity` — shared project identity, useful for controlled service-to-service scenarios;
- `oauth2` — per-user identity passthrough when CEPIO must preserve end-user authorization context;
- `user-entra-token` — supported by the actor model for Microsoft Entra user-token flows where the downstream service requires it.

For industrial write actions, use explicit CEPIO roles and keep Foundry tool approval enabled as defense in depth.

## Foundry registration contract

The repository includes:

`deployments/foundry/cepio-mcp-toolbox.yaml`

This is a CEPIO deployment contract rather than a Microsoft-importable file format. It captures the intended Foundry configuration independently from preview API/schema changes.

Recommended remote MCP connection:

```text
server_url: https://<cepio-mcp-host>/mcp
server_label: cepio
authentication: agentic-identity
audience: api://<cepio-mcp-app-registration>
```

Equivalent current Azure Developer CLI shape:

```bash
azd ai connection create cepio-mcp \
  --kind remote-tool \
  --target https://<cepio-mcp-host>/mcp \
  --auth-type agentic-identity \
  --audience "api://<cepio-mcp-app-registration>"
```

For a full-profile deployment, Foundry approval policy should keep execution gated:

```json
{
  "always": ["cepio_execute_action"]
}
```

The read/query/explain/Skill/recommend tools can normally be configured without Foundry approval because CEPIO still performs authorization on every call. A customer can require additional approval for any tool.

## MCP Python SDK

Install the optional server dependency:

```bash
pip install -e '.[mcp]'
```

Build the backward-compatible full protocol server:

```python
from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import ContextVarActorProvider
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server

runtime = build_runtime()
actor_provider = ContextVarActorProvider()
mcp = build_mcp_server(runtime, actor_provider)
```

Build the narrower recommendation-only profile:

```python
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server_with_profile

mcp = build_mcp_server_with_profile(
    runtime,
    actor_provider,
    tool_profile="recommendation-only",
)
```

## Authenticated remote host

CEPIO includes a production-oriented Streamable-HTTP entrypoint:

```bash
cepio-foundry-mcp
```

It reuses CEPIO's Entra token validator, explicit role/group mapping, `ContextVarActorProvider`, and MCP transport host/origin restrictions. The host defaults to the `recommendation-only` tool profile and binds only to `127.0.0.1` unless the deployment explicitly sets `CEPIO_MCP_BIND_HOST`.

A container/App Service/AKS deployment that requires external listening can set:

```bash
export CEPIO_MCP_BIND_HOST='0.0.0.0'
```

External exposure must remain behind TLS and Entra authentication with explicit `CEPIO_MCP_ALLOWED_HOSTS` / `CEPIO_MCP_ALLOWED_ORIGINS` configuration. See [Foundry Agent Lighthouse — G1](foundry-agent-g1.md) for the live qualification runbook.

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

`cepio_evaluate_skill` uses the shared CEPIO application contract. Each invocation re-runs actor-aware Skill preflight, executes only through the restricted host, carries governed evidence forward, and may produce/persist a CEPIO Decision. Skill evaluation does not grant external Action authority.

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

`cepio_execute_action` always constructs the `ActionRequest` from authenticated actor context and calls the normal CEPIO runtime. Existing policy, preconditions, idempotency, audit, compensation metadata, and human-approval semantics remain in force.

Foundry approval cannot override a CEPIO deny.

## Tool-schema generation

The MCP server is built with the official MCP Python SDK. Tool JSON Schemas are generated from typed Python/Pydantic contracts, including `ObjectQuery` and `SkillInvocation`.

The actor identity is intentionally absent from those schemas. This prevents a model from self-asserting identity or privilege.

## Offline testing

The official MCP SDK supports in-process clients. CEPIO CI uses that mode to perform the real MCP discovery/invocation path without a network endpoint or Foundry service.

Tests verify:

- the backward-compatible eight-tool full surface;
- the seven-tool recommendation-only surface with execution omitted;
- generated tool schemas;
- actor fields are absent from tool arguments;
- policy-filtered object reads;
- governed object queries;
- explicit function authorization;
- executable Skill evaluation;
- Entra-claim-to-CEPIO-role mapping;
- recommend-only agent behavior;
- separate human-role execution behavior;
- existing CEPIO tests, SHACL validation, and refinery demo remain green.

## Security invariants

1. No MCP tool accepts caller-supplied CEPIO roles.
2. No source adapter/repository is an MCP tool.
3. Every object/property read passes CEPIO policy.
4. Function calls are explicitly allowlisted by CEPIO role.
5. Skill evaluation does not imply external Action authority.
6. Recommendation does not execute.
7. Execution always uses `CEPIORuntime.execute_action`.
8. Foundry approval is additive; it cannot bypass CEPIO policy.
9. Unmapped/unauthenticated identities fail closed.
10. CEPIO canonical semantics remain independent of Foundry and the MCP SDK.

## Microsoft references

- Foundry Agent Service overview and tool/toolbox model: https://learn.microsoft.com/azure/foundry/agents/overview
- MCP authentication: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
- Build/register custom MCP server: https://learn.microsoft.com/azure/foundry/mcp/build-your-own-mcp-server
- Azure Functions MCP + Foundry: https://learn.microsoft.com/azure/azure-functions/functions-mcp-foundry-tools
