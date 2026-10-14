# CEPIO

**Common Energy & Process Industry Ontology**

> **An industry operating ontology for Energy & Process Industries — connecting enterprise data, operational state, industrial semantics, AI reasoning and governed action.**

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and natively realized across the Microsoft ecosystem.**

CEPIO provides a canonical model of industrial **objects, relationships, state, time, provenance, logic, decisions and governed actions**.

The intended operating loop is:

```text
Observe -> Understand -> Reason -> Decide -> Recommend -> Authorize -> Act -> Observe outcome
```

Applications and AI agents should be able to operate on the enterprise without embedding business logic directly into SAP, AVEVA PI, OSDU, Primavera P6, Fabric tables, SQL schemas or another source-system representation.

---

## What CEPIO is

CEPIO is an **industrial operating abstraction** between enterprise systems and the applications, agents and workflows that consume them.

```text
Enterprise reality
        |
        v
Source systems
SAP · PI · OSDU · P6 · MES · Fabric · SQL
        |
        v
      CEPIO
+--------------------------------+
| Objects                        |
| Relationships                  |
| Properties                     |
| Events + State                 |
| Valid time + Transaction time  |
| Provenance                     |
| Functions                      |
| Decisions                      |
| Actions                        |
| Policies                       |
| Migration contracts            |
+---------------+----------------+
                |
       +--------+--------+
       v                 v
     Apps              Agents
       |                 |
       +--------+--------+
                v
       Governed operations
```

CEPIO is designed to answer questions such as:

- What industrial object does this data represent?
- How is that object related to the rest of the enterprise?
- What is its current state?
- What was its state at a particular point in time?
- What did CEPIO know at that point in time?
- Where did a particular value come from?
- Which events produced the current state?
- What function or calculation can be applied?
- What decision follows from the evidence?
- What action is recommended?
- Who or what is authorized to execute it?
- How does the ontology evolve without silently breaking applications?

CEPIO is **not** another data lake, graph database product, generic RDF/OWL standards project, agent framework, or plant-control system. CEPIO defines the industrial meaning and operating contract; platforms implement it.

---

## Architecture principle

CEPIO separates three concerns:

```text
1. CEPIO Canonical Model
   What an industrial enterprise means
            |
            v
2. Platform Bindings
   How CEPIO is realized on technology platforms
            |
            v
3. Customer Profiles
   How a particular enterprise operates
```

> **Microsoft services may implement CEPIO capabilities, but they do not define CEPIO's industrial semantics.**

Likewise, SAP schemas, PI tags, Fabric tables, OSDU objects and customer-specific data models may map into CEPIO without becoming the canonical CEPIO model by default.

---

## Current status

### Released package

Current Python package version: **`0.3.0`**.

The v0.3 release established the **Temporal + Provenance Kernel**.

### Current `main`

`main` has advanced beyond the packaged v0.3 release and now contains the major foundations of the **v0.4 Microsoft Platform Extension**.

Implemented capabilities include:

- canonical modular industrial ontology;
- IRI-first semantic identity;
- canonical property contract and property-level provenance;
- bitemporal object and relationship history;
- deterministic event -> state projection;
- typed operational object-set query contract;
- NetworkX graph analytics with optional NVIDIA cuGraph acceleration;
- Digital Twin Consortium ISA-95 manufacturing federation;
- Microsoft Fabric / Fabric IQ semantic binding;
- Microsoft Foundry + governed CEPIO MCP integration;
- Entra identity -> CEPIO actor context;
- explicit function/action authorization;
- ontology migration manifests and CI semantic compatibility gates.

Current CI validates:

```text
pytest
ontology compatibility
SHACL / ontology validation
reference refinery demo
```

`main` is the authoritative stable development line.

---

## CEPIO operating model

CEPIO combines semantics, operational state and kinetics:

```text
                           CEPIO
                             |
          +------------------+------------------+
          |                  |                  |
      SEMANTICS            STATE             KINETICS
          |                  |                  |
      Objects              Events             Functions
      Relationships        Time               Decisions
      Properties           History            Actions
      Interfaces           Provenance         Workflows
      Capabilities         Projection         Constraints
          |                  |                  |
          +------------------+------------------+
                             |
                      Policy + Audit
                             |
                       Apps + Agents
```

The ontology models both **what the enterprise is** and **what the enterprise can do**.

---

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

---

## Canonical industrial model

CEPIO uses reusable modules rather than one monolithic ontology.

### Foundation

`core`, `lifecycle`, `kinetic`

### Industrial common

`industrial`, `asset`, `work_management`, `reliability`, `hse`, `supply`, `performance`, `workforce`, `agentic_operations`

### Industry domains

`energy`, `process_industry`, `manufacturing`, `epcic`, `drilling`

### Enterprise

`enterprise`, `commercial`

Typical CEPIO primitives include:

```text
Entity · Asset · Activity · Event · State · Party · Organization
Location · Material · Resource · Measurement · KPI · Risk
Objective · Capability · Process · Document · Contract
WorkItem · Decision · Action
```

The Operational Asset is an important semantic pivot connecting process, reliability, maintenance, supply, workforce, risk and financial consequences.

Example:

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

---

## IRI-first identity

Full RDF IRIs are the canonical identity for classes, relationships and datatype properties.

```text
https://cepio.org/ontology/industrial#WorkOrder
```

QName and local-name forms such as `industrial:WorkOrder` and `WorkOrder` are convenience aliases only. Ambiguous aliases fail closed.

---

## Property contract and provenance

A source field is classified rather than copied blindly into the ontology:

```text
Source field
   |
   +-- Canonical property
   +-- Relationship
   +-- Observation value
   +-- Observation timestamp
   +-- Provenance metadata
   +-- Customer/profile-specific property
```

CEPIO can explain **why it believes a value** through `PropertyProvenance`, including source system, source entity/field/record, source-value hash, mapping version, transformation run, observed time and ingestion time.

---

## Time and state

CEPIO distinguishes:

- **valid time** — when a fact is true in the industrial domain;
- **transaction time** — when CEPIO recorded or learned that fact.

This enables CEPIO to distinguish "what was actually true at time T?" from "what did CEPIO believe at time T?".

```python
historical = runtime.get_object_at("K-201", transaction_time)
valid_state = runtime.get_object_valid_at("K-201", valid_time)
relationships = runtime.relationships_at("K-201", valid_time)
```

Operational state can also be rebuilt deterministically from immutable events.

```text
TripEvent
   -> CompressorOperatingStateProjector
   -> operatingState = "tripped"
   -> RecoveryEvent
   -> operatingState = "running"
```

Event ordering is deterministic using `(occurred_at, event_id)`.

---

## Typed operational query

CEPIO provides a structured query contract over the canonical model. Consumers do not need to know SQLite, RDF, Fabric or source-system schemas.

The contract supports:

- object type + subtype matching;
- typed property predicates;
- relationship constraints;
- valid-time and transaction-time context;
- deterministic sorting;
- pagination.

The query contract is backend-neutral so the same application semantics can be translated into future Fabric, graph or production data stores.

---

## Graph Intelligence

CEPIO includes backend-neutral graph analytics using NetworkX as the CPU/reference implementation and optional RAPIDS `nx-cugraph` acceleration.

Supported analysis includes:

- PageRank;
- degree centrality;
- betweenness centrality;
- eigenvector centrality;
- Louvain communities;
- dependency traversal and blast radius.

NVIDIA is an optional acceleration plane; CEPIO owns the graph semantics.

---

## Manufacturing + ISA-95

CEPIO federates the Digital Twin Consortium `ManufacturingOntologies` corpus as an external ISA-95 / IEC 62264 semantic source.

Coverage includes equipment, materials, personnel, physical assets, operations definitions, capabilities, schedules, requests/responses, manufacturing performance, tests, workflow specifications and resource networks.

Shared concepts converge onto existing CEPIO semantics:

```text
DTC / ISA-95              CEPIO
---------------------------------------------
Equipment              -> industrial:Equipment
PhysicalAsset          -> core:PhysicalAsset
Person                 -> core:Person
MaterialRequirement    -> supply:MaterialRequirement
```

Manufacturing-specific concepts live under:

```text
https://cepio.org/ontology/manufacturing#
```

See `docs/standards/dtc-isa95-manufacturing.md` and `THIRD_PARTY_NOTICES.md`.

---

## Standards federation

CEPIO is designed to federate relevant industry standards rather than recreate them. Current or targeted references include:

`OSDU`, `ISA-95 / IEC 62264`, `ISO 15926`, `CFIHOS`, `DEXPI`, `BIM / IFC`, and selective `FIBO` concepts where appropriate.

> **Reuse reference semantics where they are strong; retain CEPIO as the operating abstraction that connects those semantics across the enterprise.**

---

## Microsoft-native architecture

CEPIO is a Microsoft Data + AI platform extension while preserving a portable canonical contract.

```text
                    MICROSOFT DATA + AI
                            |
            +---------------+---------------+
            |               |               |
          DATA           AI / AGENTS     IDENTITY
            |               |               |
     Fabric / OneLake    Foundry           Entra
     Warehouse           Agents
     Lakehouse           MCP
     Eventhouse
            |               |
            +-------+-------+
                    |
                    v
                   CEPIO
      +-----------------------------+
      | Objects                     |
      | Relationships               |
      | State + Time                |
      | Provenance                  |
      | Functions                   |
      | Decisions                   |
      | Governed Actions            |
      | Policy                      |
      +--------------+--------------+
                     |
             Application runtime
```

### Platform responsibility

| Platform | CEPIO role |
|---|---|
| **Fabric / OneLake / RTI** | enterprise data foundation and operational/analytical source bindings |
| **Fabric IQ / Ontology / Graph** | Microsoft-native materialization of CEPIO semantic objects and relationships |
| **Microsoft Foundry** | model and agent execution grounded through CEPIO tools |
| **Microsoft Entra** | authenticated human, application and agent identity |
| **Azure App Service** | planned managed hosting profile for CEPIO REST/MCP APIs |
| **AKS** | planned scaled/containerized runtime profile |
| **Purview** | deferred enterprise governance/catalog/lineage bridge |

---

## Fabric + Fabric IQ binding

CEPIO can generate a Microsoft-native semantic deployment bundle while remaining the canonical authority:

```text
CEPIO canonical modules
          |
          v
FabricIQBindingGenerator
          |
     +----+----+
     v         v
ontology.ttl   binding-manifest.json
     |         |
     +----+----+
          v
      Fabric IQ
       Ontology
```

The sidecar manifest preserves canonical IRIs, module ownership/versions, source mappings, entity keys, contract hashes and Graph eligibility.

Reference source types include Lakehouse, Warehouse, Eventhouse/KQL, SQL Database, Mirrored Database and Semantic Model.

---

## Foundry + governed MCP

CEPIO exposes seven governed MCP tools for Microsoft Foundry agents:

```text
cepio_get_object
cepio_query_objects
cepio_get_state_at
cepio_explain_property
cepio_call_function
cepio_recommend_action
cepio_execute_action
```

Identity is injected from the authenticated hosting context; actor ID and roles are not model-callable MCP arguments.

```text
Microsoft Foundry Agent
          |
          | authenticated identity
          v
     CEPIO MCP Gateway
          |
          +-- read policy
          +-- property filtering
          +-- function authorization
          +-- action policy
          +-- preconditions
          +-- audit
          |
          v
      CEPIO Runtime
```

Recommendation is intentionally separate from execution. An AI agent may be allowed to inspect evidence and recommend an action while remaining unable to execute that action.

---

## Ontology lifecycle and compatibility

CEPIO ontology definitions are treated as **versioned production contracts**.

CI compares the current ontology against an explicitly accepted baseline and detects changes to modules, namespaces, classes, relationships, datatype properties, subclass structures, domains, ranges and datatype ranges.

Policy:

```text
Additive semantic change
-> patch or higher version bump

Breaking change for pre-1.0 module
-> minor or major bump + explicit migration manifest

Breaking change for 1.x+ module
-> major bump + explicit migration manifest
```

Undeclared breaking changes fail CI. Stale or duplicate migration declarations also fail.

Example migration manifest:

```yaml
schema_version: '1'
id: replace-old-equipment
from_ref: <accepted-baseline>
description: Replace deprecated equipment semantic.
issue: '#123'
changes:
  - change: class_removed:industrial:https://cepio.org/ontology/industrial#OldEquipment
    rationale: OldEquipment duplicates the canonical Equipment contract.
    strategy: deprecate-then-remove
    replacement: https://cepio.org/ontology/industrial#Equipment
```

Supported strategies include `alias`, `rewrite`, `dual-read`, `deprecate-then-remove`, `manual` and `no-data-impact`.

---

## Reference industrial reasoning chain

The refinery reference scenario demonstrates how CEPIO domains connect:

```text
Hydrocracker Margin KPI
        -> Hydrocracker Process Unit
        -> K-201 Recycle Gas Compressor
        -> Trip Event
        -> Historical State
        -> Risk / Production-Loss Function
        -> Decision
        -> Governed CreateWorkOrder
        -> Critical Spare
        -> Inventory
        -> Supplier
        -> Audit + Provenance
```

The same operating abstraction is intended to extend across refining, petrochemicals, upstream, midstream, drilling, manufacturing, mining, power, utilities and EPCIC through shared modules plus domain/customer extensions.

---

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO

python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python examples/demo.py
```

Start the API:

```bash
uvicorn cepio.api:app --reload
```

Open `http://localhost:8000/docs`.

### Persistence

```python
from cepio.bootstrap import build_runtime
runtime = build_runtime(sqlite_path="cepio.db")
```

SQLite and in-memory repositories remain reference implementations rather than the final distributed enterprise runtime.

### MCP

```bash
python -m pip install -e '.[mcp]'
```

Reference server: `examples/foundry_mcp_server.py`

Foundry deployment contract: `deployments/foundry/`

### NVIDIA graph acceleration

Optional RAPIDS profiles are under `deploy/nvidia/`. CEPIO does not require an NVIDIA runtime for normal development, testing or deployment.

---

## Repository structure

```text
ontologies/                     canonical CEPIO RDF/OWL modules
ontology-modules.yaml           module catalogue, versions and dependencies
mappings/                       source mappings + canonical property contract
shapes/                         SHACL validation contracts
src/cepio/                      runtime, query, temporal, provenance, graph, policy, SDK
src/cepio/integrations/microsoft/
                                Fabric IQ + Foundry/MCP bindings
integrations/                   deployment/source binding manifests
compatibility/                  accepted baseline + migration manifests
actions/                        declarative actions
policies/                       authorization examples
deploy/                         optional runtime profiles
deployments/                    platform deployment artifacts
examples/                       refinery reference data and demos
tests/                          semantic/runtime/platform/compatibility tests
docs/                           architecture, standards, roadmap and ADRs
THIRD_PARTY_NOTICES.md          external attribution
```

---

## Development workflow

CEPIO follows a trunk-oriented model:

```text
main
 |
 +-- feature/*
       |
       +-- Pull Request
             |
             +-- pytest
             +-- ontology compatibility
             +-- SHACL validation
             +-- reference demo
             |
             +-- successful merge -> main
```

Feature branches should be short-lived and deleted after successful merge. Important, validated features should not remain indefinitely outside `main`.

---

## Roadmap

### Completed foundations

- **v0.1 Semantic Scaffold** — initial modular ontology architecture.
- **v0.2 Operational Kernel** — persistence, policy, decisions, actions, audit and SDK foundations.
- **v0.3 Temporal + Provenance Kernel** — provenance, bitemporal history and deterministic event-state reconstruction.

### Current — v0.4 Microsoft Platform Extension

Completed on `main`:

```text
[x] Typed operational query
[x] Microsoft platform architecture
[x] Fabric / Fabric IQ semantic binding
[x] Foundry / MCP binding
[x] Ontology migration + compatibility gates
```

Current priorities:

```text
[ ] App Service + AKS reference deployment
[ ] Runtime observability / OpenTelemetry
```

Deferred / non-blocking:

```text
[ ] Purview governance + lineage bridge
```

### v0.5 Live Industrial Integration

Target production-grade integration with SAP, AVEVA PI, OSDU, Primavera P6, real-time reconciliation and governed writeback.

### v0.6 Reference Industrial Applications

Target applications include Asset Reliability, Refinery Margin Optimization and Turnaround Planning.

### Later platformization

SDK maturity, CLI and registry tooling, production persistence, scale/HA, security hardening, multi-tenancy, deployment automation, visual studio tooling and repeatable second-enterprise adoption.

---

## Design philosophy

CEPIO is not intended to become a large collection of disconnected ontology classes.

Its purpose is to create an **operational model of the enterprise**:

```text
enterprise evidence
       |
       v
industrial meaning
       |
       v
operational state
       |
       v
reasoning
       |
       v
decision
       |
       v
authorized action
```

Industrial enterprises already have enormous amounts of data. The harder problem is connecting that data to **meaning, context, state, decisions and action**.

```text
DATA
  +
SEMANTICS
  +
TIME
  +
PROVENANCE
  +
REASONING
  +
GOVERNED ACTION
  =
INDUSTRIAL OPERATING ABSTRACTION
```

That is the direction of CEPIO.
