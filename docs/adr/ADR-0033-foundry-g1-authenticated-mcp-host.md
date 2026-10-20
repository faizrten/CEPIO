# ADR-0033 — Authenticated Foundry G1 MCP Host and Recommendation-Only Tool Profile

- **Status:** Accepted for G1 implementation
- **Date:** 2026-10-20
- **Decision scope:** Public Microsoft/Foundry integration and deployment boundary
- **Parent:** #246 / #248

## Context

CEPIO already exposes governed industrial capabilities through MCP and already separates model reasoning from CEPIO evidence, policy, Decision and Action semantics. The Microsoft-native Reliability Agent Lighthouse requires a real Microsoft Foundry-hosted agent to use that surface without giving the model direct access to CEPIO repositories, Fabric SQL, SAP write APIs or source adapters.

The existing MCP reference server was suitable for protocol testing but did not provide a production-shaped authenticated remote host. G1 also has a deliberately narrower authority boundary than later lighthouse gates: the agent may investigate and produce a governed Decision, but it must not execute an external Action.

`pyproject.toml` is a protected governance path because this increment adds an executable MCP-host entrypoint and an optional live Foundry dependency. The change therefore requires explicit architectural rationale, security invariants and qualification evidence rather than treating the host as ordinary integration plumbing.

## Decision

### 1. Microsoft hosts the agent; CEPIO remains the industrial authority boundary

Microsoft Foundry owns model execution and the generic agent loop. CEPIO remains authoritative for industrial evidence, Skill admission, Decision persistence, policy/authority and Actions.

The agent receives only the CEPIO MCP surface. No MCP tool exposes CEPIO repositories, source adapters or source-system credentials.

### 2. Preserve the existing MCP builder contract

`build_mcp_server(runtime, actor_provider)` remains unchanged and continues to expose the existing full eight-tool governed surface.

A new additive `build_mcp_server_with_profile(...)` factory provides explicit tool-profile selection. This avoids a breaking public API change and satisfies the repository compatibility ratchet.

### 3. G1 uses a recommendation-only MCP profile

The G1 profile exposes:

- object reads and typed queries;
- temporal state;
- provenance explanation;
- governed deterministic functions;
- executable Skill evaluation;
- action recommendation evaluation.

It does **not** publish `cepio_execute_action`.

This is defense in depth, not the primary authorization mechanism. CEPIO policy remains authoritative even when the host narrows the visible tool set.

### 4. Remote MCP identity is derived only from verified Entra claims

The remote Streamable-HTTP host reuses CEPIO's existing `EntraTokenValidator` and `EntraClaimsMapper`.

Only explicitly configured Entra roles/groups map to CEPIO roles. Tool arguments cannot supply actor identity or roles. Missing credentials fail with `401`; an authenticated principal with no mapped CEPIO authority fails with `403`.

The verified actor is bound through `ContextVarActorProvider`, preserving the same actor-aware application/runtime boundary used by existing CEPIO integrations.

### 5. Network exposure is explicit and least-privilege by default

The host defaults to `127.0.0.1`, not `0.0.0.0`.

A deployment that requires external ingress must explicitly set `CEPIO_MCP_BIND_HOST`. MCP transport allowed-host/origin controls remain required, and production exposure remains behind TLS and Entra authentication.

### 6. Live Foundry qualification is protocol-evidence based

A G1 run passes only when the Foundry Responses API contains actual MCP protocol evidence showing:

- an observed `cepio_evaluate_skill` call;
- the required Skill identity when one is pinned;
- completed Skill evaluation;
- governed evidence references;
- a persisted CEPIO Decision identity;
- zero `cepio_execute_action` calls.

Model prose cannot self-certify that a Skill was evaluated or a Decision was created.

## Consequences

### Positive

- G1 can use a real Foundry-hosted agent without introducing a CEPIO agent framework.
- Agent identity and authority remain separated: Entra authenticates the principal; CEPIO maps and enforces industrial authority.
- The G1 execution surface is least-privilege while preserving the full MCP contract for later governed-action phases.
- Existing public MCP signatures remain backward compatible.
- Live qualification can distinguish model claims from actual CEPIO tool/Decision evidence.

### Costs / constraints

- A live G1 PASS still requires an externally configured Foundry project/agent and a remotely reachable CEPIO MCP deployment; repository CI cannot claim that environment result.
- Protected Reliability IQ remains outside the public repository. A separate composition seam is required so an externally assembled `CEPIOApplicationService` can supply protected Skill executors without creating a plugin framework.
- Deployment operators must configure explicit Entra role mapping, allowed hosts/origins and any non-loopback bind address.

## Security invariants

1. No MCP tool accepts caller-supplied CEPIO roles or actor identity.
2. No direct source-system or repository handle is exposed to the agent.
3. The authenticated host fails closed on missing/invalid credentials and unmapped authority.
4. Recommendation-only G1 does not expose external Action execution.
5. CEPIO policy remains authoritative regardless of Foundry tool approval or tool visibility.
6. Foundry-specific concepts remain in the Microsoft integration layer and do not enter CEPIO Core semantics.
7. The host does not weaken existing evidence, Decision, policy, Action or audit contracts.

## Validation

The implementation is qualified through repository-required gates and focused tests covering:

- backward-compatible full MCP discovery;
- recommendation-only tool discovery with execution absent;
- invalid profile rejection;
- Entra identity mapping and fail-closed missing/invalid/unmapped identities;
- host configuration parsing and transport restrictions;
- safe loopback bind default;
- protocol-level G1 PASS/FAIL evaluation;
- rejection of model prose without MCP evidence;
- rejection of any execution call during G1;
- API/client compatibility, architecture, security, CodeQL and coverage ratchets.

A repository merge means the live qualification path is available and repository-qualified. It does **not** mean that a real Microsoft Foundry environment has already passed G1.

## Alternatives rejected

### Change the existing MCP builder signature

Rejected. The existing public MCP builder is already a compatibility surface. G1 is additive and does not justify breaking it.

### Depend only on CEPIO policy while exposing `cepio_execute_action`

Rejected for G1. Policy is still authoritative, but the lighthouse's first gate explicitly has no external Action scope. Removing the tool from discovery provides appropriate least-privilege defense in depth.

### Build a CEPIO agent runtime

Rejected. It conflicts with the North Star: Microsoft owns agent execution; CEPIO owns industrial agency.

### Publish protected Reliability logic in the public repository

Rejected. Public CEPIO should expose interoperable contracts and integration surfaces; differentiated Industry IQ and protected evaluation content remain in CEPIO-Labs.
