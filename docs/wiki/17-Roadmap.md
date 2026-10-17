# Roadmap to CEPIO v1.0

See [version naming](../version-naming.md) for product, component, Lab and API version scopes, and [execution roadmap](../roadmap.md) for release gates.

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

## Completed — CEPIO v0.4 Developer Preview

Platform integration, secured API/client contracts, deployment profiles (#65), observability (#66) and Developer Preview qualification (#69) are on main. Umbrella #22 is completed. Qualification is distinct from publication of a GitHub Release.

## Current — CEPIO v0.5 Live Industrial Integration

Target outcome: prove CEPIO across live enterprise systems and close the governed writeback loop.

Current work (#51):

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

## Parallel — Kinetic runtime and Generalization Lab

#67 has durable workflows, human approval, bounded resilience, external verification and Outcomes on main. Trigger subscriptions, public workflow surfaces, telemetry and production operation remain. Runtime component versions do not identify CEPIO releases.

#112/#116/#119 track the open drilling qualification stack. Drilling domain v0.4/v0.4.1/v0.5 name benchmark contracts, independently of CEPIO product releases.

#20 Purview and #25 GPU validation remain parked without a current release target.

## Future — CEPIO v0.6 Reference Industrial Applications

Target applications:

- asset reliability;
- refinery margin optimization;
- turnaround planning.

Gate: measurable operating value with complete observe-to-action loop.

## Future — CEPIO v0.7 Developer Platform

Planned:

- mature SDKs;
- CLI;
- package/module registry;
- OpenAPI/MCP tooling;
- ontology-as-code workflows;
- developer documentation.

## Future — CEPIO v0.8 Enterprise Runtime

Planned:

- production persistence;
- scale/HA;
- multi-tenancy;
- security hardening;
- production observability;
- SLO/performance program.

## Future — CEPIO v0.9 Enterprise Adoption

Gate:

> A second Energy & Process enterprise can adopt CEPIO primarily through mapping, configuration and approved extensions rather than runtime redesign.

## Future — CEPIO v1.0 Production Platform

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
