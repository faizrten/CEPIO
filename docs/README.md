# CEPIO Documentation

This directory contains CEPIO's technical documentation and the curated CEPIO Wiki.

## Start here

- **[Code Quality & Governance v2](governance/code-quality-governance-v2.md)** — quality gates, security, compatibility evidence, release qualification and required check names.

- **[CEPIO v0.4 Developer Preview](developer-preview.md)** — clean-environment install, startup, qualification and release boundary.
- **[CEPIO Wiki](wiki/Home.md)** — narrative, navigable documentation for product, architecture, ontology, runtime, APIs, integrations, operations, roadmap and glossary.
- **[Architecture](architecture.md)** — authoritative runtime architecture notes.
- **[Execution Roadmap](roadmap.md)** — detailed implementation and release roadmap.
- **[Kinetic Runtime](kinetic-runtime.md)** — durable workflow kernel over CEPIO Functions, Decisions, approvals and governed Actions.
- **[Kinetic Execution Resilience v0.2](kinetic-execution-resilience.md)** — bounded Function retry/timeout, workflow cancellation and governed reverse compensation.
- **[Governed External Action Runtime](external-action-runtime.md)** — canonical-to-source identity resolution, async writeback, verification and reconciliation.
- **[Kinetic Runtime Consistency v0.3.1](kinetic-runtime-consistency-v0.3.1.md)** — immutable workflow versions, atomic triggers, explicit workflow lineage, identity revalidation and optimistic dispatch claims.
- **[Kinetic External Verification Gate v0.4](kinetic-external-verification-v0.4.md)** — durable workflow wait on source verification with immutable terminal Outcomes and explicit reconciliation for unknown writes.
- **[Generalization & Competency Harness](generalization-harness.md)** — agentic validation architecture and the deterministic drilling-contractor v0.1 benchmark.
- **[Drilling Harness Semantic Remediation v0.2](drilling-semantic-remediation-v0.2.md)** — first evidence-driven remediation cycle against the frozen drilling benchmark.
- **[Drilling Domain Qualification v0.4](drilling-domain-qualification-v0.4.md)** — frozen enterprise, optimization, and agentic-operations competency benchmark and remediation rules.

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
- [Drilling Domain Qualification v0.4](drilling-domain-qualification-v0.4.md)

## Integrations

- [Microsoft Fabric / Fabric IQ](integrations/microsoft-fabric-iq.md)
- [NVIDIA cuGraph](integrations/nvidia-cugraph.md)

## Documentation model

The documentation is intentionally split into two layers:

1. **`docs/wiki/`** — the explanatory and navigational layer for readers.
2. **Technical documents in `docs/`, ontologies, mappings, shapes and code** — the authoritative executable/design contracts.

When the two differ, the implementation contracts and accepted architecture decisions in the repository are authoritative. The wiki should be updated as part of material CEPIO capability and release changes.

## Workflow policy v0.5.1

[Workflow policy integration](workflow-policy-v0.5.1.md) binds exact policy versions to durable workflow instances, derives trusted canonical context, pauses governed actions for human approval, and persists policy evidence through Action, external execution and Outcome.
