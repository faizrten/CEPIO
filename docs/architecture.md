# CEPIO v0.2 Architecture

## Design target

CEPIO is an **operational ontology**, not a semantic catalog. Its runtime is intended to provide the stable business abstraction that applications and AI agents interact with while underlying source systems remain replaceable.

## Runtime components

```text
                        CEPIO Runtime
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
 Object Repository      Event Repository      Audit Repository
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             │
                      Ontology Registry
                    types · inheritance
                  relationship constraints
                             │
                        Policy Engine
                             │
                 ┌───────────┴───────────┐
                 │                       │
           Function Runtime        Action Runtime
                 │                       │
              typed IO             authorization
              traversal             preconditions
                                    idempotency
                                    audit
                                    versioning
                                    compensation metadata
                             │
                        Adapter Boundary
             SAP · PI · OSDU · P6 · Fabric · others
```

## Persistence boundary

`ObjectRepository`, `EventRepository`, `AuditRepository` and `DecisionRepository` are domain-facing interfaces. v0.2 ships in-memory and SQLite reference implementations. Future graph, Fabric or cloud persistence must implement the same contracts instead of leaking storage semantics into applications.

## Semantic integrity

RDF/OWL modules are parsed into `TypeRegistry`. The runtime rejects undeclared object and relationship types and can enforce `rdfs:domain` / `rdfs:range` using subclass reasoning.

Example:

```text
Compressor is-a RotatingEquipment
RotatingEquipment is-a Equipment

hasWorkOrder domain Equipment
hasWorkOrder range WorkOrder

Compressor --hasWorkOrder--> WorkOrder  ✓
Hydrocracker --hasWorkOrder--> WorkOrder ✗
```

## Kinetic safety boundary

Action execution order is:

```text
resolve target
    ↓
resolve action definition
    ↓
policy evaluation
    ↓
authorized idempotency replay check
    ↓
preconditions
    ↓
effect handler
    ↓
immutable audit
    ↓
optional external adapter
```

Policy is evaluated **before** idempotent replay. Client-provided idempotency keys are internally scoped by actor + action + target, preventing a successful result from becoming an authorization bypass.

## Agent boundary

The MCP facade exposes ontology tools through an actor-scoped security context. Object-type and property filtering is applied on reads; action policy is always re-evaluated by the runtime. Agents can therefore be given broad reasoning context while remaining denied from high-risk execution.

## Versioning

Every object carries an integer `version`. Mutations may supply an `expected_version`. A mismatch fails with a concurrency conflict rather than silently overwriting a newer state.

## Source-system strategy

Adapters remain side-effect-free stubs in v0.2. The next integration phase should implement transactional adapters while preserving three invariants:

1. CEPIO IDs remain stable even if external system IDs change.
2. external writeback is never invoked before CEPIO authorization and validation;
3. reconciliation records the source-system result back into CEPIO provenance/audit.
