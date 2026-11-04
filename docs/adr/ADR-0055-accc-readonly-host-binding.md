# ADR-0055: Request-scoped read-only ACCC admission

Status: Architectural direction approved by Faiz on 2026-11-03; implementation/security review and merge remain pending. No production activation.

## Context

The offline ACCC prototype accepts trusted admission facts, which are not a
client-facing authorization boundary. An agent-facing adapter needs concrete host
authentication, policy, Skill preflight and versioned source checks.

## Decision

Bind existing CEPIO authentication and runtime policy per invocation. Expose only a
strict CompositionRequest through the Microsoft FunctionTool adapter. Host-owned
profiles pin exact qualified contracts, compatible sets and source records. Reuse
the existing EvidenceBinding contract, with a narrow adapter payload convention.
Block unsupported policy requirements, Actions, Decision-producing Skills, unknown
compatibility, source scope mismatch and unresolved evidence.

## Consequences

No new identity provider, generic agent runtime, evidence store or Skill registry.
No route, authentication setting, permission, deployment or Action execution changes.
Hosts retain responsibility for qualified profiles, truthful source adapters,
request-local credentials and policy-version governance. Offline signature tests
do not attest a live Entra or industrial source integration. A minimal SDK Harness factory disables generic tools and retains approval handling.
Its loop is tested using a scripted offline client, not a live model.

See [implementation and reproduction contract](../architecture/accc-harness-readonly-spike.md).

## Default agent runtime — founder decision, 2026-11-03

Microsoft Agent Framework Harness is the default generic agent execution runtime
for new CEPIO agent experiences. The approved ACCC entry point is
`create_readonly_harness(client, request_scoped_host)`. Hosts supply the authorized
model client; selecting this default does not select or fund a model provider.

CEPIO retains capability/Skill qualification, evidence checks, tenant/actor policy,
industrial Decisions, governed Actions and outcome assurance. Harness approval never
overrides a CEPIO denial. The current default integration remains read-only.

Keep Microsoft-specific code in the integration adapter. CEPIO Core contracts remain
provider-neutral, and the Microsoft package remains an optional dependency for Core-only
consumers. Alternative host runtimes are explicit integrations rather than the default.
Do not silently fall back to another runtime if the chosen Harness is unavailable;
report the missing dependency/configuration instead.

This establishes the architecture and documented integration default. It does not
switch an existing deployed application, register a route, provision Azure resources,
expand permissions, execute industrial Actions or authorize paid inference. Existing
applications require their own governed adoption changes. Production activation and
live industrial qualification remain separate gates.
