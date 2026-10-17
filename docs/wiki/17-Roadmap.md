# Roadmap to v1.0

## Completed — v0.1 Semantic Scaffold

Outcome: common ontology foundation.

Key results:

- modular core/industrial/energy/lifecycle/enterprise/kinetic ontology;
- object, relationship, event and function concepts;
- in-memory traversal;
- initial actions and roles;
- FastAPI scaffold;
- refinery sample.

## Completed — v0.2 Operational Kernel

Outcome: executable operating runtime.

Key results:

- repository abstractions;
- SQLite backend;
- optimistic concurrency;
- action audit;
- secure idempotency;
- RDF-driven type registry;
- policy interface;
- preconditions/approvals;
- Decision records;
- typed functions;
- traversal;
- Python SDK;
- MCP-ready facade;
- reference adapters;
- SHACL path.

## Completed — v0.3 Temporal + Provenance Kernel

Outcome: CEPIO can explain what is true, where it came from, what was true/known at time T, and which events produced state.

Key results:

- broader canonical industrial modules;
- IRI-first identity;
- canonical property contract;
- source references and property provenance;
- bitemporal object/relationship history;
- deterministic event-state projection.

## Current — v0.4 Microsoft Platform Extension

Completed foundations:

- typed operational query;
- Microsoft platform extension architecture;
- Fabric/Fabric IQ semantic binding;
- Foundry + governed MCP;
- ontology migration manifests and CI compatibility gates.

### Independent domain qualification milestone

The drilling-contractor domain qualification v0.4 is a frozen lab benchmark, not a CEPIO product release. It expands enterprise, optimization, contract, and digital/AI persona coverage across three challenge bands while preserving classified semantic gaps. See the [qualification contract](../drilling-domain-qualification-v0.4.md) and [ADR-0010](../adr/ADR-0010-drilling-domain-qualification.md).

### Current priority

**App Service + AKS deployment profiles**.

### Next priority

**Runtime observability / OpenTelemetry**.

### Deferred / non-blocking

- Purview governance/lineage bridge;
- GPU AKS cuGraph benchmarking.

## Next — v0.5 Live Industrial Integration

Target outcome: prove CEPIO across live enterprise systems and close the governed writeback loop.

Planned:

- production SAP S/4HANA/EAM adapter;
- historian/PI streaming adapter;
- OSDU adapter;
- P6 adapter;
- event ingestion/reconciliation;
- governed writeback;
- retries/dead-letter handling;
- identity resolution.

Release gate:

> One CEPIO application traverses at least three live enterprise sources and performs one governed, auditable and reconciled enterprise writeback.

## v0.6 Reference Industrial Applications

Target applications:

- asset reliability;
- refinery margin optimization;
- turnaround planning.

Gate: measurable operating value with complete observe-to-action loop.

## v0.7 Developer Platform

Planned:

- mature SDKs;
- CLI;
- package/module registry;
- OpenAPI/MCP tooling;
- ontology-as-code workflows;
- developer documentation.

## v0.8 Enterprise Runtime

Planned:

- production persistence;
- scale/HA;
- multi-tenancy;
- security hardening;
- production observability;
- SLO/performance program.

## v0.9 Enterprise Adoption

Gate:

> A second Energy & Process enterprise can adopt CEPIO primarily through mapping, configuration and approved extensions rather than runtime redesign.

## v1.0 Production Platform

Expected characteristics:

- stable compatibility/upgrade guarantees;
- deployment automation;
- SRE/security controls;
- repeatable enterprise adoption;
- partner extension/certification model;
- mature API/SDK contracts;
- production-grade integration and governance.

## What it takes to reach v1.0

The dominant work is no longer ontology vocabulary creation. The critical path is productization:

```text
semantic contract
 -> stable API
 -> live adapters
 -> production deployment
 -> observability/SRE
 -> reference applications
 -> second-customer repeatability
 -> v1 compatibility guarantees
```
