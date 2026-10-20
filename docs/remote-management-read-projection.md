# Remote Management Read Projection v0.1

## Purpose

Industry IQ Studio needs to observe a deployed CEPIO runtime without binding to runtime internals or weakening the local Management Contract boundary.

CEPIO therefore provides an additive **authenticated, read-only** projection of the existing Management Contract under `/management/v1/*` when the hosted API composition (`cepio.host_api:app`) is used.

The standalone `cepio-management` process remains loopback-only on `127.0.0.1:8100`.

## Authorization

Every remote management request uses the existing CEPIO authentication stack and requires one of:

- `cepio_management_reader` — least-privilege read-only management role;
- `cepio_admin` — existing administrative role, which also retains read access.

In production, `CEPIO_AUTH_MODE=entra` validates the bearer token against the configured Entra issuer, audience and JWKS endpoint. The remote projection does not add another token format, shared secret or browser-facing credential mechanism.

## Surface

The remote projection exposes only GET operations:

```text
GET /management/v1/health
GET /management/v1/status
GET /management/v1/capabilities
GET /management/v1/skills
GET /management/v1/industry-iq
GET /management/v1/bindings
GET /management/v1/profiles
```

These routes return the same sanitized Management Contract descriptors used by the loopback API.

## Deliberate exclusions

This change does **not** introduce:

- install, configure, restart or mutation commands;
- provider credentials or connection strings;
- raw environment variables;
- raw customer/source payloads;
- customer data;
- policy mutation;
- approval or promotion actions;
- credential management;
- a second management data model.

Remote management mutation remains deferred until CEPIO has a typed command contract, deployment authority, immutable audit, change planning, reconciliation and rollback semantics.

## Hosted composition

The production container starts:

```text
uvicorn cepio.host_api:app --host 0.0.0.0 --port $PORT
```

`host_api` composes two separate contracts in one process:

```text
/api/v1/*          Application Contract
/management/v1/*   authenticated Management read projection
```

The Application Contract remains unchanged. The standalone local management process remains unchanged.

## Industry IQ Studio

Studio should call the remote management projection from its server-side BFF. Browser code must not store CEPIO bearer tokens or call the CEPIO management endpoint directly.

The intended production direction is Entra-authenticated Studio plus a server-side identity/token exchange or managed-identity path. The first DEV integration may use a server-side token only as a temporary development bridge; such a token must never be committed to source control or exposed through `NEXT_PUBLIC_*` variables.
