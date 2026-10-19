# CEPIO Management Control Plane

## Purpose

The CEPIO Management Contract describes **what a CEPIO runtime is running with**. It is separate from the Application Contract, which describes **what CEPIO can do with industrial context**.

```text
CONTROL PLANE                         EXECUTION PLANE
Management Contract                  Application Contract
        |                                     |
Management API / future CLI          REST / MCP / SDK
        |                                     |
Industry IQ Studio                   Apps / agents / Copilot
        \___________________  __________________/
                            \/
                       CEPIO runtime
```

## Management Contract v0.1

The first version is deliberately read-only and protocol-neutral. Durable descriptors include:

- `RuntimeHealth`
- `RuntimeDescriptor`
- `CapabilityInventory`
- `SkillDescriptor`
- `IndustryIQPackDescriptor`
- `BindingDescriptor`
- `ProfileDescriptor`

The contract version is `0.1.0`.

## Local FastAPI projection

The first projection is a separate FastAPI application, not an extension of the public `/api/v1` operational API.

Supported endpoints:

```text
GET /management/v1/health
GET /management/v1/status
GET /management/v1/capabilities
GET /management/v1/skills
GET /management/v1/industry-iq
GET /management/v1/bindings
GET /management/v1/profiles
```

Run it locally with:

```bash
cepio-management
```

The supported launcher binds to `127.0.0.1:8100`. Set `CEPIO_MANAGEMENT_PORT` to change the port. The FastAPI projection also rejects non-loopback clients.

## Security and disclosure boundary

v0.1 does not expose:

- raw `CEPIO_*` environment variables;
- database paths or connection strings;
- Entra tenant/audience/JWKS values;
- private runtime dictionaries;
- credentials, tokens or secrets;
- customer data;
- mutation endpoints.

`RuntimeDescriptor.persistence_mode` reports only `memory`, `sqlite`, or `external` rather than a connection URL.

## Skills

The management plane receives its shipped Skill inventory from the same composition source used by the Application Contract runtime. A Skill descriptor reports stable identity, required Industry IQ packs, Decision/Action capability references, whether an executable host binding exists, and its declared authority posture.

This inventory is descriptive. It does not bypass actor-aware Skill preflight at invocation time.

## Industry IQ

`/management/v1/industry-iq` reports the runtime's installed Industry IQ pack IDs and versions. It does not install, upgrade or resolve packs.

## Bindings

Bindings are **explicit management facts**. A provider is not reported as configured merely because CEPIO contains integration code for it.

A `BindingDescriptor` records:

```text
binding_id
provider
capability
mode            read | write | read-write
status          ready | degraded | not-configured
authority
```

This is the initial management abstraction that Industry IQ Studio can later use for provider status without depending on Fabric-, OSDU-, Cognite-, SAP- or PI-specific implementation classes.

## Profiles

`/management/v1/profiles` reports active runtime profiles and versions only. It does not expose profile source files or customer-specific configuration bodies.

## What comes later

Remote management and mutation are intentionally deferred. Before adding management commands such as install, configure, restart or change policy, CEPIO must define:

1. management identity and Entra/RBAC semantics;
2. tenant and deployment authority;
3. a typed management-command contract;
4. validation and change planning;
5. immutable audit;
6. execution/reconciliation semantics;
7. rollback/compensation where applicable.

Industry IQ Studio should consume this Management Contract rather than bind directly to CEPIO runtime internals.
