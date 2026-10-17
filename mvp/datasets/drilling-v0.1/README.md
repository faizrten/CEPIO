# CEPIO Synthetic Industrial Dataset — Drilling v0.1

This fixture is the first CEPIO MVP conformance testbed. It is designed to prove that CEPIO can turn heterogeneous drilling data into canonical, traceable industrial objects and relationships that are usable by APIs, applications and agents.

## What is included

- schema and ontology alignment;
- four engineered operational scenarios with known ground truth;
- cross-system entity-resolution aliases;
- twenty golden questions for semantic acceptance testing;
- deterministic Python generator for master data, operations, maintenance and telemetry;
- pytest conformance tests.

The generator intentionally produces source-system inconsistencies through aliases while preserving a canonical IRI for each object. No live customer or vendor data is included.

## Generate the dataset

```bash
python scripts/generate_drilling_mvp_dataset.py \
  --output .generated/drilling-v0.1 \
  --telemetry-points 12000
```

Use a larger `--telemetry-points` value for scale tests. The committed fixture is the contract; generated data should normally remain outside source control.

## MVP acceptance sequence

1. Ingest generated records through CEPIO adapters.
2. Resolve aliases to canonical objects.
3. Verify graph relationships and provenance.
4. Run the twenty golden questions through REST/SDK/MCP.
5. Compare returned values and references to ground truth.
6. Repeat the same test pattern against a refinery fixture to measure CEPIO Core reuse.

## Engineered scenarios

- **SCN-001** — Mud Pump Bearing Degradation: rising vibration and bearing temperature, failure, 4.2 h NPT, repair and signal normalization.
- **SCN-002** — Top Drive Cooling Degradation: early-warning pattern with an open preventive work order and no realized NPT.
- **SCN-003** — BOP Pressure Test Failure: pressure decay, 1.5 h downtime, sealing-element repair and successful recovery.
- **SCN-004** — Mud Pump Discharge Pressure Excursion: intermittent valve sticking, 2.1 h NPT and valve-assembly replacement.

## Definition of done for this fixture

The fixture is considered valid when generation is deterministic, every engineered scenario is linked across telemetry/maintenance/NPT records, entity aliases are unambiguous, all golden questions have explicit expected evidence, and CI passes `tests/test_drilling_mvp_dataset.py`.
