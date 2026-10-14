# CEPIO Execution Roadmap

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and native to the Microsoft ecosystem.**

CEPIO owns the canonical industrial semantic and operational contract. Microsoft services provide the data, semantic materialization, AI, application hosting and infrastructure planes on which that contract is realized.

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

**Gate achieved:** CEPIO can answer `what is true -> where did it come from -> what was true/known at time T -> what events caused the state -> what governed action can follow?`

---

# Current — v0.4 Microsoft Platform Extension

**Outcome:** make CEPIO natively consumable across the Microsoft Data + AI platform while preserving a portable, source-system-neutral canonical contract.

## Completed P0

### #5 — Typed operational query contract ✓

- typed object type/subtype queries;
- property predicates;
- relationship constraints;
- valid-time and transaction-time filters;
- deterministic sorting and pagination;
- in-memory and SQLite parity;
- FastAPI and Python SDK exposure.

### #7 — Microsoft platform extension architecture ✓

- CEPIO established as the canonical industrial semantic/operational contract;
- Microsoft services implement CEPIO capabilities without defining CEPIO industrial semantics;
- durable boundaries for Fabric, Fabric IQ, Foundry, Entra, App Service, AKS and optional Purview integration.

### #18 — Fabric + Fabric IQ semantic binding ✓

- deterministic CEPIO -> Fabric IQ binding manifest;
- importable ontology TTL generation;
- canonical IRI + module/version preservation;
- Lakehouse, Warehouse, Eventhouse/KQL, SQL, mirrored DB and semantic-model source contracts;
- Graph eligibility metadata;
- semantic drift detection;
- offline validation without Fabric credentials.

### #19 — Foundry + governed CEPIO MCP ✓

- CEPIO read/query/time/provenance/function/action tools exposed through MCP;
- Entra/Foundry identity -> CEPIO actor context;
- actor identity and roles excluded from model-callable tool arguments;
- explicit function authorization;
- recommendation separated from execution;
- no agent bypass of CEPIO policy or enterprise adapters.

## Completed P1

### #4 — Ontology migration manifests + compatibility gates ✓

- accepted ontology baseline pinned to immutable Git history;
- compatibility analysis across modules, namespaces, classes, relationships, properties, hierarchy and range/domain constraints;
- semantic-version enforcement;
- explicit migration-manifest format for intentional breaking changes;
- stale/duplicate migration declarations fail closed;
- compatibility gate enforced in GitHub Actions.

## Current priority

### #21 — App Service + AKS reference deployment profiles

**Goal:** make the current CEPIO runtime deployable as a coherent Microsoft-native reference system.

#### App Service
- CEPIO REST/MCP APIs and lightweight domain applications;
- managed identity / Entra integration boundary;
- VNet/private connectivity patterns;
- health/readiness endpoints;
- deployment slots and autoscale guidance;
- configuration and secretless patterns.

#### AKS
- scale-out CEPIO runtime, adapters, projectors and event workers;
- Entra Workload Identity;
- private networking and Key Vault integration;
- probes and autoscaling;
- workload isolation;
- auditable rollout patterns;
- optional NVIDIA GPU profile remains separate and non-blocking.

## Next priority

### #6 — Runtime observability / OpenTelemetry

- structured events for query, repository, function, policy, MCP, action and adapter execution;
- latency / success / failure metrics;
- distributed trace correlation across Foundry -> MCP -> CEPIO -> adapter;
- OpenTelemetry-compatible hook boundary;
- no unauthorized industrial data in telemetry payloads.

## Deferred / non-blocking

### #20 — Purview governance + lineage bridge

Purview remains useful for enterprise catalog, classification and governance but is **not a current v0.4 release blocker**.

Future scope may include:
- Purview/Data Map asset -> CEPIO SourceReference mapping;
- governance/classification/domain metadata in explanation context;
- CEPIO transformation -> Purview lineage publication artifacts;
- preservation of CEPIO runtime provenance as the operationally precise lineage layer.

## v0.4 release gate

A Microsoft-native reference deployment should demonstrate:

1. CEPIO canonical semantics materialized through the Fabric/Fabric IQ binding;
2. a Foundry agent querying CEPIO through MCP without bypassing CEPIO policy;
3. ontology evolution protected by migration manifests and CI compatibility gates;
4. the same CEPIO runtime deployable through App Service or AKS reference profiles;
5. all CEPIO core tests remaining cloud-independent and executable offline.

Purview is explicitly deferred and non-blocking for this release path.

Sequence:

`Query ✓ -> Fabric/IQ ✓ -> Foundry/MCP ✓ -> Migration compatibility ✓ -> App Service/AKS -> Observability`

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

# Platformization path

## v0.7 — Developer Platform

- SDK maturity;
- CLI;
- package/module registry;
- MCP/OpenAPI tooling;
- ontology-as-code workflows;
- developer tooling and documentation.

## v0.8 — Enterprise Runtime

- production persistence;
- scale and high availability;
- multi-tenancy;
- security hardening;
- production observability;
- SLO/performance program.

## v0.9 — Enterprise Adoption

**Gate:** a second Energy & Process enterprise can adopt CEPIO primarily through mapping, configuration and approved extensions rather than redesigning the runtime.

## v1.0 — Production Platform

- compatibility and upgrade guarantees;
- deployment automation;
- production SRE/security controls;
- partner extension/certification model;
- repeatable enterprise adoption.

---

## Project-board view

### DONE
- v0.1 Semantic Scaffold
- v0.2 Operational Kernel
- v0.3 Temporal + Provenance Kernel
- SEO/AD domain normalization
- DTC ISA-95 manufacturing federation
- IRI-first semantic identity
- property provenance
- bitemporal object/relationship history
- deterministic event/state projection
- graph intelligence + optional cuGraph acceleration
- #5 typed query + temporal filter contract
- #7 Microsoft platform extension architecture
- #18 Fabric + Fabric IQ semantic binding
- #19 Foundry + CEPIO MCP binding
- #4 migration manifests + compatibility gates

### NOW
- #21 App Service + AKS deployment profiles

### NEXT
- #6 Runtime observability / OpenTelemetry

### DEFERRED / NON-BLOCKING
- #20 Purview governance + lineage bridge
- #25 GPU AKS cuGraph validation / benchmarking

### LATER
- v0.5 Live Industrial Integration
- v0.6 Reference Industrial Applications
- v0.7 Developer Platform
- v0.8 Enterprise Runtime
- v0.9 Enterprise Adoption
- v1.0 Production Platform
