# CEPIO Documentation

This directory contains CEPIO's technical documentation and the curated CEPIO Wiki.

## Start here

- **[Version naming and delivery status](version-naming.md)** — distinguish CEPIO releases, runtime components, Lab benchmarks and API versions.
- **[Canonical v1.0 completion scorecard](v1-completion-scorecard.md)** — evidence-backed 100-point product-maturity model and current canonical baseline.
- **[v1.0 scorecard governance](governance/v1-scorecard-governance.md)** — scoring authority, evidence rules, partial-credit discipline, regression and change control.

- **[Code Quality & Governance v2](governance/code-quality-governance-v2.md)** — quality gates, security, compatibility evidence, release qualification and required check names.

- **[CEPIO v0.4 Developer Preview](developer-preview.md)** — clean-environment install, startup, qualification and release boundary.
- **[CEPIO Wiki](wiki/Home.md)** — narrative, navigable documentation for product, architecture, ontology, runtime, APIs, integrations, operations, roadmap and glossary.
- **[Management Control Plane](wiki/21-Management-Control-Plane.md)** — protocol-neutral Management Contract v0.1 and local read-only FastAPI projection.
- **[Binding Contract v0.1](developer/platform-bindings.md)** — provider-neutral manifest, runtime registration, conformance and Management projection for replaceable industrial platforms.
- **[Industry Performance Packs v0.1](industry-performance-packs.md)** — reusable refinery and drilling-contractor objectives, KPI identities, driver graphs, guardrails and reference accountability built on Performance Contracts.
- **[Architecture](architecture.md)** — authoritative runtime architecture notes.
- **[Execution Roadmap](roadmap.md)** — detailed implementation and release roadmap.
- **[Kinetic Runtime](kinetic-runtime.md)** — durable workflow kernel over CEPIO Functions, Decisions, approvals and governed Actions.
- **[Kinetic Execution Resilience v0.2](kinetic-execution-resilience.md)** — bounded Function retry/timeout, workflow cancellation and governed reverse compensation.
- **[Governed External Action Runtime](external-action-runtime.md)** — canonical-to-source identity resolution, async writeback, verification and reconciliation.
- **[Kinetic Runtime Consistency v0.3.1](kinetic-runtime-consistency-v0.3.1.md)** — immutable workflow versions, atomic triggers, explicit workflow lineage, identity revalidation and optimistic dispatch claims.
- **[Kinetic External Verification Gate v0.4](kinetic-external-verification-v0.4.md)** — durable workflow wait on source verification with immutable terminal Outcomes and explicit reconciliation for unknown writes.
- **[Generalization & Competency Harness](generalization-harness.md)** — agentic validation architecture and the deterministic drilling-contractor v0.1 benchmark.
- **[Drilling Harness Semantic Remediation v0.2](drilling-semantic-remediation-v0.2.md)** — first evidence-driven remediation cycle against the frozen drilling benchmark.

## Users, competency and assurance

- [Target Users / Personas](wiki/19-Target-Users-Personas.md) — industrial users, platform builders, lighthouse focus and catalog boundaries.
- [Competency & Assurance](wiki/20-Competency-Assurance.md) — semantic benchmarks, operational gates, Operator evidence discipline and maturity direction.
- [Operational assurance](../generalization/OPERATIONAL_ASSURANCE.md) — deterministic runtime evidence contract.
- [Operator v0.6](../generalization/OPERATOR_V06.md) — executable REST/MCP agent boundary.

## v0.4 public API and operations

- [API v1 client guide](api-client-guide.md)
- [API reliability semantics](api-reliability.md)
- [Representative API examples](api-examples.md)
- [REST security / Microsoft Entra](rest-security.md)
- [Typed query contract](query-contract.md)
- [Query load baseline](query-load-baseline.md)
- [API versioning](api-versioning.md)
- [Reference deployment profiles](deployment-profiles.md)
- [Observability / OpenTelemetry](observability.md)

## Key technical contracts

- [Canonical v1.0 completion scorecard](v1-completion-scorecard.md)
- [v1.0 scorecard schema](v1-completion-scorecard.schema.md)
- [v1.0 scorecard governance](governance/v1-scorecard-governance.md)
- [Management Control Plane](wiki/21-Management-Control-Plane.md)
- [ADR-0020 — Management Control Plane v0.1](adr/ADR-0020-management-control-plane-v0.1.md)
- [Binding Contract v0.1](developer/platform-bindings.md)
- [ADR-0026 — Binding Contract v0.1](adr/ADR-0026-binding-contract-v0.1.md)
- [ADR-0028 — Fabric Live Binding Proof v0.1](adr/ADR-0028-fabric-live-binding-proof-v0.1.md)
- [Industry Performance Packs v0.1](industry-performance-packs.md)
- [ADR-0034 — Industry Performance Reference Packs v0.1](adr/ADR-0034-industry-performance-reference-packs-v0.1.md)
- [Kinetic runtime](kinetic-runtime.md)
- [Kinetic execution resilience v0.2](kinetic-execution-resilience.md)
- [Governed external action runtime](external-action-runtime.md)
- [Kinetic runtime consistency v0.3.1](kinetic-runtime-consistency-v0.3.1.md)
- [Kinetic external verification gate v0.4](kinetic-external-verification-v0.4.md)
- [Temporal state projection](temporal-state-projection.md)
- [Microsoft platform extension](microsoft-platform-extension.md)
- [Foundry + MCP](foundry-mcp.md)
- [Migrations and compatibility](migrations-and-compatibility.md)
- [Type identity and versioning](type-identity-and-versioning.md)
- [Property normalization](property-normalization.md)
- [Domain module normalization](domain-module-normalization.md)
- [Generalization & Competency Harness](generalization-harness.md)
- [Drilling Harness Semantic Remediation v0.2](drilling-semantic-remediation-v0.2.md)

## Integrations

- [Microsoft Fabric / Fabric IQ](integrations/microsoft-fabric-iq.md)
- [Microsoft Fabric Live Binding Proof v0.1](integrations/microsoft-fabric-live-binding-proof.md)
- [NVIDIA cuGraph](integrations/nvidia-cugraph.md)

## Documentation model

The documentation is intentionally split into two layers:

1. **`docs/wiki/`** — the explanatory and navigational layer for readers.
2. **Technical documents in `docs/`, ontologies, mappings, shapes and code** — the authoritative executable/design contracts.

When the two differ, the implementation contracts and accepted architecture decisions in the repository are authoritative. The wiki should be updated as part of material CEPIO capability and release changes.

## Workflow policy v0.5.1

[Workflow policy integration](workflow-policy-v0.5.1.md) binds exact policy versions to durable workflow instances, derives trusted canonical context, pauses governed actions for human approval, and persists policy evidence through Action, external execution and Outcome.
