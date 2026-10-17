# Refinery Instrumentation and Engineering Topology v0.4

## Purpose

This slice adds the minimum reusable semantics needed to connect field instrumentation and authoritative engineering topology to CEPIO process context without copying PA-DIM, DEXPI, CFIHOS or NAMUR NOA models into the canonical ontology.

## Canonical process-industry additions

- `process:ProcessVariable` — durable process context representing what is measured or controlled independently of any individual observation value.
- `process:PipingSegment` — source-neutral physical process connection used to reconstruct process topology.

Key relationships:

- `process:measuresProcessVariable` — links canonical `industrial:Equipment` to the process variable it measures.
- `process:carriesStream` — links a physical `process:PipingSegment` to a `process:ProcessStream`.

Observed values continue to use `cepio:Measurement`-derived semantics, including timestamps and provenance. Device health and diagnostic observations reuse `reliability:ConditionSignal`.

## PA-DIM federation boundary

The accepted refinery v0.2 triage classifies PA-DIM `ProcessDevice` and `DeviceDiagnosticObservation` as mapping-layer concepts rather than new CEPIO classes.

`mappings/process_instrumentation_bindings.yaml` therefore maps:

```text
PA-DIM ProcessDevice
  -> industrial:Equipment
  -> asset:InstalledAsset
  -> asset:FunctionalLocation
  -> process:measuresProcessVariable
  -> process:ProcessVariable

PA-DIM DeviceDiagnosticObservation
  -> reliability:ConditionSignal
  -> reliability:observedOnEquipment
  -> industrial:Equipment
```

External identifiers and dictionary references remain mapping provenance. This avoids a second device identity model beside CEPIO's existing industrial and asset semantics.

## Engineering topology boundary

CEPIO adds only the topology required for cross-system reasoning:

```text
DesignTag
  -> InstalledAsset / Equipment
  -> PipingSegment
  -> ProcessStream
  -> ProcessUnit
```

Detailed DEXPI line classes, engineering attributes and CFIHOS exchange structures remain external. The ontology provides the stable semantic join points; exchange schemas remain replaceable adapters.

## NAMUR NOA boundary

A NAMUR NOA monitoring-and-optimization channel describes deployment and integration topology rather than a physical/process business object. It is therefore represented as a `cepio:DigitalAsset` integration binding using the existing `cepio:dependsOn` relationship.

```text
Monitoring / optimization application or channel
  -> cepio:DigitalAsset
  -> cepio:dependsOn
  -> industrial:Equipment
  -> process:ProcessVariable
```

The binding records that the control path remains unchanged, the monitoring/optimization path is separate, and policy/provenance metadata is required. CEPIO does not create `process:MonitoringOptimizationChannel`.

## Intended refinery reasoning chain

```text
Functional Location
  -> Installed Equipment
  -> Process Variable
  -> Measurement / Condition Signal
  -> Operating Envelope / Constraint
  -> Alarm / Deviation
  -> Process Unit

Engineering Tag
  -> Installed Equipment
  -> Piping Segment
  -> Process Stream
  -> Process Unit
```

This creates the semantic substrate for live process observability, brownfield instrumentation federation and engineering-record reconstruction while preserving a single canonical asset identity.

## Generalization guardrails

- The frozen refinery persona/standards competency pack v0.2 is unchanged.
- No `process:ProcessDevice` class is introduced.
- No `process:DeviceDiagnosticObservation` class is introduced.
- No `process:MonitoringOptimizationChannel` class is introduced.
- `industrial:Equipment`, `asset:InstalledAsset`, `asset:FunctionalLocation` and `reliability:ConditionSignal` are reused.
- Detailed PA-DIM, DEXPI, CFIHOS and NAMUR NOA structures remain external mappings/integration bindings.
- No customer or site vocabulary is introduced.
- Industrial-common modules do not acquire a reverse dependency on the process domain.

## Frozen benchmark expectation

The benchmark remains unchanged. Expected movement is:

- `RP-PE-007`: 3/7 -> 4/7 PARTIAL
- `RP-PE-008`: 6/8 -> 8/8 PASS
- `RP-PE-012`: 2/6 -> 2/6 PARTIAL
- aggregate: 64/87 (73.6%) -> 67/87 (77.0%)
- expected status: PASS 5 / PARTIAL 7 / FAIL 0 / ERROR 0

The intentionally unresolved literal terms in `RP-PE-007` and `RP-PE-012` are evidence of the federation boundary, not ontology defects.

## Versioning

`process_industry` advances from `0.1.4` to `0.1.5`.
