# Standards Federation

## Philosophy

CEPIO should reuse strong existing standards rather than recreate them, while owning only the reusable industrial operating intelligence that connects those standards across decisions, evidence, authority and action.

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

```text
Industry / technical standards
        |
        v
Federation + mapping / Binding Contract
        |
        v
CEPIO thin operating core + Industry IQ
```

External standards are important sources of technical semantics and competency pressure. They are not automatically canonical CEPIO vocabulary.

## Current and targeted references

Relevant standards/ecosystems include:

- OSDU / OSDU DDMS and OSDU-aligned platforms;
- ISA-95 / IEC 62264;
- Digital Twin Consortium Manufacturing Ontologies;
- ISO 15926;
- CFIHOS;
- DEXPI;
- BIM / IFC;
- selective FIBO concepts;
- IADC operational/reporting/contracts guidance where applicable;
- Energistics WITSML;
- PPDM;
- API / SPE references used as competency or assurance benchmarks where appropriate.

The purpose of this list is federation/benchmarking, not wholesale ontology import.

## Federation treatments

Use four explicit treatments:

- **REUSE** — consume the external object/concept directly when its identity/semantics are authoritative;
- **BIND** — expose a thin CEPIO handle/evidence relationship while preserving external authority;
- **EXTEND** — attach CEPIO operating intelligence such as evidence, uncertainty, Decision or workflow semantics to the authoritative external object;
- **OWN** — model only semantics that properly belong to CEPIO's reusable operating abstraction.

A fifth practical outcome is **REJECT** when the literal external/customer term is the wrong CEPIO abstraction and should remain a mapping or derived concept instead.

## ISA-95 / IEC 62264

CEPIO federates Digital Twin Consortium manufacturing ontology concepts as an external semantic source.

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

Manufacturing-specific specialization should stay in manufacturing/domain layers rather than contaminating generic Core.

## OSDU

OSDU remains authoritative for upstream technical-domain data where applicable. Azure Data Manager for Energy / OSDU-aligned managed services are treated as platform/provider bindings rather than CEPIO's semantic definition.

Boundary:

```text
OSDU / ADME
 technical records · DDMS · bulk domain payloads
              |
              | authoritative identity/evidence
              v
CEPIO
 enterprise context · evidence · hypotheses
 uncertainty · confidence · Opportunity / Options
 Decision · authority · workflow · Action · Outcome
```

Examples:

- an OSDU fault interpretation remains the authoritative interpretation object; CEPIO may attach hypotheses/confidence/uncertainty about its operational meaning;
- a reservoir model/scenario remains in OSDU/RESQML; CEPIO may reference it as evidence in an Opportunity/Decision without copying the payload;
- Well, Wellbore, Trajectory, Seismic, Log, Interpretation, Grid and Reservoir Model semantics should be reused/bound where strong rather than recreated.

CEPIO should:

- preserve external record/version identity;
- avoid copying seismic, logs, grids or RESQML bulk data into Core;
- represent cross-domain operating meaning that OSDU does not own;
- use logical/provider-neutral binding capabilities instead of hard-coding one platform implementation;
- treat provider gaps as binding gaps rather than reasons to create a competing DDMS.

## Drilling references: IADC, WITSML, PPDM and related guidance

The Generalization/Competency Harness uses drilling standards and industry references as **benchmarks and mappings**, not canonical authority over CEPIO architecture.

Examples of the intended pattern:

- IADC/WITSML activity/report classifications may be mapped to source-neutral CEPIO activity semantics;
- CEPIO should not create duplicate NPT entities merely because a reporting code set uses a particular label if NPT is better derived from activity/productivity + causal downtime/failure;
- workforce certificates remain evidence, not automatic proof of competence;
- well-control and jack-up assurance semantics may justify domain capability where reusable;
- commercial concepts such as rate/dayrate should reuse common commercial semantics rather than be duplicated in drilling Core vocabulary.

Approved capability alternatives let CEPIO satisfy an industrial competency through a correct semantic composition rather than literal standards vocabulary copying.

## ISO 15926 / CFIHOS / DEXPI

These references are especially useful around engineering information, plant structures, handover and process design.

CEPIO should selectively map them where they improve interoperability and evidence precision while keeping design/engineering bulk content in the systems built to manage it.

## BIM / IFC and spatial systems

BIM/IFC/spatial identifiers can be bound to CEPIO canonical object identity so visualization remains replaceable.

```text
IFC / 3D node
    |
spatial binding
    |
CEPIO object identity
    |
state · evidence · work · risk · Decisions · Actions
```

The viewer/geometry store is not the CEPIO ontology.

## FIBO

FIBO can provide precise financial reference semantics but should not be imported indiscriminately.

Use FIBO where precise finance concepts materially improve interoperability. Keep CEPIO Performance/Commercial semantics focused on connecting physical/operating evidence to objectives, KPIs, contracts, economics and governed Decisions.

Industry Performance Reference Packs should remain organization-neutral; customer formulas/targets are specialization even when financial concepts align to FIBO.

## Standards and competency assurance

External standards can pressure CEPIO through competency questions:

```text
external benchmark
 -> persona / industrial responsibility
 -> competency question
 -> required capability
 -> CEPIO semantic/runtime evaluation
 -> CORE / DOMAIN / MAPPING / PROFILE / REJECT
```

This prevents two failure modes:

1. blindly importing every standard term;
2. claiming industrial competence without checking against recognized external practice.

A semantic PASS against a standards-informed competency still does not establish live operational qualification.

## Binding Contract relationship

Standards federation and platform/provider binding are related but distinct:

- standards federation answers **what external semantics/identity should be reused or mapped**;
- Binding Contract answers **how authoritative provider evidence/action capabilities enter the CEPIO runtime**.

For example, OSDU semantics may be reused while Fabric, ADME or another provider supplies the actual runtime transport.

## Federation rules

1. Reuse external identity where it is authoritative.
2. Do not duplicate a mature standard concept without evidence of CEPIO-specific operating need.
3. Keep external standards modular and attributable.
4. Map external semantics into CEPIO canonical/domain relationships explicitly.
5. Preserve provenance of semantic/source origin.
6. Preserve CEPIO operation when a specific external standard/provider is absent.
7. Prefer capability-based/provider-neutral bindings over provider-specific ontology semantics.
8. Keep technical bulk payload ownership in the domain system designed to manage it.
9. Treat standards as competency pressure, not automatic canonical-vocabulary mandates.
10. Keep customer-specific mappings/interpretations in PROFILE/MAPPING unless independent reuse evidence justifies promotion.

See [Integration Architecture](10-Integration-Architecture.md), [Competency & Assurance](20-Competency-Assurance.md) and [Current State](../current-state.md).
