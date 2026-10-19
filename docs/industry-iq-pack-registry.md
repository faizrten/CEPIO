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
required Industry IQ pack ID + optional SemVer constraint
      ↓
registry-resolved deployment
      ↓
Skill runtime preflight
      ↓
READY / BLOCKED
      ↓
READY-only dispatch
```

### v0.5.1 Skill-to-pack compatibility

`SkillPreflightSpec` supports two additive forms:

- `industry_iq_packs={"cepio.iq.drilling.npt"}` — legacy ID-only requirement, treated as any installed version;
- `industry_iq_pack_constraints={"cepio.iq.drilling.npt": ">=0.1.0,<0.2.0"}` — explicit Skill-to-pack compatibility contract.

Preflight evaluates the installed runtime version using the same deterministic SemVer language as pack resolution. A Skill fails closed when:

- the required pack is absent (`INDUSTRY_IQ_PACK_UNAVAILABLE`);
- the declared constraint is malformed (`INDUSTRY_IQ_PACK_CONSTRAINT_INVALID`);
- the installed pack version does not satisfy the Skill contract (`INDUSTRY_IQ_PACK_VERSION_INCOMPATIBLE`).

A compatible constrained dependency emits `INDUSTRY_IQ_PACK_COMPATIBLE`. Existing ID-only declarations retain the v0.4/v0.5 `INDUSTRY_IQ_PACK_AVAILABLE` PASS result for backward compatibility.

This closes the gap between deployment composition and Skill admission: pack presence alone is no longer sufficient when a Skill declares a semantic compatibility range.

The pack registry does not weaken Skill preflight. Target-instance evidence remains an independent invocation-time concern.

## Current first-class pack

`cepio.iq.drilling.npt@0.1.0` publishes an explicit manifest declaring:

- CEPIO Core compatibility `>=0.4.0,<1.0.0`;
- function `calculateNPTDuration`;
- decision `npt-follow-up-recommendation`;
- action `CreateNPTInvestigation`.

This makes the v0.4 drilling proof the first registry-managed Industry IQ pack without moving OSDU wellbore semantics, drilling source codes or customer data into CEPIO Core.

## Next evolution

The next logical extension is a deployment-level catalogue that can source pack manifests from separately versioned packages or repositories while preserving the same resolved deployment manifest and Skill preflight contract. Remote or untrusted pack discovery must remain host-controlled; agents and Skills must not install or upgrade their own Industry IQ dependencies.
