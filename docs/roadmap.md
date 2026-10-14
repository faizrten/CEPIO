# CEPIO Execution Roadmap

## Completed — v0.1 Semantic Scaffold

- modular CEPIO Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology;
- object, relationship, event and function concepts;
- in-memory graph traversal;
- initial actions and policy roles;
- FastAPI scaffold and refinery sample.

## Completed — v0.2 Operational Kernel

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
- executable KPI→asset→event→decision→work-order→spare demo.

## v0.3 — Temporal + Provenance Kernel

**Outcome:** CEPIO can reconstruct what the enterprise believed at a point in time and explain where every property came from.

- immutable object-version history;
- bitemporal relationship validity;
- event-to-state projections;
- source-system identity map;
- property-level provenance and lineage;
- ontology semantic versioning and migration manifests;
- breaking-change compatibility tests;
- richer query/filter API;
- runtime telemetry and OpenTelemetry hooks.

**Gate:** answer “what did we know, from which source, at time T, and what action followed?” without querying a source system directly.

## v0.4 — Live Industrial Integration

**Outcome:** source-system abstraction becomes real.

- SAP S/4HANA/EAM read/write adapter;
- AVEVA PI/historian streaming adapter;
- OSDU adapter + upstream semantic mapping;
- Primavera P6 schedule adapter;
- Fabric/OneLake + Fabric IQ mapping;
- Entra identity mapping;
- writeback reconciliation and dead-letter handling;
- secrets/configuration boundary.

**Gate:** one CEPIO application traverses at least three live enterprise sources and performs one governed reconciled writeback.

## v0.5 — Reference Applications

- Asset Reliability operating application;
- Refinery Margin Optimization application;
- Turnaround Planning multi-agent application;
- decision/outcome feedback loop;
- workflow inbox for human approvals.

**Gate:** CEPIO proves measurable operating value, not merely semantic elegance.

## v1.0 — Platformization

- production graph/search backend;
- generated SDKs for Python/.NET/TypeScript;
- production MCP server and tool registry;
- ontology package registry;
- visual ontology/workflow studio;
- multi-tenancy and namespace governance;
- performance benchmark and SLO program;
- partner extension/certification model;
- standards mapping packs for OSDU, ISO 15926, CFIHOS, ISA-95, FIBO, DEXPI/IFC.

**Gate:** a second enterprise can adopt CEPIO by mapping/configuration rather than redesigning the ontology/runtime.
