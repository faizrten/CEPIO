# ADR-0034 — Hosted MCP Gateway v0.1

**Status:** Proposed  
**Date:** 2026-10-20  
**Classification:** PUBLIC architecture/security contract

## Context

CEPIO already implements a governed MCP tool surface and proves it through the official MCP Python SDK. The remaining gap is deployment: the Azure-hosted CEPIO process exposes the REST Application Contract and the Management read projection, but it does not yet expose a remote Streamable HTTP MCP endpoint.

That leaves an undesirable mismatch between CEPIO's implemented protocol convergence and its deployed product surface. Developers can call `/api/v1`, Industry IQ Studio can call `/management/v1`, but Foundry/Copilot/agent clients do not yet have a canonical remote `/mcp` endpoint.

## Decision

The hosted CEPIO process will expose three separate protocol surfaces over one governed runtime:

```text
/api/v1/*          Application Contract REST projection
/management/v1/*   authenticated Management read projection
/mcp               authenticated Streamable HTTP MCP projection
```

All three surfaces share the same CEPIO runtime, policy engine, Skill admission, Decision semantics and Action Runtime. MCP does not introduce a second authorization model or alternate industrial semantics.

## Authentication and actor binding

Hosted MCP reuses CEPIO's existing authentication configuration and `EntraTokenValidator`.

For every Streamable HTTP request:

1. the hosting adapter validates the bearer token using the configured CEPIO Entra audience, issuer and JWKS endpoint;
2. token roles plus configured group-to-role mappings become CEPIO roles;
3. the verified principal is converted to the MCP `ActorContext`;
4. the actor is bound to the request-scoped `ContextVarActorProvider`;
5. MCP tools obtain actor identity only from that provider.

No MCP tool accepts `actor_id`, `actor_roles`, access tokens or role assertions as model-callable arguments.

Actors with no CEPIO role fail closed before protocol dispatch.

Development header identity remains available only when `CEPIO_AUTH_MODE=dev` and the existing CEPIO environment guard allows development/test mode.

## Transport

The hosted endpoint uses the official MCP Python SDK Streamable HTTP application with:

- `stateless_http=True`;
- `json_response=True`;
- explicit MCP session-manager ownership by the outer FastAPI lifespan;
- explicit transport host/origin protection;
- the same `/mcp` path for Foundry, Copilot and generic MCP clients.

The MCP SDK remains an optional CEPIO package dependency. The production container explicitly installs the MCP extra/runtime dependency because `cepio.host_api` hosts the protocol surface. CEPIO Core semantics remain independent from the MCP SDK.

## Host and origin security

DNS-rebinding protection stays enabled.

Allowed hosts are resolved from:

1. `CEPIO_MCP_ALLOWED_HOSTS`, when explicitly configured; otherwise
2. local/test hosts plus Azure App Service `WEBSITE_HOSTNAME` when present.

Browser Origins are denied unless explicitly listed in `CEPIO_MCP_ALLOWED_ORIGINS`. Non-browser Foundry/Copilot/agent clients normally do not send an Origin header.

## Tool surface

Hosted MCP exposes the same eight governed tools already qualified in-process:

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

`cepio_evaluate_skill` is the MCP projection of the same Application Contract Skill evaluation used by REST and SDK clients.

`cepio_recommend_action` and `cepio_execute_action` remain separate so reasoning authority cannot silently become execution authority.

## Lifespan ownership

Mounted ASGI sub-application lifespans are not started automatically by Starlette/FastAPI. Therefore the outer CEPIO host explicitly enters `mcp.session_manager.run()` for the lifetime of the process.

This is a production invariant. A mounted MCP route without a running session manager is considered an invalid host composition.

## Deployment qualification

The Azure deployment must fail if any of the following are false:

- `/api/v1/health` reports healthy;
- anonymous `/api/v1/objects` returns HTTP 401;
- anonymous `/management/v1/health` returns HTTP 401;
- anonymous `/mcp` returns HTTP 401.

Authenticated protocol behavior is covered in CI through the official MCP SDK and hosted-transport tests. Live Foundry/Copilot consumption remains a separate ecosystem integration proof rather than a prerequisite for exposing the CEPIO endpoint.

## Rejected alternatives

### Separate MCP container/service immediately

Rejected for v0.1. It would duplicate runtime configuration and make identity/policy drift more likely before there is a scaling requirement that justifies another service boundary.

### Let Azure/Foundry authentication replace CEPIO policy

Rejected. Authentication proves who is calling; CEPIO remains authoritative for what the actor may read, calculate, recommend or execute.

### Reimplement MCP tools as REST wrappers

Rejected. Protocol convergence already delegates REST, SDK and MCP to shared CEPIO application/runtime contracts. A second implementation would create semantic drift.

### Make the MCP SDK a mandatory CEPIO Core dependency

Rejected. The protocol transport remains a hosting concern. Only the production host/container requires the MCP SDK.

## Consequences

Positive:

- CEPIO has one canonical deployed endpoint with REST, Management and MCP surfaces;
- Foundry/Copilot/generic MCP clients can consume CEPIO directly;
- identity and policy are shared with REST rather than duplicated;
- the eight-tool governed MCP contract becomes a real deployed product surface;
- Industry IQ Studio and agent clients remain separated by protocol purpose while sharing runtime truth.

Trade-offs:

- the hosted process now owns the MCP SDK and session-manager lifecycle;
- App Service/custom domains must keep MCP host allowlists correct;
- a future independent MCP scaling plane may require extracting this host composition behind the same contract.

## Validation

Qualification requires:

- development and Entra actor mapping fail closed without CEPIO roles;
- model-callable tool schemas continue to exclude actor identity/roles;
- authenticated HTTP requests are bound to `ContextVarActorProvider`;
- the mounted MCP session manager is running before request dispatch;
- the public REST OpenAPI contract remains unchanged and does not absorb `/mcp`;
- existing MCP protocol and protocol-convergence tests remain green;
- Docker/container qualification includes the MCP dependency;
- Azure deployment smoke testing verifies anonymous `/mcp` HTTP 401;
- existing CI, quality, compatibility, governance and CodeQL gates remain enforced.
