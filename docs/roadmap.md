# CEPIO Execution Roadmap

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and native to the Microsoft ecosystem.**

CEPIO owns the canonical industrial semantic and operational contract. Microsoft services provide the data, semantic materialization, AI, governance, application hosting and infrastructure planes on which that contract is realized.

`CEPIO semantic contract -> Microsoft platform bindings -> customer deployment`

---

## Completed — v0.1 Semantic Scaffold

**Outcome:** establish the common ontology foundation.

- modular CEPIO Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology;
- object, relationship, event and function concepts;
- in-memory graph traversal;
- initial actions and policy roles;
- FastAPI scaffold and refinery sample.

---

## Completed — v0.2 Operational Kernel

**Outcome:** move from ontology vocabulary to an executable operational runtime.

- persistent repository abstractions and SQLite backend;
- optimistic object concurrency;
- immutable action audit;
- secure idempotency;
- RDF-driven type registry and relationship validation;
- policy-engine interface with object/property/action controls;
- action preconditions and approval metadata;
- Decision records;
- typed function inputs;
- inverse/multi-hop traversal;
- Python SDK and MCP-ready facade;
- dry-run SAP, AVEVA PI, OSDU, P6 and Fabric contracts;
- SHACL validation path;
- executable KPI -> asset -> event -> decision -> work-order -> spare demo.

---

## Completed — v0.3 Temporal + Provenance Kernel

**Outcome:** CEPIO can explain what an industrial object means, where its values came from, what was true at time T, what CEPIO knew at time T, and which immutable events produced derived operational state.

### Canonical industrial model
- common modules for Asset, Work Management, Reliability, HSE, Supply, Performance, Workforce, Commercial and Agentic Operations;
- domain modules for Process Industry, EPCIC and Drilling;
- SEO refinery/petrochemical + EPC ontology normalized into CEPIO;
- AD asset-heavy/drilling ontology normalized into CEPIO;
- 42/42 SEO entities and 59/59 AD core entities mapped;
- 967 source-property occurrences classified into canonical properties, relationship keys, observations, provenance or profile-specific semantics.

### Semantic contract
- IRI-first identity for classes, relationships and datatype properties;
- fail-closed alias ambiguity;
- semantic module namespaces, versions and dependencies;
- compatibility snapshots for classes, relationships and properties;
- canonical property registry with datatype and authority metadata.

### Provenance + time
- SourceReference, TransformationRun and PropertyProvenance contracts;
- property-level lineage explanations;
- immutable object version history;
- transaction-time reconstruction;
- valid-time queries and bitemporal object views;
- immutable relationship revision history;
- bitemporal graph queries.

### Event -> state
- deterministic ordering `(occurred_at, event_id)`;
- replayable projection contract;
- compressor operating-state reference projector;
- independent projection checkpoints;
- delete/rebuild derived state from immutable source events.

### Platform positioning
- CEPIO established as a Microsoft Data + AI platform extension across Fabric, Fabric IQ, Foundry, Purview, App Service, AKS and Entra;
- Microsoft services may implement CEPIO capabilities, but they do not define CEPIO industrial semantics.

**Gate achieved:** CEPIO can answer: `what is true -> where did it come from -> what was true/known at time T -> what events caused the state -> what governed action can follow?`

---

# Current — v0.4 Microsoft Platform Extension

**Outcome:** make CEPIO natively consumable across the Microsoft Data + AI platform while preserving a portable, source-system-neutral canonical contract.

## P0 — Operational query contract

Tracked by **#5**.

- typed query model for object type, property predicates, relationships, pagination and time;
- current-state and point-in-time queries;
- repository-neutral query API;
- FastAPI + Python SDK exposure;
- no premature CEPIO-specific textual query language.

## P0 — Fabric + Fabric IQ semantic binding

Tracked by **#18**.

- deterministic CEPIO -> Fabric IQ binding manifest;
- map CEPIO classes, properties and relationships to Fabric IQ ontology constructs;
- preserve canonical CEPIO IRI + module version metadata;
- bind Fabric Lakehouse / Warehouse / SQL / Real-Time Intelligence sources where appropriate;
- graph/GQL mapping where appropriate;
- drift detection between CEPIO canonical contract and deployed Fabric IQ representation;
- offline validation without Fabric credentials.

## P0 — Foundry + MCP agent binding

Tracked by **#19**.

- expose CEPIO query, temporal, provenance, function and action surfaces as MCP-compatible tools;
- Foundry tool/toolbox registration contract;
- Entra/Foundry identity -> CEPIO actor context;
- separate recommend-action from execute-action permissions;
- agent-facing lineage and state explanation tools;
- no agent bypass of CEPIO policy or source adapters.

## P1 — Ontology lifecycle + migration manifests

Tracked by **#4**.

- complete migration-manifest format;
- CI gate for intentional breaking semantic changes;
- executable/reviewable module migration contracts;
- preserve additive compatibility by default.

## P1 — Runtime observability

Tracked by **#6**.

- structured events for query, repository, function, policy, action and adapter execution;
- latency / success / failure metrics;
- OpenTelemetry-compatible hook boundary;
- no unauthorized industrial data in telemetry payloads.

## P1 — Purview governance + lineage bridge

Tracked by **#20**.

- Purview/Data Map asset -> CEPIO SourceReference mapping;
- governance/classification/domain metadata in CEPIO explanation context;
- CEPIO transformation -> Purview lineage publication artifact;
- preserve CEPIO runtime provenance as the operationally precise lineage layer;
- governance metadata must not bypass CEPIO authorization.

## P1 — App Service + AKS deployment profiles

Tracked by **#21**.

### App Service
- CEPIO REST/MCP APIs and lightweight domain apps;
- managed identity / Entra;
- VNet/private connectivity;
- health, slots, autoscale and telemetry patterns.

### AKS
- scale-out CEPIO runtime, adapters, projectors and event workers;
- Entra Workload Identity;
- private networking and Key Vault/secretless patterns;
- probes, autoscaling, workload isolation and auditable rollout.

## v0.4 gate

A Microsoft-native reference deployment must demonstrate:

1. CEPIO canonical semantics materialized through a Fabric/Fabric IQ binding;
2. a Foundry agent querying CEPIO through MCP without bypassing CEPIO policy;
3. provenance linked to Purview governance identity;
4. the same CEPIO runtime deployable through an App Service or AKS reference profile;
5. all CEPIO core tests remaining cloud-independent and executable offline.

---

# Next — v0.5 Live Industrial Integration

**Outcome:** prove that CEPIO abstracts real industrial source systems and closes the governed writeback loop.

- SAP S/4HANA / EAM production-grade adapter;
- AVEVA PI / historian streaming adapter;
- OSDU upstream adapter and semantic mapping;
- Primavera P6 schedule adapter;
- Fabric/OneLake operational materialization where required;
- real-time event ingestion and reconciliation;
- governed writeback with explicit external acknowledgement;
- retry, dead-letter and reconciliation handling;
- secrets/configuration boundary and environment isolation;
- customer/source identity resolution.

**Gate:** one CEPIO application traverses at least three live enterprise sources and performs one governed, auditable and reconciled enterprise writeback.

---

# Later — v0.6 Reference Industrial Applications

**Outcome:** prove measurable operating value rather than semantic elegance.

## Asset Reliability
- condition -> risk -> failure mode -> work -> spare -> action;
- maintenance decision and outcome feedback loop.

## Refinery Margin Optimization
- margin KPI -> process unit -> constraint/event -> operating decision -> financial impact;
- connect process, reliability and finance semantics.

## Turnaround Planning
- scope -> asset/work package -> materials -> workforce -> schedule -> risk;
- multi-agent planning and governed human approvals.

**Gate:** at least one reference application demonstrates measurable business impact with a complete observe -> reason -> decide -> authorize -> act -> learn loop.

---

# v1.0 Platformization

**Outcome:** CEPIO becomes an adoptable industrial operating ontology platform rather than a reference implementation.

- production graph/search backend;
- generated SDKs for Python, .NET and TypeScript;
- production MCP server and governed tool registry;
- ontology/module package registry;
- visual ontology / mapping / workflow studio;
- multi-tenancy and namespace governance;
- performance benchmark and SLO program;
- deployment automation and upgrade tooling;
- partner extension/certification model;
- standards mapping packs for OSDU, ISO 15926, CFIHOS, ISA-95, FIBO, DEXPI and IFC;
- customer profile packaging and compatibility certification.

**Gate:** a second enterprise can adopt CEPIO primarily through mapping, configuration and approved extensions rather than redesigning the ontology/runtime.

---

## Project-board view

### DONE
- v0.1 Semantic Scaffold
- v0.2 Operational Kernel
- v0.3 Temporal + Provenance Kernel
- SEO/AD domain normalization
- IRI-first semantic identity
- property provenance
- bitemporal object/relationship history
- deterministic event/state projection
- Microsoft platform extension architecture

### NOW — v0.4 P0
- #5 Typed query + temporal filter contract
- #18 Fabric + Fabric IQ semantic binding
- #19 Foundry + CEPIO MCP binding

### NEXT — v0.4 P1
- #4 Migration manifests / ontology lifecycle
- #6 Runtime observability / OpenTelemetry
- #20 Purview governance + lineage bridge
- #21 App Service + AKS deployment profiles

### LATER
- v0.5 Live Industrial Integration
- v0.6 Reference Industrial Applications
- v1.0 Platformization
