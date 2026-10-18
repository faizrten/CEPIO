# CEPIO Petrophysics v1.1 — Operational Evidence Binding

Status: experimental

## Purpose

Petrophysics v1 qualified CEPIO reasoning against synthetic fixtures. v1.1 proves a North-Star property: **the Petrophysics operating abstraction must remain stable when the underlying evidence provider changes.**

The reasoning engines are unchanged. A provider resolves authoritative source records into the existing logical evidence package, after which CEPIO performs the same semantic, uncertainty, assurance, dependency and authority reasoning.

```text
Source systems / data plane
        |
        v
PetrophysicsEvidenceProvider
        |
        v
logical evidence package
        |
        +--> PET-02 FormationEvaluationAssuranceRuntime
        |
        +--> PetrophysicsV1Runtime (PET-05 / PET-06)
        |
        v
same CEPIO reasoning + policy contract
```

## Provider-neutral contract

`PetrophysicsEvidenceProvider` exposes:

- `provider_id`
- `supported_journeys`
- `resolve_pet02(well, interval)`
- `resolve_v1_portfolio()`

`PetrophysicsOperationalRuntime` consumes the provider contract and continues to run CEPIO Skill preflight and policy enforcement independently of the source implementation.

The synthetic provider supports PET-01 through PET-08. It is retained as the regression oracle.

## Microsoft Fabric provider

`FabricPetrophysicsEvidenceProvider` lives under `cepio.integrations.microsoft`; Fabric concepts do not leak into the provider-neutral Petrophysics runtime.

v1.1 covers three operational spearhead journeys:

- PET-02 — Formation Evaluation Assurance
- PET-05 — Cross-Well Interpretation Consistency
- PET-06 — Model Handover & Property Propagation

The provider consumes normalized table rows through the injected `FabricTableReader` transport boundary. The public profile is `integrations/microsoft/fabric_iq/petrophysics-v1.evidence.yaml`.

The initial logical tables cover context, formation-evaluation cases, evidence references, uncertainty/confidence, downstream dependencies, cross-well interpretation summaries and model-handover transformations.

### What v1.1 does not claim

v1.1 does **not** claim a live authenticated Fabric SQL connection. The included `InMemoryFabricTableReader` executes the exact table contract using Fabric-shaped rows so provider invariance is deterministic in CI. A live SQL/Lakehouse reader can be injected later without changing Petrophysics reasoning.

This distinction is intentional: v1.1 freezes the source contract before coupling it to workspace credentials, networking or a specific Fabric access surface.

## Source-authority invariant

Fabric may contain a replicated or curated view of technical evidence. That does not make Fabric the technical source of authority.

For example, a WellLog referenced through a Fabric table still retains:

```text
source_system  = osdu
source_service = wellbore_ddms
record_id      = opendes:...WellLog:A17-PETRO-MAIN
record_version = 1759000000000001
```

CEPIO therefore preserves original source identity/version across the adapter boundary.

## Bulk-data boundary

The Fabric evidence tables contain metadata, interpreted findings, evidence references, assessments and dependency lineage. They do not contain LAS payloads or bulk curve arrays.

Bulk well-log data remains in the governed technical data plane. CEPIO consumes the evidence identity/context required for enterprise reasoning.

## Parity gate

v1.1 is accepted only when the same qualified runtime returns semantically identical outputs for Synthetic and Fabric providers:

```text
PET-02 Synthetic == Fabric
PET-05 Synthetic == Fabric
PET-06 Synthetic == Fabric
```

The parity checks include:

- authoritative/superseded interpretation resolution;
- interpretation deltas;
- contradictory core/log evidence;
- uncertainty and confidence;
- original source/version provenance;
- cross-well method/cutoff/transform inconsistency;
- model handover transformations;
- stale dependency detection;
- downstream impact;
- provider-independent policy and Skill preflight.

## North-Star significance

This milestone establishes a key CEPIO property:

> **CEPIO owns the industrial operating abstraction; the evidence provider is a replaceable implementation beneath it.**

The next transport increment can bind the same Fabric provider contract to an actual Azure/Fabric Lakehouse or SQL endpoint. A later OSDU/ADME provider should satisfy the same logical Petrophysics evidence contract rather than creating a new reasoning path.
