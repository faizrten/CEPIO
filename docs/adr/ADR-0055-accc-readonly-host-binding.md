# ADR-0055: Request-scoped read-only ACCC admission

Status: Proposed — architecture review required; no production activation.

## Context

The offline ACCC prototype accepts trusted admission facts, which are not a
client-facing authorization boundary. An agent-facing adapter needs concrete host
authentication, policy, Skill preflight and versioned source checks.

## Decision proposed

Bind existing CEPIO authentication and runtime policy per invocation. Expose only a
strict CompositionRequest through an optional Microsoft FunctionTool. Host-owned
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
