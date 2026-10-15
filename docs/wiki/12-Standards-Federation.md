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

OSDU remains authoritative for upstream domain data where applicable.

CEPIO should:

- preserve OSDU identifiers;
- map OSDU concepts rather than duplicate them unnecessarily;
- provide enterprise relationships to maintenance, finance, projects, commercial context and actions;
- avoid positioning OSDU as a complete enterprise ontology.

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
