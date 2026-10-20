# ADR-0033 — Remote Management Read Projection v0.1

**Status:** Proposed  
**Date:** 2026-10-20  
**Classification:** PUBLIC architecture/security contract

## Context

Management Contract v0.1 deliberately exposes a loopback-only, read-only control plane. That boundary prevents an early management surface from becoming an unauthenticated remote administration API. Industry IQ Studio now needs to observe a deployed CEPIO runtime, but opening the loopback listener or coupling Studio directly to runtime internals would violate the control-plane architecture.

CEPIO already has production Entra bearer-token validation and sanitized Management Contract descriptors. The missing capability is an explicit hosted projection that reuses those contracts while retaining least privilege and excluding all management mutation.

## Decision

CEPIO will expose an additive authenticated **remote read projection** under `/management/v1/*` only in the hosted API composition.

The hosted process is `cepio.host_api:app` and composes:

```text
/api/v1/*          Application Contract
/management/v1/*   authenticated Management read projection
```

The standalone `cepio-management` process remains unchanged and loopback-only on `127.0.0.1:8100`.

### Authority

Remote reads require an authenticated actor with one of:

- `cepio_management_reader` — preferred least-privilege role;
- `cepio_admin` — existing administrator role, which retains read access.

Production authentication uses the existing Entra JWT validator and configured CEPIO API audience. No parallel shared-secret authentication mechanism is introduced.

### Read-only contract

The hosted projection exposes the existing seven GET descriptors only:

```text
GET /management/v1/health
GET /management/v1/status
GET /management/v1/capabilities
GET /management/v1/skills
GET /management/v1/industry-iq
GET /management/v1/bindings
GET /management/v1/profiles
```

No management POST, PUT, PATCH or DELETE route is added.

### Disclosure boundary

The remote projection uses the same sanitized Management Contract service as the loopback API. It does not expose:

- credentials, tokens or connection strings;
- raw `CEPIO_*` environment variables;
- Entra tenant configuration;
- provider secrets;
- raw source/customer payloads;
- customer-specific configuration bodies;
- management mutation commands.

### Deployment protection

The production container entry point changes from `cepio.public_api:app` to `cepio.host_api:app`. This is a hosting composition change, not an Application Contract change.

The Azure deployment smoke test must fail unless:

1. `/api/v1/health` remains healthy;
2. anonymous `/api/v1/objects` remains HTTP 401; and
3. anonymous `/management/v1/health` is HTTP 401.

This makes accidental unauthenticated control-plane exposure a deployment failure.

## Industry IQ Studio boundary

Studio consumes the remote projection through its server-side BFF. Browser code must not hold CEPIO management tokens or call the CEPIO management surface directly.

A short-lived server-side user token is acceptable only as a DEV bridge. The production target is a dedicated Studio workload identity / managed identity or governed on-behalf-of flow assigned `cepio_management_reader`.

## Rejected alternatives

### Open the existing management listener remotely

Rejected. It would erase the deliberate loopback security boundary of Management Contract v0.1.

### Expose management descriptors under `/api/v1`

Rejected. Application and Management contracts answer different questions and must remain separately evolvable.

### Let Studio inspect CEPIO runtime internals directly

Rejected. That would couple Studio to implementation details and duplicate control-plane semantics.

### Add management commands now

Rejected. Remote mutation still requires typed commands, management authority, immutable audit, change planning, reconciliation and rollback/compensation semantics.

## Consequences

Positive:

- Industry IQ Studio can observe Azure-hosted CEPIO through a durable contract;
- local management remains loopback-only;
- least-privilege read authority is explicit;
- `/api/v1` compatibility remains unchanged;
- deployment verifies the anonymous-access boundary.

Trade-offs:

- Entra must define and assign the `cepio_management_reader` app role for least-privilege production use;
- the initial Studio DEV bridge still needs an authenticated token;
- remote write administration remains intentionally unavailable.

## Validation

Qualification requires:

- all seven remote Management descriptors return successfully to an authorized reader;
- unauthorised authenticated actors receive HTTP 403;
- production requests without a bearer token receive HTTP 401;
- POST/PUT/DELETE management requests remain unavailable;
- `cepio_admin` retains read access;
- the standalone management API remains loopback-only;
- public Application Contract compatibility tests remain green;
- deployment profile validation requires the hosted composition;
- Azure deployment smoke testing verifies anonymous management HTTP 401;
- existing CI, quality, architecture, security, governance and CodeQL gates remain enforced.
