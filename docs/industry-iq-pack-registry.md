# Industry IQ Pack Registry v0.5

CEPIO v0.5 turns the v0.4 Industry IQ extension seam into a deterministic deployment contract.

The registry is intentionally not another ontology or module system. Canonical industrial semantics stay in CEPIO ontology modules, while source-system truth remains in authoritative external systems such as OSDU/ADME, Fabric, historians and EAM/ERP platforms. Industry IQ packs package executable domain intelligence that extends the governed runtime.

## Pack manifest

Each pack may publish an `IndustryIQPackManifest` with:

- `pack_id` and stable semantic `version`;
- `requires_core`, a CEPIO Core version constraint;
- `requires_packs`, transitive Industry IQ dependencies;
- declared functions, decisions and actions owned by the pack.

Legacy v0.4 packs that only expose `pack_id`, `version` and `install()` remain valid. Their manifest is synthesized, preserving compatibility while allowing gradual adoption of richer metadata.

## Resolution lifecycle

```text
available pack versions
        ↓
requested pack IDs / constraints
        ↓
Core-version compatibility
        ↓
transitive dependency resolution
        ↓
cycle detection
        ↓
capability collision validation
        ↓
immutable install order
        ↓
pack installation
        ↓
deployment manifest
```

Resolution is side-effect free. CEPIO does not call a pack's `install()` method until the complete composition has passed compatibility, dependency and collision checks.

## Fail-closed invariants

The registry rejects the composition when:

- no available version satisfies all constraints;
- a pack is incompatible with the current Core version;
- dependency requirements cannot be composed;
- dependencies contain a cycle;
- two selected packs claim the same function, decision or action;
- a pack attempts to replace a function, decision or action already owned by Core;
- the same pack is installed twice into one runtime.

The runtime's existing `industry_iq_packs` map remains the compact installed-capability view used by Skill preflight. The registry additionally records an `IndustryIQDeploymentManifest` after successful installation so hosts can expose exact pack composition without teaching the agent how deployment admission works.

## Skill boundary

Skill admission remains a host/runtime concern:

```text
Skill dependency
      ↓
required Industry IQ pack ID
      ↓
registry-resolved deployment
      ↓
Skill runtime preflight
      ↓
READY / BLOCKED
      ↓
READY-only dispatch
```

The pack registry does not weaken Skill preflight. A Skill still fails closed when a required pack is absent, and target-instance evidence remains an invocation-time concern.

## Current first-class pack

`cepio.iq.drilling.npt@0.1.0` now publishes an explicit manifest declaring:

- CEPIO Core compatibility `>=0.4.0,<1.0.0`;
- function `calculateNPTDuration`;
- decision `npt-follow-up-recommendation`;
- action `CreateNPTInvestigation`.

This makes the v0.4 drilling proof the first registry-managed Industry IQ pack without moving OSDU wellbore semantics, drilling source codes or customer data into CEPIO Core.

## Next evolution

The next logical extension after this registry is a deployment-level catalogue that can source pack manifests from separately versioned packages or repositories and bind Skill package requirements to explicit pack-version constraints. The runtime contract introduced here is designed so that discovery can evolve without changing the Core execution boundary.
