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
- `process_industry`
- `manufacturing`
- `epcic`
- `drilling`

### Enterprise

- `enterprise`
- `commercial`

## Current module catalogue

| Module | Namespace | Current module version | Tier | Stability |
|---|---|---:|---|---|
| core | `https://cepio.org/ontology/core#` | 0.2.0 | foundation | stable |
| lifecycle | `.../lifecycle#` | 0.2.0 | foundation | stable |
| kinetic | `.../kinetic#` | 0.2.0 | foundation | stable |
| industrial | `.../industrial#` | 0.2.1 | industrial-common | stable |
| enterprise | `.../enterprise#` | 0.2.0 | enterprise | stable |
| energy | `.../energy#` | 0.2.0 | domain | stable |
| asset | `.../asset#` | 0.1.0 | industrial-common | developing |
| work_management | `.../work#` | 0.1.0 | industrial-common | developing |
| reliability | `.../reliability#` | 0.1.0 | industrial-common | developing |
| hse | `.../hse#` | 0.1.0 | industrial-common | developing |
| supply | `.../supply#` | 0.1.0 | industrial-common | developing |
| performance | `.../performance#` | 0.1.0 | industrial-common | developing |
| workforce | `.../workforce#` | 0.1.0 | industrial-common | developing |
| agentic_operations | `.../agentic#` | 0.1.0 | industrial-common | developing |
| process_industry | `.../process#` | 0.1.2 | domain | developing |
| manufacturing | `.../manufacturing#` | 0.1.0 | domain | experimental |
| epcic | `.../epcic#` | 0.1.0 | domain | developing |
| drilling | `.../drilling#` | 0.1.0 | domain | developing |
| commercial | `.../commercial#` | 0.1.0 | enterprise | developing |

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
