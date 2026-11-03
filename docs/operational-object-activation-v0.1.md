# Operational Object Activation v0.1 — bounded reference inspection

## Purpose and boundaries

This is the **first implementation slice** of the proposed CEPIO Operational
Ontology Activation program. It is intentionally *not* an attempt to recreate
Palantir's Ontology Object backend, Ontology Manager, Workshop, or Actions SDK.

Existing CEPIO RDF/OWL, ontology identity, typed objects, relationship
repository, actor-scoped Application Contract, Decisions, Skills and Actions
remain the single semantic/runtime authority. No new canonical ontology class,
API route, MCP tool, database table, infrastructure resource, inference provider
or authority path is introduced.

The reference provides a **local application-level** inspection of one
operational object and its first-hop visible relationships. This is not a
remotely hosted Object Explorer yet.

## Observable behavior

`inspect_operational_object(service, object_id, trusted_context, max_related=25)`

1. Uses `CEPIOApplicationService.read_object` for the subject, including existing
   actor/object/property policy filtering.
2. Resolves inbound and outbound first-hop relationships through the existing
   object repository, validates identity/type consistency, and performs the
   *same actor-scoped read* for every related object.
3. Omits neighbors that the actor is not permitted to read. Hidden object IDs,
   property contents and relationship endpoints are never returned. Related
   output is deterministic and bounded to at most 50 distinct objects.
4. Returns the existing `ContextEnvelope` and small relationship references;
   does **not** return raw link property dictionaries, events, unverified source
   evidence, source credentials or executable capabilities.
5. Marks evidence as `not_attested`, live state as `not_live_qualified` and
   Action capability as `not_evaluated`. A literal `operatingState` property in
   the synthetic fixture is **not** verified current plant condition.
6. Does not call an Industry IQ function, persist a Decision, evaluate authority,
   execute an Action, append an audit entry or mutate source/CEPIO objects.

## Example

From the repository root:

```bash
PYTHONPATH=src python examples/operational_object_k201.py
PYTHONPATH=src pytest -q tests/test_operational_object_inspection_v01.py
```

This loads existing `examples/satorp_hydrocracker.json` synthetic objects
and relationships and inspects `K-201` through the existing application
service. The privileged `cepio_admin` role is **only** a locally supplied
fixture role; it must not be interpreted as authenticated tenant permission.

The resulting payload can be consumed by a future authorized Studio adapter,
but no REST/MCP addition is claimed in this increment.

## Negative controls

Tests prove:

- inaccessible subject is rejected before graph traversal;
- inaccessible related objects, IDs and properties are not serialized;
- property-level allowlists remain in force on the subject and neighbors;
- bounded request parameters fail for invalid sizes;
- no Decision or Action audit is persisted.

## Known non-claims and next qualification gates

This reference is **not production tenant isolation**. `ExecutionContext`
must come from a trusted authenticated host and is not user input. Live
deployment requires independently enforcing the tenant and source-use boundary,
relationship visibility/classification, bounded graph budgets and pagination.

The following remain **unqualified**:

- real SAP/PI/Fabric/engineering source identities and reliable refresh;
- provenance-attested observations, valid/transaction-time operational state,
  conflicting/stale-source handling and source-of-truth reconciliation;
- policy-qualified Action preview and approval obligations;
- distributed PostgreSQL operational projections;
- live remote REST/MCP consumer integration and a Studio object workspace;
- K-201 three-source Decision -> authorized external Action -> source readback ->
  verification/reconciliation -> immutable Outcome.

Those are v0.5 CONNECT proof requirements or later components. This reference
earns **no automatic v1 scorecard points or release advancement**.

## IP / licensing

The public module contains only generic, source-neutral object inspection
behavior. Domain-specific K-201 reasoning, protected evaluation datasets and
customer-licensed engineering parsers remain outside CEPIO Core. No pyDEXPI,
Foundry/Palantir runtime, Azure provisioning or paid inference dependency exists.

## Implementation location

- `src/cepio/operational_object_inspection.py`
- `tests/test_operational_object_inspection_v01.py`
- `examples/operational_object_k201.py`

Next implementation increment: source-attested state/evidence projection over
the same authorized object, not a second semantic store or an unconstrained
agent API.
