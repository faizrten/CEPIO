# CEPIO v0.3 — Temporal + Provenance Kernel

**Common Energy & Process Industry Ontology** is an operational ontology runtime for Energy & Process Industries.

CEPIO is designed around a single architectural principle: the ontology must be the governed operating abstraction through which applications and AI agents can **observe, reason, decide and act** — without coupling business logic to SAP, AVEVA PI, OSDU, Primavera, Fabric or another source-system schema.

## What v0.3 adds

v0.3 extends the v0.2 operational kernel with a governed semantic contract, normalized industry modules, provenance, temporal history and deterministic state reconstruction:

- canonical CEPIO modules for Asset, Work Management, Reliability, HSE, Supply, Performance, Workforce, Commercial, Process Industry, EPCIC, Drilling and Agentic Operations;
- SEO/SATORP and AD/ARO normalization into canonical CEPIO semantics rather than customer-specific namespaces;
- 42 SEO entities and 59 AD core entities mapped;
- 967 SEO/AD source-property occurrences classified into canonical properties, relationship keys, observations or profile semantics;
- IRI-first identity for classes, relationships and datatype properties with ambiguity failing closed;
- semantic module versions, namespaces, dependencies and compatibility snapshots;
- canonical property registry with datatype and semantic/write authority;
- property-level provenance using source references, transformation runs, source-value hashes and lineage explanation;
- immutable object version history with transaction-time reconstruction;
- object valid-time queries with optional transaction-time "as known then" views;
- relationship revision history and bitemporal relationship queries;
- deterministic event ordering and replay;
- reference compressor operating-state projector;
- separate projection checkpoints so derived state can be deleted and rebuilt from immutable source events;
- reference SQLite persistence for provenance, history and projection checkpoints;
- all v0.2 action, policy, idempotency, audit, function, MCP and adapter boundaries preserved.

## Five-plane architecture

```text
Applications / Copilots / Agents / Autonomous Systems
                       │
                 Experience Plane
                       │
Actions · Functions · Decisions · Rules · Preconditions
                       │
                   Kinetic Plane
                       │
Objects · Relationships · Events · State · KPI · Interfaces
                       │
                  Semantic Plane
                       │
Policy · Versioning · Audit · Provenance · Authorization · Time
                       │
                 Governance Plane
                       │
SAP · PI/AVEVA · OSDU · P6 · Fabric/OneLake · other adapters
                       │
                Integration Plane
```

## Canonical contract

```text
Module
  └─ Type / Relationship / Datatype Property
         └─ Source Mapping
                └─ Provenance
                       └─ Temporal State
                              └─ Event Projection
                                     └─ Function / Decision / Action
```

CEPIO can therefore answer not only **what is true**, but also **where it came from, what CEPIO knew at time T, what was valid in the industrial world at time T, and which events produced the current operational state**.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest -q
PYTHONPATH=src python examples/demo.py
uvicorn cepio.api:app --reload
```

The API documentation is then available at `/docs`.

## Persistence example

```python
from cepio.bootstrap import build_runtime

runtime = build_runtime(sqlite_path="cepio.db")
```

The same runtime contracts are used whether the backend is in-memory or SQLite.

## Temporal example

```python
historical = runtime.get_object_at("K-201", transaction_time)
valid_state = runtime.get_object_valid_at("K-201", valid_time)
relationships = runtime.relationships_at("K-201", valid_time)
```

Transaction time means **when CEPIO recorded the fact**. Valid time means **when the fact is considered true in the industrial domain**.

## Projection example

```python
from cepio.bootstrap import build_projection_engine
from cepio.projection import CompressorOperatingStateProjector

engine = build_projection_engine(runtime)
checkpoint = engine.rebuild("K-201", CompressorOperatingStateProjector())
```

Projection checkpoints are independent of source events; derived state can be cleared and rebuilt without mutating the event history.

## Security invariant

Being able to reason about an action does **not** imply permission to execute it. An `ai_agent_recommender` may receive only authorized properties and can recommend maintenance actions, while execution remains denied unless an authorized identity crosses the policy boundary.

## Repository structure

- `ontologies/` — modular OWL/RDF semantic definitions
- `mappings/` — canonical property vocabulary plus SEO/AD normalization artifacts
- `shapes/` — SHACL constraints
- `src/cepio/` — runtime, temporal/provenance kernels, repositories, policy, MCP facade, SDK and adapters
- `actions/` — declarative action definitions
- `policies/` — role/object/property/action examples
- `examples/` — refinery reference graph and executable demo
- `tests/` — semantic, temporal, persistence, policy, kinetic and adapter tests
- `docs/` — architecture, normalization, temporal semantics, benchmark, ADRs and roadmap
- `AGENTS.md` — Codex engineering brief for the next release

## What v0.3 is not

v0.3 is still a reference operational kernel, not yet a production distributed graph platform, enterprise workflow engine or live plant-control system. SQLite remains the reference persistence backend, external adapters are dry-run only, and production Microsoft/Fabric/Foundry integrations remain explicit follow-on work.
