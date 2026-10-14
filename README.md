# CEPIO v0.2 — Operational Kernel

**Common Energy & Process Industry Ontology** is an operational ontology runtime for Energy & Process Industries.

CEPIO is designed around a single architectural principle: the ontology must be the governed operating abstraction through which applications and AI agents can **observe, reason, decide and act** — without coupling business logic to SAP, AVEVA PI, OSDU, Primavera, Fabric or another source-system schema.

## What v0.2 adds

v0.2 upgrades the v0.1 semantic scaffold into an executable operational kernel:

- repository contracts for objects, relationships, events, audit and decisions;
- reference **SQLite persistence** plus in-memory repository;
- **optimistic concurrency** on ontology objects;
- immutable audit records for action attempts;
- actor/action/target-scoped **idempotency**;
- ontology type registry with subclass reasoning and relationship domain/range enforcement;
- action preconditions and human-approval metadata;
- replaceable policy-engine interface with object, property and action controls;
- agent `recommend-but-not-execute` security pattern;
- persisted `Decision` records connecting observation → recommendation → action → outcome;
- typed function inputs;
- multi-hop graph traversal including inverse relationships;
- thin typed Python SDK;
- MCP-ready governed tool facade;
- dry-run integration contracts for SAP S/4HANA/EAM, AVEVA PI, OSDU, Primavera P6 and Fabric/OneLake;
- SHACL validation path with pySHACL in full environments and an offline bootstrap validator;
- cross-domain refinery demo: KPI → process unit → compressor → events → decision → work order → spare → supplier.

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
Policy · Versioning · Audit · Provenance · Authorization
                       │
                 Governance Plane
                       │
SAP · PI/AVEVA · OSDU · P6 · Fabric/OneLake · other adapters
                       │
                Integration Plane
```

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

## Security invariant

Being able to reason about an action does **not** imply permission to execute it. An `ai_agent_recommender` may receive only authorized properties and can recommend maintenance actions, while execution remains denied unless an authorized identity crosses the policy boundary.

## Repository structure

- `ontologies/` — modular OWL/RDF semantic definitions
- `shapes/` — SHACL constraints
- `src/cepio/` — runtime, repositories, policy, MCP facade, SDK and adapters
- `actions/` — declarative action definitions
- `policies/` — role/object/property/action examples
- `examples/` — refinery reference graph and executable demo
- `tests/` — semantic, persistence, policy, kinetic and adapter tests
- `docs/` — architecture, benchmark, ADRs and roadmap
- `AGENTS.md` — Codex engineering brief for the next release

## What v0.2 is not

v0.2 is not yet a production distributed graph platform, workflow engine, enterprise identity implementation or live SAP/PI/OSDU integration. The core boundaries are deliberately stable so those capabilities can be added without contaminating CEPIO domain semantics.
