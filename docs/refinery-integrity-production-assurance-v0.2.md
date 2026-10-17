# Refinery Integrity + Production Assurance v0.2

This slice implements the second remediation family from the frozen refinery/process-manufacturing v0.2 standards and persona challenge.

## Objective

Connect process operating conditions, mechanical integrity risk and production consequence without creating refinery-only duplicates of reusable industrial semantics.

The intended reasoning chain is:

```text
Operating condition
  -> Integrity Operating Window
  -> Process deviation / excursion
  -> Damage mechanism
  -> Equipment
  -> RBI assessment + inspection evidence
  -> Failure risk
  -> Production capacity / production loss
  -> Economic consequence
```

## Canonical semantics added

### Reliability / industrial-common

- `reliability:DamageMechanism`
- `reliability:RiskBasedInspectionAssessment`
- `reliability:damageMechanismForEquipment`
- `reliability:assessmentForEquipment`
- `reliability:assessmentConsidersDamageMechanism`
- `reliability:assessmentUsesInspection`

`RiskBasedInspectionAssessment` specializes `cepio:Risk`. The model reuses `industrial:Equipment`, `industrial:Inspection`, `reliability:ConditionSignal` and generic CEPIO consequence relationships instead of introducing refinery-specific inspection or pressure-equipment identities.

### Process industry / domain

- `process:IntegrityOperatingWindow`

An integrity operating window specializes the existing `process:OperatingEnvelope`. Excursions are represented using the existing `process:ProcessDeviation` and `process:deviationAgainstEnvelope` semantics. CEPIO intentionally does not add a separate IOW-excursion event hierarchy.

### Performance / industrial-common

- `performance:ProductionCapacity`

Production capacity specializes `cepio:Measurement`. Nameplate, available, constrained and demonstrated capacity should be expressed as measurement context/classification unless later archetypes prove a need for additional canonical classes.

## Explicit non-addition: AvailabilityKPI

The frozen refinery benchmark asks for `performance:AvailabilityKPI`, but the accepted gap triage classified that requirement as **MAPPING** rather than ontology remediation.

Availability is represented with:

- `cepio:KPI`
- `performance:KPIObservation`
- `performance:observationOfKPI`
- `performance:observationForEntity`
- external metric/formula mappings for calculation convention, scope and terminology

This prevents an unbounded class-per-KPI taxonomy while retaining full semantic and analytical expressivity.

## Module versions

| Module | Previous | This slice |
| --- | --- | --- |
| `reliability` | 0.1.0 | 0.1.1 |
| `performance` | 0.1.1 | 0.1.2 |
| `process_industry` | 0.1.2 | 0.1.3 |

## Architectural guardrails

1. Reliability and production-assurance semantics remain reusable across Energy & Process Industry archetypes.
2. `reliability` and `performance` do not import the process domain.
3. IOW reuses the process operating-envelope model rather than creating a parallel hierarchy.
4. Availability remains a KPI instance/formula concern, not an ontology class.
5. The frozen refinery v0.2 competency pack is not modified in this slice.
6. No customer or site-profile vocabulary is introduced.

## Benchmark expectation

The slice should fully remediate `RP-PE-005` because all retained canonical integrity gaps are implemented. `RP-PE-011` should improve but intentionally remain partial in the frozen benchmark because `performance:AvailabilityKPI` is rejected as a canonical class. A future frozen benchmark should test generic KPI composability and metric mapping rather than the literal class name.
