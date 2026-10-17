# Refinery Quality, Environmental Evidence and Energy Performance v0.6

## Purpose

Phase 6 closes the remaining genuine gaps in the normalized refinery/process-manufacturing capability benchmark without inflating CEPIO with duplicate specification classes or class-per-KPI vocabulary.

## Product quality and disposition

CEPIO already has `manufacturing:MaterialLot`, `manufacturing:MaterialSpecification`, test specifications/results and process quality observations. The missing durable semantics were the relationship between a lot and the material specification against which it is evaluated, and an explicit disposition object for off-spec material.

Added:

- `manufacturing:QualityDisposition` as a governed `cepio:WorkItem`
- `manufacturing:lotEvaluatedAgainstSpecification`
- `manufacturing:dispositionForLot`

This supports:

```text
Material Lot
  -> evaluated against -> Material Specification
  -> quality evidence / test result
  -> Quality Disposition
  -> hold / release / rework / regrade / blend-back / scrap
```

The frozen benchmark literal `lotConformsToSpecification` is normalized away because an off-spec lot cannot truthfully be asserted to conform. Conformance remains a result/evidence property, not graph-edge truth.

## Environmental compliance evidence

Added to `process_industry`:

- `process:EmissionLimit` as a `kinetic:Constraint`
- `process:evaluatedAgainstEmissionLimit`

The existing `process:EmissionObservation` and `process:emissionFromUnit` now form a complete compliance-evidence chain:

```text
Process Unit
  <- emission from - Emission Observation
  -> evaluated against -> Emission Limit
  -> corrective action / compliance response
```

This is source-neutral process-industry semantics suitable for refining, petrochemicals, gas processing and other continuous-process facilities.

## Energy performance

No `performance:EnergyIntensityKPI` class is introduced.

Energy intensity remains:

```text
cepio:KPI
  + performance:KPIObservation
  + mappings/performance_kpis.yaml#energy-intensity
```

The mapping preserves ISO 50001-oriented identity plus formula, denominator, unit, baseline and target conventions as external metric metadata and provenance. This prevents an unbounded ontology class for every business KPI.

## Normalized benchmark v0.1.2

The raw frozen refinery v0.1 pack is unchanged. The normalization layer now also corrects:

- generic `manufacturing:Specification` -> canonical `manufacturing:MaterialSpecification`
- misleading `lotConformsToSpecification` -> `lotEvaluatedAgainstSpecification`
- generic `cepio:impacts` quality-disposition edge -> `manufacturing:dispositionForLot`
- `performance:EnergyIntensityKPI` -> canonical `cepio:KPI` plus metric mapping

Target normalized result:

- 41/41 capability checks
- 100.0% semantic readiness
- PASS 16 / PARTIAL 0 / FAIL 0 / ERROR 0

CI is authoritative.

## Versioning

- `manufacturing`: 0.1.0 -> 0.1.1
- `process_industry`: 0.1.5 -> 0.1.6
- `performance`: remains 0.1.2 because only mapping metadata changes
