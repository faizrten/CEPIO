# Digital Twin Consortium ISA-95 Manufacturing federation

CEPIO federates the Digital Twin Consortium (DTC) `ManufacturingOntologies` repository as a standards-aligned manufacturing semantic source.

## Upstream baseline

- Repository: `digitaltwinconsortium/ManufacturingOntologies`
- Pinned commit: `f6b45fc83c922177fa7590c530339c4876b677c6`
- Standard family: ISA-95 / IEC 62264
- Source representations: DTDL and W3C Web of Things Thing Models
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)

The DTC models are licensed under CC BY 4.0. CEPIO retains attribution to the Digital Twin Consortium and links back to the upstream repository. CEPIO does not vendor the generated upstream corpus; the source commit is pinned in `mappings/dtc_isa95_to_cepio.yaml` for reproducibility and review.

## Architecture

```text
DTC ManufacturingOntologies
ISA-95 DTDL + WoT models
          │
          ▼
DTC federation/mapping contract
          │
          ▼
CEPIO manufacturing domain
          │
  ┌───────┼────────┬─────────┐
  │       │        │         │
 core  industrial supply  manufacturing
  │       │        │         │
  └───────┴────────┴─────────┘
          │
          ▼
CEPIO runtime / Fabric IQ / Foundry / applications
```

The constitutional rule remains unchanged: external standards and platform services may inform or implement CEPIO semantics, but they do not become the authority for CEPIO's canonical industrial meaning.

## Why federation rather than copying

The DTC repository is a generated implementation of ISA-95 concepts in DTDL and WoT. CEPIO is an operational ontology with its own canonical identities, temporal/provenance kernel, policy model and action semantics.

Directly copying the source models would create duplicate concepts such as `Equipment`, `PhysicalAsset`, `Person`, and `MaterialRequirement`. Instead CEPIO applies four mapping dispositions:

1. **Equivalent/convergent** — reuse an existing CEPIO type when the semantics already align.
2. **Normalized** — promote a manufacturing concept into `https://cepio.org/ontology/manufacturing#`.
3. **Property normalization** — map generated `*Property` interfaces into CEPIO canonical datatype properties, observations, relationships and provenance.
4. **Review before promotion** — retain less-common source concepts as federated upstream semantics until a CEPIO use case justifies canonical promotion.

## Key convergence mappings

| DTC / ISA-95 concept | CEPIO canonical concept | Treatment |
|---|---|---|
| `Equipment` | `industrial:Equipment` | equivalent |
| `PhysicalAsset` | `core:PhysicalAsset` | equivalent |
| `Person` | `core:Person` | equivalent |
| `MaterialRequirement` | `supply:MaterialRequirement` | convergence |
| `HierarchyScope` | `manufacturing:HierarchyScope` | normalized |
| `OperationsDefinition` | `manufacturing:OperationsDefinition` | normalized |
| `OperationsCapability` | `manufacturing:OperationsCapability` | normalized |
| `OperationsSchedule` / `OperationsRequest` | `manufacturing:*` | normalized |
| `OperationsPerformance` / `OperationsResponse` | `manufacturing:*` | normalized |
| `WorkDefinition` / `WorkMaster` | `manufacturing:*` | normalized |
| `WorkSchedule` / `WorkRequest` / `JobOrder` | `manufacturing:*` | normalized |
| `WorkPerformance` / `JobResponse` | `manufacturing:*` | normalized |
| `WorkflowSpecification` | `manufacturing:WorkflowSpecification` | normalized |

## ISA-95 hierarchy

DTC's `HierarchyScope` includes the standard role-based levels such as Enterprise, Site, Area, Work Center, Work Unit, Process Cell, Production Line, Production Unit, Work Cell, Storage Zone and Storage Unit.

CEPIO represents these as operational scope/functional-asset concepts while leaving company-specific site and area structures to profiles and source mappings.

```text
Enterprise
   ↓
Site
   ↓
Area
   ↓
Work Center / Process Cell / Production Line
   ↓
Work Unit / Production Unit / Work Cell
   ↓
Equipment / Physical Asset
```

This allows the same CEPIO graph to bridge ISA-95 manufacturing hierarchy with process-industry units, asset management, work management and enterprise context.

## Property-object normalization

Many ISA-95 DTC interfaces are generated property carriers, for example `EquipmentProperty`, `MaterialClassProperty` and `PersonnelCapabilityProperty`.

CEPIO does not promote those containers as operational business objects. Their values should be classified through the existing canonical-property contract:

```text
DTC *Property interface
        │
        ├── datatype property ──► CEPIO canonical property IRI
        ├── foreign reference ──► CEPIO relationship
        ├── measured value ─────► Observation / Measurement
        └── source metadata ────► CEPIO property provenance
```

`PropertyMeasurement` and `EvaluatedProperty` are exceptions because they represent test/quality domain semantics rather than generic generated property containers.

## Coverage

The federation contract records the DTC families covered by the integration.

### ISA-95 Part 2

- Material
- Operational Location
- Operations Capability
- Operations Definition
- Operations Event
- Operations Performance
- Operations Record
- Operations Schedule
- Operations Test
- Personnel
- Physical Asset and Equipment
- Process Segment

### ISA-95 Part 4

- Resource Relationship
- Work Alert
- Work Calendar
- Work Capability
- Work Definition
- Work Performance
- Work Record
- Work Schedule
- Workflow Specification

## Versioning

The upstream DTC commit is intentionally pinned. A future upstream refresh should:

1. compare DTC source-model changes against the pinned commit;
2. classify new/changed concepts;
3. update `mappings/dtc_isa95_to_cepio.yaml`;
4. update the CEPIO `manufacturing` module version according to semantic-versioning rules;
5. pass CEPIO module compatibility, ontology, SHACL and runtime tests.

This keeps upstream evolution explicit and prevents a source repository update from silently changing CEPIO's canonical contract.
