# Integration Architecture

## Integration principle

CEPIO does not replace systems of record. It creates a stable semantic and operational layer above them.

```text
Source systems
 SAP · PI · OSDU · P6 · MES · engineering · SQL · Fabric
       |
       v
Mapping / Adapter / Event ingestion
       |
       v
CEPIO canonical objects + relationships + state + provenance
       |
       v
Applications / Agents / Governed actions
```

## Adapter contract

An adapter should translate between an external system and CEPIO while preserving:

- stable CEPIO identity;
- canonical types/properties;
- source references;
- external acknowledgement;
- authorization boundaries;
- reconciliation.

## SAP S/4HANA / EAM

Expected roles:

- equipment/functional location source;
- maintenance work management;
- materials/spares;
- procurement and vendors;
- external writeback destination for governed work actions.

Production-grade SAP integration is targeted for v0.5. Current repository direction includes dry-run/reference contracts.

## AVEVA PI / historian

Expected roles:

- time-series observations;
- equipment/process operational state signals;
- events and anomalies;
- near-real-time evidence for functions and decisions.

A production streaming adapter is targeted for v0.5.

## OSDU

OSDU should be treated as an authoritative upstream data foundation, not as the enterprise ontology.

Recommended relationship:

```text
OSDU authoritative upstream records
       |
       v
CEPIO semantic projection / mapping
       |
       v
Enterprise context across operations, maintenance, finance, projects and action
```

Preserve OSDU identity and domain semantics where appropriate while projecting them into CEPIO's enterprise operating abstraction.

## Primavera P6

Expected roles:

- project schedules;
- turnaround planning;
- EPCIC activities;
- dependencies and milestones.

## Fabric / OneLake

Fabric may provide the analytical and operational data foundation under CEPIO, including Lakehouse, Warehouse, Eventhouse/KQL and other data products.

CEPIO still owns canonical industrial semantics.

## Visualization and spatial systems

Spatial/3D viewers should be treated as additional projections of CEPIO identity rather than as the ontology itself.

Potential pattern:

```text
3D object/node
   |
spatial binding
   |
CEPIO object ID
   |
ontology + state + provenance + actions
```

This allows visualization technology to remain replaceable.

## Integration maturity model

### Level 0 — static mapping

Source extracts are mapped into CEPIO.

### Level 1 — refreshable context

Mappings run repeatedly with provenance and identity resolution.

### Level 2 — event-driven operational state

Near-real-time events update CEPIO state.

### Level 3 — governed action

CEPIO executes approved external actions.

### Level 4 — closed-loop reconciliation

External acknowledgement returns into CEPIO, and outcomes feed subsequent decisions.
