# Standards Federation

## Philosophy

CEPIO should reuse strong existing standards rather than recreate them, while still owning the enterprise operating abstraction that connects them.

```text
Industry / technical standards
        |
        v
Federation + mapping
        |
        v
CEPIO enterprise operating abstraction
```

## Current and targeted standards

- OSDU
- ISA-95 / IEC 62264
- Digital Twin Consortium Manufacturing Ontologies
- ISO 15926
- CFIHOS
- DEXPI
- BIM / IFC
- selective FIBO concepts

## ISA-95 / IEC 62264

CEPIO currently federates Digital Twin Consortium manufacturing ontology concepts as an external semantic source.

Shared concepts converge on existing CEPIO semantics where appropriate.

Example:

```text
DTC / ISA-95              CEPIO
---------------------------------------------
Equipment              -> industrial:Equipment
PhysicalAsset          -> core:PhysicalAsset
Person                 -> core:Person
MaterialRequirement    -> supply:MaterialRequirement
```

Manufacturing-specific concepts live under CEPIO's manufacturing namespace rather than contaminating generic core semantics.

## OSDU

OSDU remains authoritative for upstream technical domain data where applicable. Azure Data Manager for Energy (ADME) is a managed OSDU-aligned implementation and is treated as a platform binding, not as CEPIO's semantic definition.

CEPIO uses four explicit federation treatments:

- **REUSE** — consume the OSDU/DDMS object directly;
- **BIND** — expose a thin CEPIO enterprise handle while preserving OSDU authority and identity;
- **EXTEND** — attach CEPIO reasoning/decision sidecars to an authoritative OSDU object;
- **OWN** — model only semantics that properly belong to the CEPIO operating abstraction.

The first executable contract is `mappings/osdu_subsurface_bindings.yaml` and the design rationale is documented in `docs/subsurface-osdu-boundary-v0.1.md`.

The key boundary is:

```text
OSDU / ADME
  technical data, schemas, DDMS, bulk domain payloads
              |
              | authoritative references
              v
CEPIO
  enterprise context, evidence, hypotheses,
  uncertainty, confidence, decisions and actions
```

For example, an OSDU `FaultInterpretation` remains the authoritative interpretation object. CEPIO may attach a `Hypothesis`, `ConfidenceAssessment` or `UncertaintyAssessment` describing what the enterprise currently believes about that interpretation and why.

Likewise, OSDU `ReservoirModelScenario` remains the scenario/model record. CEPIO may reference it as evidence and attach assumptions, uncertainty assessments and decision provenance without copying the reservoir-model payload.

CEPIO should therefore:

- preserve OSDU record and version identifiers;
- map OSDU concepts rather than duplicate them unnecessarily;
- never copy seismic, well-log or RESQML bulk payloads into canonical CEPIO state;
- provide enterprise relationships to maintenance, drilling, finance, projects, commercial context and governed actions;
- represent evidence, hypothesis, uncertainty, confidence and information gain using CEPIO Core semantics;
- resolve OSDU/ADME access through logical capabilities rather than hard-coding one service path;
- treat current platform-service gaps as binding gaps, not reasons to create competing CEPIO DDMS implementations;
- avoid positioning OSDU as a complete enterprise operating ontology.

## ISO 15926 / CFIHOS / DEXPI

These standards are useful especially around engineering information, plant structures, handover and process design.

CEPIO should reference and map them selectively where they improve interoperability and semantic precision.

## FIBO

FIBO can be useful for precise financial concepts but should not be imported indiscriminately into an industrial operating ontology.

Use FIBO where financial semantics require it; keep CEPIO's enterprise/commercial modules focused on the operational concepts needed to connect physical performance to economic consequence.

## Federation rules

1. Reuse external identity where it is authoritative.
2. Do not duplicate a mature standard concept without a reason.
3. Keep external standards modular.
4. Map to CEPIO's canonical enterprise relationships.
5. Maintain provenance of semantic origin.
6. Preserve CEPIO's ability to operate even when a specific external standard is absent.
7. Prefer capability-based runtime bindings over provider-specific ontology semantics.
8. Keep technical bulk payload ownership in the domain system designed to manage it.
