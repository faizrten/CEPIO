# CEPIO Documentation

This directory contains CEPIO's technical documentation and the curated CEPIO Wiki.

## Roadmap capability labels

CEPIO product releases use a stable capability taxonomy:

`FOUNDATION -> CONNECT -> EXECUTE -> EXTEND -> OPERATE -> GENERALIZE -> GUARANTEE`

These labels describe **what each product release must prove**. They are not separate version axes and do not replace component, Lab, Skill, ontology-module or API versions.

- **v0.4 FOUNDATION — Developer Preview** — coherent operating contract for developers.
- **v0.5 CONNECT — Live Industrial Integration** — operate over authoritative industrial systems.
- **v0.6 EXECUTE — Kinetic Runtime + Reference Industrial Applications** — produce governed, verified industrial outcomes.
- **v0.7 EXTEND — Industrial Developer Platform** — let independent teams add Industry IQ without modifying Core.
- **v0.8 OPERATE — Enterprise Runtime** — sustained enterprise-grade operation.
- **v0.9 GENERALIZE — Portability + Second-Enterprise Adoption** — prove reuse across enterprises/platforms.
- **v1.0 GUARANTEE — Production Guarantees** — stable explicit production contracts.

See [Version naming and delivery status](version-naming.md) for the canonical naming rules and [Execution Roadmap](roadmap.md) for release gates.

## Start here

- **[Version naming and delivery status](version-naming.md)** — distinguish product roadmap labels, CEPIO releases, runtime components, Lab benchmarks, Skill versions, ontology modules and API versions.
- **[Code Quality & Governance v2](governance/code-quality-governance-v2.md)** — quality gates, security, compatibility evidence, release qualification and required check names.
- **[CEPIO v0.4 FOUNDATION — Developer Preview](developer-preview.md)** — clean-environment install, startup, qualification and release boundary.
- **[CEPIO Wiki](wiki/Home.md)** — narrative, navigable documentation for product, architecture, ontology, runtime, APIs, integrations, operations, roadmap and glossary.
- **[Architecture](architecture.md)** — authoritative architecture under the thin-core / thick-Industry-IQ North Star.
- **[Execution Roadmap](roadmap.md)** — detailed `FOUNDATION -> CONNECT -> EXECUTE -> EXTEND -> OPERATE -> GENERALIZE -> GUARANTEE` roadmap.
- **[Kinetic Runtime](kinetic-runtime.md)** — durable workflow kernel over CEPIO Functions, Decisions, approvals and governed Actions.
- **[Kinetic Execution Resilience v0.2](kinetic-execution-resilience.md)** — bounded Function retry/timeout, workflow cancellation and governed reverse compensation.
- **[Governed External Action Runtime](external-action-runtime.md)** — canonical-to-source identity resolution, async writeback, verification and reconciliation.
- **[Kinetic Runtime Consistency v0.3.1](kinetic-runtime-consistency-v0.3.1.md)** — immutable workflow versions, atomic triggers, explicit workflow lineage, identity revalidation and optimistic dispatch claims.
- **[Kinetic External Verification Gate v0.4](kinetic-external-verification-v0.4.md)** — durable workflow wait on source verification with immutable terminal Outcomes and explicit reconciliation for unknown writes.
- **[Generalization & Competency Harness](generalization-harness.md)** — deterministic competency/generalization architecture.
- **[Drilling Harness Semantic Remediation v0.2](drilling-semantic-remediation-v0.2.md)** — evidence-driven remediation against the frozen drilling benchmark.

## Users, competency and assurance

- [Target Users / Personas](wiki/19-Target-Users-Personas.md) — industrial decision-makers, builders, platform teams, governance users and AI-agent consumers.
- [Competency & Assurance](wiki/20-Competency-Assurance.md) — semantic, runtime, Skill, agent and operational competency.
- [Operational assurance](../generalization/OPERATIONAL_ASSURANCE.md) — deterministic runtime evidence contract.
- [Operator v0.6](../generalization/OPERATOR_V06.md) — executable REST/MCP agent boundary.

## v0.4 FOUNDATION public API and operations

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

## Integrations

- [Microsoft Fabric / Fabric IQ](integrations/microsoft-fabric-iq.md)
- [NVIDIA cuGraph](integrations/nvidia-cugraph.md)

## Documentation model

The documentation is intentionally split into two layers:

1. **`docs/wiki/`** — explanatory and navigational documentation.
2. **Technical documents in `docs/`, ontologies, mappings, shapes and code** — authoritative executable/design contracts.

When the two differ, implementation contracts and accepted architecture decisions in the repository are authoritative. The wiki should be updated with material CEPIO capability, positioning and release changes.

## Workflow policy v0.5.1

[Workflow policy integration](workflow-policy-v0.5.1.md) binds exact policy versions to durable workflow instances, derives trusted canonical context, pauses governed actions for human approval, and persists policy evidence through Action, external execution and Outcome.
