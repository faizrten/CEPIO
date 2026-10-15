# Architecture

## Five-plane architecture

```text
Applications · Workspaces · Copilots · Agents
                       |
               EXPERIENCE PLANE
                       |
Functions · Decisions · Actions · Workflows
                       |
                  KINETIC PLANE
                       |
Objects · Relationships · Events · State · KPI
                       |
                 SEMANTIC PLANE
                       |
Policy · Time · Provenance · Audit · Versioning
                       |
                GOVERNANCE PLANE
                       |
SAP · PI · OSDU · P6 · Fabric · MES · other systems
                       |
               INTEGRATION PLANE
```

### Experience plane

The experience plane contains the interfaces people and software interact with:

- web applications;
- engineering workspaces;
- copilots;
- AI agents;
- analytics experiences;
- domain applications;
- visualization layers.

The experience plane should consume CEPIO contracts instead of embedding direct source-system logic.

### Kinetic plane

The kinetic plane defines what the enterprise **can do**:

- functions;
- decisions;
- recommendations;
- governed actions;
- workflows;
- constraints and preconditions.

### Semantic plane

The semantic plane defines what the enterprise **is**:

- objects;
- relationships;
- properties;
- events;
- state;
- KPIs and risks.

### Governance plane

The governance plane makes the operating abstraction trustworthy:

- identity and actor context;
- policy;
- valid time and transaction time;
- property provenance;
- immutable audit;
- semantic versioning;
- migration contracts.

### Integration plane

The integration plane connects CEPIO to systems of record and systems of execution while preserving canonical CEPIO identity and semantics.

## Runtime architecture

```text
                        CEPIO Runtime
                             |
        +--------------------+---------------------+
        |                    |                     |
 Object Repository      Event Repository      Audit Repository
        |                    |                     |
        +--------------------+---------------------+
                             |
                      Ontology Registry
                    types · inheritance
                  relationship constraints
                             |
                        Policy Engine
                             |
                 +-----------+-----------+
                 |                       |
           Function Runtime        Action Runtime
                 |                       |
              typed IO             authorization
              traversal             preconditions
                                    idempotency
                                    audit
                                    versioning
                                    compensation metadata
                             |
                        Adapter Boundary
             SAP · PI · OSDU · P6 · Fabric · others
```

## Persistence boundary

Domain-facing repository interfaces isolate CEPIO semantics from persistence technology.

Current reference implementations include:

- in-memory repositories;
- SQLite.

These are intentionally reference implementations, not the final enterprise-scale persistence architecture.

Future Fabric, graph or distributed storage implementations should satisfy the same domain contracts.

## Semantic integrity

RDF/OWL modules are parsed into a type registry. Runtime validation can reject undeclared types and enforce domain/range constraints through subclass reasoning.

Example:

```text
Compressor is-a RotatingEquipment
RotatingEquipment is-a Equipment

hasWorkOrder domain Equipment
hasWorkOrder range WorkOrder

Compressor --hasWorkOrder--> WorkOrder  OK
Hydrocracker --hasWorkOrder--> WorkOrder  INVALID
```

## Adapter boundary

Adapters isolate CEPIO from external-system implementation details.

Three durable invariants are important:

1. CEPIO IDs remain stable even when source-system IDs change.
2. External writeback occurs only after CEPIO authorization and validation.
3. Source-system acknowledgement and reconciliation return into CEPIO provenance/audit.

## Canonical vs platform-specific architecture

```text
CEPIO semantic contract
        |
        +-------------------+
        |                   |
        v                   v
Microsoft binding       Other bindings
Fabric / Foundry        graph / cloud / local
        |
        v
Customer deployment/profile
```

This prevents CEPIO from becoming equivalent to a specific Microsoft service while still allowing Microsoft-native implementation.
