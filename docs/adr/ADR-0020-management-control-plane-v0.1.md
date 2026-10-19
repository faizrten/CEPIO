# ADR-0020 — CEPIO Management Control Plane v0.1

**Status:** Proposed

## Context

CEPIO now has a protocol-neutral Application Contract for operational use by applications and agents. Administrative/runtime introspection is a different concern: it describes what a CEPIO runtime is configured with rather than asking CEPIO to reason, decide, or act on industrial context.

Exposing management state directly through the public `/api/v1` runtime API would mix control-plane and execution-plane responsibilities, risk publishing private implementation details, and prematurely create remote-administration security commitments.

## Decision

Introduce a separate **Management Contract v0.1** and make a local read-only FastAPI application its first projection.

The management plane exposes durable descriptors for:

- runtime health and sanitized runtime configuration;
- capability inventory;
- shipped Skill contracts and authority posture;
- installed Industry IQ packs;
- explicitly configured binding descriptors;
- active customer/deployment profiles.

The management plane does **not** expose raw environment variables, persistence URLs, secrets, private runtime dictionaries, or inferred provider connectivity.

### Plane separation

```text
Industry IQ Studio / admin tooling
              |
      Management Contract
              |
       Management API
              |
          CEPIO runtime

Apps / agents / Copilot
              |
      Application Contract
              |
       REST / MCP / SDK
              |
          CEPIO runtime
```

### Local-only boundary

The supported v0.1 launcher binds to `127.0.0.1` and the FastAPI projection rejects non-loopback clients. Remote management is not a v0.1 product claim.

### Read-only boundary

All v0.1 management operations are GET-only. Runtime mutation, pack installation, binding changes, profile changes, restart, policy edits, and deployment operations are deliberately excluded.

A future management command model must introduce explicit identity, authorization, validation, audit and reconciliation rather than adding ad-hoc POST endpoints.

### Binding truthfulness

A binding is reported only when the host supplies a `BindingDescriptor`. The existence of adapter or integration code does not imply a configured or live binding.

## Consequences

- Industry IQ Studio can evolve against a stable management abstraction instead of runtime internals.
- Public runtime APIs remain focused on industrial application semantics.
- The local API can later be projected through CLI or a secured remote management protocol without changing the underlying management contract.
- Remote enterprise management will require a separate ADR covering Entra/RBAC, tenant boundaries, audit, and mutation semantics.
