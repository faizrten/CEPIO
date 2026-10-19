# ADR-0026 — Binding Contract v0.1

**Status:** Proposed

## Context

CEPIO already has provider-neutral platform-binding primitives and qualified Synthetic/Fabric evidence bindings. The Management Contract separately exposes `BindingDescriptor` values for control-plane inventory.

Without a canonical registration contract, runtime conformance and management inventory can drift: a provider implementation can advertise one mode/capability set while the management plane independently declares another. Repository support can also be confused with a binding that is actually configured in a runtime.

The CEPIO north star requires replaceable providers underneath stable Industry IQ. Binding semantics therefore need a durable contract that is independent of Microsoft Fabric, Cognite, OSDU, SAP or any future provider.

## Decision

Adopt **Binding Contract v0.1** as the canonical provider-neutral boundary.

The contract has three distinct layers:

1. `PlatformBindingManifest` — immutable implementation declaration: binding identity, provider, authoritative source system, mode and capabilities.
2. `BindingRegistration` — explicit host/runtime registration: manifest + industrial capability + current runtime status.
3. `BindingDescriptor` — Management Contract projection derived from the registration for Studio/operations consumption.

Repository/provider support alone MUST NOT create a runtime registration.

### Evidence bindings

Evidence bindings:

- declare `resolve-evidence`;
- may declare `versioned-identity`;
- cannot declare governed-write, verify or reconcile;
- derive management access mode `read`;
- derive authority `observation-only`;
- preserve source identity and provenance through `ExternalRecordReference`.

### Governed-action bindings

Governed-action bindings:

- declare governed-write, verify and reconcile;
- cannot declare resolve-evidence;
- derive management access mode `write`;
- derive authority `governed-action`;
- must execute external side effects only through CEPIO's existing governed Action Runtime.

### Runtime status

A registration reports exactly one of:

- `ready`;
- `degraded`;
- `not-configured`.

Status is runtime/configuration truth. It is not inferred from whether provider code exists in the repository.

## Compatibility

The existing `PlatformBindingManifest`, evidence/governed conformance helpers, Synthetic drilling NPT binding and Microsoft Fabric drilling NPT binding remain valid.

Management's published `CEPIOManagementService.__init__` and `build_management_service(...)` signatures remain unchanged. Direct `BindingDescriptor` input therefore remains supported exactly as before.

The canonical Binding Contract path is additive: `build_management_service_from_registrations(...)` projects `BindingRegistration` values into the existing Management descriptor contract and then delegates to the frozen builder. The legacy and canonical construction paths are intentionally separate rather than adding new parameters to an already-published interface.

No existing public `/api/v1` application contract, MCP surface, SDK surface, ontology or persisted customer semantic is changed.

## Portability proof

The existing drilling NPT qualification remains the first provider-replacement proof:

```text
SyntheticDrillingNPTBinding
           │
           ├── Binding Contract v0.1
           │
FabricDrillingNPTBinding
           │
           ▼
      same NPT Skill
           │
           ▼
semantically equivalent assessment
```

Provider/source provenance is intentionally different. Industry IQ interpretation is expected to remain equivalent.

## Security and data boundary

Binding registration is metadata only. Creating a registration does not read provider/customer data and does not dispatch external writes.

The contract does not expose credentials, connection strings, tokens, tenant identifiers, raw source payloads or customer mappings to Management.

Customer runtime data and customer-specific binding configuration remain tenant-local. No customer data is used to train or generalize CEPIO across customer boundaries.

## Consequences

Positive:

- one binding truth can be consumed by Runtime, Management and Industry IQ Studio;
- provider replacement becomes explicitly testable;
- supported-provider inventory is not confused with configured-runtime inventory;
- access mode and authority are derived from contract mode rather than duplicated strings;
- future Fabric/Cognite/OSDU/SAP bindings can conform to the same lifecycle;
- the existing Management construction contract remains source-compatible.

Trade-offs:

- v0.1 still allows legacy direct Management descriptors for compatibility;
- runtime registration persistence/discovery is not yet introduced;
- health checks remain provider-owned; `degraded` status is supplied by the host rather than actively probed by Core;
- read-write composite bindings are not modeled as one implementation in v0.1; evidence and governed-action responsibilities remain separate.

## Validation

Acceptance requires:

- contract tests for evidence and governed-action registration;
- management descriptors derived from registrations without semantic drift;
- published Management constructor/builder compatibility remaining unchanged;
- Synthetic and Fabric drilling bindings registering under the same contract;
- existing Synthetic/Fabric semantic parity qualification remaining green;
- full CEPIO CI, quality, compatibility, governance and CodeQL gates without threshold reduction.
