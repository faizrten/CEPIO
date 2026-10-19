# Ontology Model

## Modular ontology architecture

CEPIO uses modular RDF/OWL ontologies rather than one monolithic schema.

### Foundation

- `core`
- `lifecycle`
- `kinetic`

### Industrial common

- `industrial`
- `asset`
- `work_management`
- `reliability`
- `hse`
- `supply`
- `performance`
- `workforce`
- `agentic_operations`

### Domain

- `energy`
- `subsurface`
- `process_industry`
- `manufacturing`
- `epcic`
- `drilling`

### Enterprise

- `enterprise`
- `commercial`

## Current module catalogue

The versions below mirror `ontology-modules.yaml` on this branch. That manifest remains the machine-readable source of truth.

| Module | Namespace | Current module version | Tier | Stability |
|---|---|---:|---|---|
| core | `https://cepio.org/ontology/core#` | 0.3.1 | foundation | stable |
| lifecycle | `.../lifecycle#` | 0.2.0 | foundation | stable |
| kinetic | `.../kinetic#` | 0.3.0 | foundation | stable |
| industrial | `.../industrial#` | 0.2.2 | industrial-common | stable |
| enterprise | `.../enterprise#` | 0.2.0 | enterprise | stable |
| energy | `.../energy#` | 0.2.0 | domain | stable |
| subsurface | `.../subsurface#` | 0.2.0 | domain | experimental |
| asset | `.../asset#` | 0.1.1 | industrial-common | developing |
| work_management | `.../work#` | 0.1.1 | industrial-common | developing |
| reliability | `.../reliability#` | 0.1.3 | industrial-common | developing |
| hse | `.../hse#` | 0.1.2 | industrial-common | developing |
| supply | `.../supply#` | 0.1.1 | industrial-common | developing |
| performance | `.../performance#` | 0.1.5 | industrial-common | developing |
| workforce | `.../workforce#` | 0.1.3 | industrial-common | developing |
| agentic_operations | `.../agentic#` | 0.1.1 | industrial-common | developing |
| process_industry | `.../process#` | 0.1.6 | domain | developing |
| manufacturing | `.../manufacturing#` | 0.1.1 | domain | experimental |
| epcic | `.../epcic#` | 0.1.0 | domain | developing |
| drilling | `.../drilling#` | 0.1.3 | domain | developing |
| commercial | `.../commercial#` | 0.1.2 | enterprise | developing |

## Common decision and optimization semantics

The Drilling Contractor domain-qualification remediation deliberately adds reusable semantics to common modules rather than creating drilling-only shortcuts:

- `agentic_operations:Prediction` represents model-derived inference separately from observed enterprise fact and can carry operating scope/risk context;
- `agentic_operations:Recommendation` can be explicitly grounded in supporting enterprise evidence and governed at a control point;
- `kinetic:OperationalPlan` and `kinetic:PlanRevision` preserve the original plan and its proposed revision as distinct governed records, with an authorizing `kinetic:Decision`;
- `performance:OutcomeAssessment` links a governed decision/intervention to KPI outcome evidence and risk context rather than storing an unsupported scalar value-realization claim.

These abstractions were introduced to close reusable enterprise/optimization gaps while keeping the drilling ontology source-neutral. See [Drilling domain qualification remediation v0.4.1](../drilling-domain-qualification-remediation-v0.4.1.md) for the qualification rationale and regression evidence.

## Core primitives

Common CEPIO concepts include:

```text
Entity
Asset
Activity
Event
State
Party
Organization
Location
Material
Resource
Measurement
KPI
Risk
Objective
Capability
Process
Document
Contract
WorkItem
Decision
Action
```

## Operational Asset as semantic pivot

The operational asset is a particularly important bridge between domains.

```text
Finance / Margin
      |
Process / Production
      |
Operational Asset
  /   |    |    \
Reliability Work Supply HSE
      |
Workforce / Vendors / Documents
```

A chain such as the following is therefore possible:

```text
EBITDA
 -> Margin
 -> Hydrocracker
 -> K-201 Recycle Gas Compressor
 -> TripEvent
 -> Bearing
 -> WorkOrder
 -> SparePart
 -> Supplier
```

## Procedure and alarm operations

The refinery Generalization Lab strengthens two layers without creating refinery-only identities.

Industrial-common owns reusable alarm/control semantics:

```text
industrial:Alarm
industrial:AlarmRationalization
industrial:ControlLoop
industrial:alarmForState
industrial:rationalizesAlarm
```

Process Industry owns continuous-process operating semantics:

```text
process:OperatingProcedure
process:ProcedureStep
process:ProcedureExecution
process:executesProcedure
process:AbnormalSituation
```

`industrial:alarmForState` ranges over generic `cepio:State`. A process-industry abnormal situation specializes that state, which lets the same alarm model remain usable across refining, chemicals, power, upstream, drilling and manufacturing.

Procedure execution reuses `cepio:dependsOn` for work permits, isolations, barriers and other execution gates rather than adding procedure-specific work-control predicates.

## Integrity and production assurance

Mechanical-integrity semantics live in industrial-common reliability:

```text
reliability:DamageMechanism
reliability:RiskBasedInspectionAssessment
reliability:damageMechanismForEquipment
reliability:assessmentForEquipment
reliability:assessmentConsidersDamageMechanism
reliability:assessmentUsesInspection
```

Continuous-process integrity context remains in the process domain:

```text
process:IntegrityOperatingWindow
  rdfs:subClassOf process:OperatingEnvelope
```

Integrity excursions reuse `process:ProcessDeviation` and `process:deviationAgainstEnvelope`, avoiding a parallel excursion-event hierarchy.

Production assurance adds the reusable measurement `performance:ProductionCapacity`. Availability remains an instance of generic `cepio:KPI`, observed through `performance:KPIObservation`, rather than a dedicated `AvailabilityKPI` ontology class. This keeps KPI identity, formulas and external terminology in the metric/mapping layer instead of proliferating classes.

## Enterprise performance semantics

Performance module v0.1.5 adds the semantic grammar for the [Enterprise Performance Graph](22-Enterprise-Performance-Graph.md):

```text
performance:PerformanceContract
performance:Outcome
performance:KeyResult
performance:Target
performance:Threshold
performance:Guardrail
performance:Accountability
performance:Contribution
performance:PerformanceResponseBinding
```

The model deliberately reuses core `cepio:Objective`, `cepio:KPI`, `cepio:Measurement`, `cepio:Evidence`, `cepio:dependsOn` and `cepio:contributesTo`. Organization-specific KPI formulas, targets and conventions remain Performance Contract / Business Logic semantics instead of becoming global ontology classes.

This allows CEPIO to connect enterprise objectives, role/persona accountability, individual key results, operating KPIs and evidence while preserving tenant-specific business meaning.

## IRI-first identity

Canonical semantic identity uses full IRIs.

Example:

```text
https://cepio.org/ontology/industrial#WorkOrder
```

QName/local aliases such as `industrial:WorkOrder` or `WorkOrder` are convenience forms. Ambiguous aliases should fail closed rather than silently resolve to the wrong concept.

## Canonical property contract

Property semantics are maintained through a canonical contract rather than uncontrolled field proliferation.

A source attribute is classified as one of:

```text
Canonical property
Relationship key
Observation value
Observation timestamp
Provenance metadata
Profile/customer-specific property
```

## Profiles and extensions

Canonical modules should remain broadly reusable. Customer-specific semantics belong in profiles or approved extensions.

A SATORP profile, for example, can specialize refinery/petrochemical semantics without redefining the generic Process Industry ontology.

## Compatibility and migration

Ontology modules are versioned production contracts.

CI checks changes to:

- module namespace/version;
- classes;
- relationships;
- datatype properties;
- subclass hierarchy;
- domain/range restrictions;
- datatype ranges.

Breaking changes require explicit migration manifests.
