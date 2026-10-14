# CEPIO v0.3 — Temporal + Provenance Kernel

**Common Energy & Process Industry Ontology**

> **North Star:** Aim for CEPIO to provide the same enterprise operating abstraction that Palantir’s Ontology provides — specialized for Energy & Process Industries and native to the Microsoft ecosystem.

CEPIO is an **industry operating ontology** for Energy & Process Industries. It provides a canonical, governed abstraction of enterprise objects, relationships, state, time, provenance, logic, decisions and actions so applications and AI agents can **observe, reason, decide and act** without coupling business logic to SAP, AVEVA PI, OSDU, Primavera, Fabric, or another source-system schema.

CEPIO is not intended to replace Microsoft Fabric, Fabric IQ, Microsoft Foundry, Microsoft Purview, Azure App Service, AKS or Entra. It is designed to become the **industrial semantic and operational extension layer across the Microsoft Data + AI platform**.

---

## Status

**Current release: `0.3.0` — Temporal + Provenance Kernel**

v0.3 is implemented on `main` and validated through GitHub Actions.

Validated baseline:

- **36 pytest tests passing**
- SHACL validation conforms
- refinery cross-domain demo executes end-to-end
- package version is `0.3.0`
- SQLite and in-memory reference runtimes supported
- no production-side effects in reference adapters

v0.3 is a **reference operational kernel**, not yet a production distributed graph/control platform.

---

## What is new in v0.3

v0.3 moves CEPIO beyond a semantic graph into a versioned, provenance-aware and temporally reconstructable operating abstraction.

### 1. Canonical industrial modules

CEPIO now contains reusable modules for:

- Asset
- Work Management
- Reliability
- HSE
- Supply
- Performance
- Workforce
- Commercial
- Process Industry
- EPCIC
- Drilling
- Agentic Operations

The goal is to promote reusable industrial semantics into CEPIO while keeping company/project-specific semantics in customer profiles.

### 2. SEO + AD normalization

Two reference ontologies were normalized into CEPIO:

- **SEO** — refinery/petrochemical, operations and EPC
- **AD** — asset-heavy drilling contractor

Coverage:

- **42 / 42 SEO entity types mapped**
- **59 / 59 AD core entity types mapped**
- **967 source-property occurrences classified**

Source fields are intentionally classified rather than blindly copied:

```text
Source field
   │
   ├── Canonical property
   ├── Relationship key
   ├── Observation value
   ├── Observation timestamp
   └── Profile-specific property
```

Foreign keys become relationships, telemetry becomes observations, provenance fields become lineage metadata, and customer-specific semantics remain profile-scoped until reuse justifies promotion.

### 3. IRI-first semantic identity

Full RDF IRIs are now the canonical identity for:

- classes
- relationships
- datatype properties

QName/local-name aliases are accepted only when unambiguous. Ambiguous aliases fail closed.

Example:

```text
https://cepio.org/ontology/industrial#WorkOrder
```

is canonical, while `WorkOrder` is only a convenience alias.

### 4. Versioned ontology-module contract

CEPIO modules now carry:

- namespace
- semantic version
- architecture tier
- stability
- dependencies
- dependency constraints
- compatibility snapshots

Breaking removals or incompatible range changes can therefore be detected as semantic-contract changes.

### 5. Property-level provenance

CEPIO can now explain **why it believes a property value**.

A property value may carry:

```text
Object
  └── canonical property IRI
       └── PropertyProvenance
            ├── source system
            ├── source entity
            ├── source field
            ├── source record
            ├── source-value hash
            ├── mapping version
            ├── transformation run
            ├── observed time
            └── ingestion time
```

Applications and agents can use `explain_property(...)` to retrieve this lineage context.

### 6. Bitemporal object and relationship history

CEPIO now distinguishes:

- **transaction time** — when CEPIO recorded/learned a fact
- **valid time** — when the fact is considered true in the industrial domain

Historical state can be reconstructed without overwriting prior versions.

```python
historical = runtime.get_object_at("K-201", transaction_time)
valid_state = runtime.get_object_valid_at("K-201", valid_time)
relationships = runtime.relationships_at("K-201", valid_time)
```

Retroactive corrections append new history rather than mutating old snapshots.

### 7. Deterministic event → state projection

Operational events can now rebuild derived state deterministically.

Reference implementation:

```text
TripEvent
   ↓
CompressorOperatingStateProjector
   ↓
operatingState = "tripped"
   ↓
RecoveryEvent
   ↓
operatingState = "running"
```

Event ordering is deterministic using `(occurred_at, event_id)`.

Projection checkpoints are stored separately from source events, so derived state can be deleted and rebuilt from immutable history.

---

## CEPIO operating abstraction

CEPIO is intended to model both **what the enterprise is** and **what the enterprise can do**.

```text
                           CEPIO
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
      SEMANTICS            STATE             KINETICS
          │                  │                  │
      Objects              Events             Functions
      Relationships        Time               Decisions
      Properties           History            Actions
      Interfaces           Provenance         Workflows
      Capabilities         Projection         Constraints
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                      Policy + Audit
                             │
                       Apps + Agents
```

The target is for an application or authorized agent to be able to:

1. resolve a real industrial object from a business concept;
2. traverse operational and enterprise relationships;
3. understand current and historical state;
4. explain where data/state came from;
5. invoke governed functions;
6. recommend or execute policy-authorized actions;
7. preserve provenance, audit and version history;
8. interact through stable APIs without knowing source-system schemas.

---

## Microsoft-native architecture

CEPIO is designed as an extension across the Microsoft Data + AI platform, not as a Fabric-only ontology.

```text
                 MICROSOFT DATA + AI PLATFORM
                              │
       ┌──────────────────────┼───────────────────────┐
       │                      │                       │
    DATA PLANE            AI / SEMANTIC           GOVERNANCE
       │                      │                       │
 Fabric / OneLake        Fabric IQ              Purview
 RTI / Eventstreams      Foundry                Data Map
 SQL / Lakehouse         Agents / MCP           Classification
 Warehouse               Ontology / Graph       Lineage
       │                      │                       │
       └──────────────────────┼───────────────────────┘
                              │
                       CEPIO EXTENSION
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
      SEMANTICS            OPERATIONS          GOVERNANCE
         │                    │                    │
   Asset / Process        Event / State        Provenance
   EPCIC / Drilling      Function / Decision  Policy
   Enterprise            Action               Time
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                      APPLICATION RUNTIME
                   ┌──────────┴───────────┐
                   │                      │
             Azure App Service           AKS
              managed PaaS         scaled runtime
                   │                      │
                   └──────────┬───────────┘
                              │
                            ENTRA
                    identity / workload trust
```

### Platform responsibility

| Platform | Primary CEPIO role |
|---|---|
| **Fabric / OneLake / RTI** | enterprise data foundation, analytical/operational data bindings, event streams |
| **Fabric IQ / Ontology / Graph** | primary Microsoft-native semantic materialization of CEPIO concepts and graph relationships |
| **Microsoft Foundry** | agent/model execution using CEPIO grounding, MCP tools, functions and governed actions |
| **Microsoft Purview** | enterprise governance, catalog, classification, Data Map and lineage bridge |
| **Azure App Service** | managed hosting for CEPIO REST/MCP APIs and lightweight applications |
| **Azure Kubernetes Service** | scaled/containerized CEPIO runtime, projectors, adapters and event workers |
| **Microsoft Entra** | identity/workload context feeding CEPIO authorization and policy |

### Constitutional architecture rule

> **Microsoft services may implement CEPIO capabilities, but they do not define CEPIO's industrial semantics.**

The canonical CEPIO contract remains portable and source-system-neutral. Microsoft-specific implementations live in integration/deployment bindings outside CEPIO-Core and the canonical domain modules.

---

## Reference reasoning chain

The v0.3 reference refinery scenario demonstrates the target operating model:

```text
Hydrocracker Margin KPI
        ↓
Hydrocracker Process Unit
        ↓
K-201 Recycle Gas Compressor
        ↓
Trip Events / Historical State
        ↓
Risk + Production-Loss Functions
        ↓
Decision
        ↓
Governed CreateWorkOrder
        ↓
Critical Spare Requirement
        ↓
Inventory Position
        ↓
Supplier
        ↓
Immutable Audit + Provenance
```

The long-term objective is for the same operational abstraction to work across refining, petrochemical, upstream, midstream, drilling, mining, power, utilities and other asset-heavy industries through shared CEPIO modules plus domain/customer extensions.

---

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

---

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

CEPIO can therefore answer not only **what is true**, but also:

- where did it come from?
- what did CEPIO know at time T?
- what was valid in the industrial world at time T?
- which immutable events produced the current operational state?
- what decision/action is permitted to follow?

---

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest -q
PYTHONPATH=src python examples/demo.py
uvicorn cepio.api:app --reload
```

API documentation is available at `/docs`.

### Persistence

```python
from cepio.bootstrap import build_runtime

runtime = build_runtime(sqlite_path="cepio.db")
```

### Temporal query

```python
historical = runtime.get_object_at("K-201", transaction_time)
valid_state = runtime.get_object_valid_at("K-201", valid_time)
relationships = runtime.relationships_at("K-201", valid_time)
```

### Projection replay

```python
from cepio.bootstrap import build_projection_engine
from cepio.projection import CompressorOperatingStateProjector

engine = build_projection_engine(runtime)
checkpoint = engine.rebuild("K-201", CompressorOperatingStateProjector())
```

---

## Security invariant

Being able to reason about an action does **not** imply permission to execute it.

An AI recommender can be authorized to:

```text
read ontology objects       ✓
read permitted properties  ✓
traverse relationships      ✓
call functions              ✓
recommend an action         ✓
execute governed action     ✗
```

Execution requires an explicitly authorized human/system identity through CEPIO policy.

---

## Repository structure

```text
ontologies/        canonical OWL/RDF modules
mappings/          canonical property vocabulary + SEO/AD mappings
shapes/            SHACL constraints
src/cepio/         runtime, temporal/provenance kernels, policy, MCP, SDK
integrations/      source/platform bindings as they are implemented
actions/           declarative action definitions
policies/          object/property/action authorization examples
examples/          refinery reference graph and demo
tests/             semantic, temporal, persistence, security and kinetic tests
docs/              architecture, ADRs, normalization and roadmap
AGENTS.md           Codex engineering brief for the next release
```

---

## What v0.3 is not

v0.3 is not yet:

- a production distributed graph platform;
- a full enterprise workflow engine;
- a live plant-control system;
- a production Fabric IQ deployment;
- a production Foundry agent integration;
- a Purview production lineage bridge;
- an App Service/AKS production deployment package;
- a live SAP / AVEVA PI / OSDU writeback implementation.

SQLite remains the reference persistence backend and external adapters remain dry-run/reference contracts.

---

## v0.4 direction — Operational Query + Microsoft Platform Integration

The next release focuses on making v0.3 usable as a Microsoft-native operational platform extension:

### P0

- typed object/relationship/temporal query contract
- Fabric + Fabric IQ semantic binding
- Foundry agent + CEPIO MCP binding

### P1

- ontology migration manifests and CI compatibility gates
- Purview governance + lineage bridge
- App Service + AKS deployment profiles
- structured observability / OpenTelemetry hooks

The goal is to keep the same CEPIO runtime and semantic contract deployable locally, in Microsoft managed services, or in Kubernetes without embedding platform-specific semantics into the canonical ontology.

---

## Design principle

CEPIO is not another data platform, graph database or agent framework.

It is intended to provide the **industrial operating abstraction** that connects enterprise data, semantics, state, AI reasoning and governed action:

```text
Enterprise reality
       ↕
      CEPIO
       ↕
Microsoft Data + AI platform
       ↕
Apps / Agents / Operations
```
