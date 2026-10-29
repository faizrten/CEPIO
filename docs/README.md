# CEPIO Documentation

## Strategic North Star and documentation authority

**Mission:** Democratize industrial expertise and elevate human professional excellence.  
**Product:** The indispensable expert companion for every industrial professional.  
**Technology:** Thin infrastructure. Thick Industry IQ.  
**Moat and trust:** Industrial Competence Network; collective industrial progress, sovereign enterprise intelligence.

Start with the [canonical Product North Star & Strategic Doctrine](strategy/industry-iq-product-north-star.md); then use the roadmap, current-state snapshot, scorecard and release manifest for **separate, evidence-backed implementation and maturity claims**. Existing historic ADRs and benchmark reports retain their original context.

This directory contains CEPIO's technical documentation and curated Wiki.

## Start here

- **[Current State](current-state.md)** â€” dated mainline capability snapshot; distinguishes published release, merged capability and scorecard maturity.
- **[Rig 07 Performance Activation](drilling-performance-activation-v0.1.md)** — deterministic synthetic drilling performance acceptance and policy-safe recommendation.
- **[CEPIO Wiki](wiki/Home.md)**
- **[Evidence and Decision Assurance v0.2](performance-evidence-decision-assurance-v0.2.md)**
- **[Executive Performance Preview v0.1](performance-executive-preview-v0.1.md)** — opt-in read-only headless decision package.
- **[Host-bound Performance Evidence v0.1](performance-host-bound-evidence-v0.1.md)** — tenant-scoped versioned read-only source materialization. â€” reader-oriented product, architecture, runtime, Industry IQ and roadmap navigation.
- **[Architecture](architecture.md)** â€” current portable Industrial Operating Intelligence architecture.
- **[Execution Roadmap](roadmap.md)** â€” authoritative product release gates from FOUNDATION through GUARANTEE.
- **[Version Naming and Delivery Status](version-naming.md)** â€” product labels, component/Lab/pack/API version scopes and roadmap-vs-scorecard distinction.
- **[Canonical v1.0 Completion Scorecard](v1-completion-scorecard.md)** â€” governed evidence-backed 100-point maturity model.
- **[v1.0 Scorecard Governance](governance/v1-scorecard-governance.md)** â€” scoring authority, evidence and change-control contract.
- **[CEPIO v0.4 FOUNDATION Developer Preview](developer-preview.md)** â€” qualified published-release installation/support boundary.
- **[Agent Delivery Protocol v0.1](developer/agent-delivery-protocol.md)** — evidence-led agent engineering, bounded PRs, and advisory industrial-judgment evaluation.
- **[Code Quality & Governance v2](governance/code-quality-governance-v2.md)** â€” quality, security, compatibility and release evidence controls.

- [Deployed image read-only evidence](adr/ADR-0042-deployed-image-readonly-evidence.md) — exact digest scans, SBOM and provenance verification boundaries.

## North Star

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

For Microsoft-hosted agent workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

The documentation should preserve this distinction throughout:

- source/platform systems remain authoritative;
- CEPIO binds them through replaceable contracts;
- reusable industrial competence accumulates in Industry IQ;
- agents operate through CEPIO evidence, policy and authority;
- model output, caches and indexes do not become authority.

## Current product posture

- **v0.4 FOUNDATION:** qualified published Developer Preview.
- **v0.5 CONNECT:** current / partial product release gate.
- **v0.6 EXECUTEâ€“v1.0 GUARANTEE:** future release gates with some foundations already implemented on `main`.
- **canonical v1 score:** 69/100 at the governed snapshot; later merges do not automatically modify the score.

See [Current State](current-state.md).

---

# Core architecture and contracts

## Semantic / temporal / governance foundation

- [Architecture](architecture.md)
- [Temporal state projection](temporal-state-projection.md)
- [Migrations and compatibility](migrations-and-compatibility.md)
- [Type identity and versioning](type-identity-and-versioning.md)
- [Property normalization](property-normalization.md)
- [Domain module normalization](domain-module-normalization.md)
- [Query contract](query-contract.md)
- [Application Contract v0.2](application-contract-v0.2.md)
- [Protocol Convergence v0.3](protocol-convergence-v0.3.md)

## Kinetic / governed execution

- [Kinetic Runtime](kinetic-runtime.md)
- [Kinetic Execution Resilience](kinetic-execution-resilience.md)
- [Kinetic Runtime Consistency](kinetic-runtime-consistency-v0.3.1.md)
- [Kinetic External Verification Gate](kinetic-external-verification-v0.4.md)
- [Governed External Action Runtime](external-action-runtime.md)
- [Workflow Policy Integration](workflow-policy-v0.5.1.md)
- [Skill Runtime Preflight](skill-runtime-preflight.md)
- [Skill Runtime Capabilities](skill-runtime-capabilities.md)

---

# Binding and platform portability

- [Binding Contract v0.1](developer/platform-bindings.md)
- [Microsoft Platform Extension](microsoft-platform-extension.md)
- [Microsoft Fabric / Fabric IQ](integrations/microsoft-fabric-iq.md)
- [Microsoft Fabric Live Binding Proof](integrations/microsoft-fabric-live-binding-proof.md)
- [Foundry + MCP](foundry-mcp.md)
- [Microsoft 365 Copilot managed agent (read-only P0)](integrations/microsoft-365-copilot-managed-agent.md)
- [Reliability Agent Lighthouse](reliability-agent-lighthouse.md)
- [Foundry Reliability G1](foundry-reliability-g1.md)
- [NVIDIA cuGraph](integrations/nvidia-cugraph.md)

Binding principle:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

---

# Industry IQ control plane

## Capability and compounding intelligence

- [Capability Registry & Compounding Industrial Intelligence](capability-registry-and-compounding-intelligence.md)
- [Intelligence Sovereignty Contract v0.1 — first enforcement slice](intelligence-sovereignty-v0.1.md) — tagged evidence use, lineage and provisional qualification boundaries.
- [Domain Onboarding workflow](wiki/20-Domain-Onboarding-Workflow.md)
- [Compounding Industrial Intelligence Wiki](wiki/21-Compounding-Industrial-Intelligence.md)

## Industry IQ packs and trust

- Industry IQ Pack Registry and compatibility contracts are documented in their focused package/Skill docs and tests.
- [Industry IQ Trusted Catalogue](industry-iq-trusted-catalogue.md)
- [Industry IQ Supply Chain v0.6.1](industry-iq-supply-chain-v0.6.1.md)

These contracts keep reusable industrial intelligence separately deployable and governed while preventing agents from gaining package discovery/install/trust-policy authority.

---

# Memory, retrieval and runtime acceleration

- [Memory & Context Architecture](memory-context-architecture.md)
- [Memory & Context Wiki](wiki/22-Memory-and-Context.md)
- [Retrieval & Indexing Architecture](retrieval-indexing-architecture.md)
- [Retrieval & Indexing Wiki](wiki/23-Retrieval-and-Indexing.md)
- [Compiled Industry IQ](compiled-industry-iq.md)
- [Compiled Industry IQ Wiki](wiki/24-Compiled-Industry-IQ.md)

Core invariant:

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

Search indexes and caches are rebuildable projections, not semantic authority or industrial truth.

---

# Enterprise performance intelligence

- [Enterprise Performance Graph Wiki](wiki/22-Enterprise-Performance-Graph.md)
- Performance Contract / specialization documentation is linked from the Enterprise Performance Graph page and associated ADRs.
- [Industry Performance Packs v0.1](industry-performance-packs.md)
- [Industry Performance Packs Wiki](wiki/25-Industry-Performance-Packs.md)
- [ADR-0034 â€” Industry Performance Reference Packs](adr/ADR-0034-industry-performance-reference-packs-v0.1.md)

Performance reference packs are organization-neutral starting points. Customer formulas, targets, thresholds, scopes, source bindings and operating structures remain customer specialization.

---

# Management and hosted protocol surfaces

- [Management Control Plane Wiki](wiki/21-Management-Control-Plane.md)
- [Remote Management Read Projection](remote-management-read-projection.md)
- [Foundry + MCP](foundry-mcp.md)
- [ADR-0035 â€” Hosted MCP Gateway](adr/ADR-0035-hosted-mcp-gateway-v0.1.md)

Hosted target composition:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

Management remains observation-only; authenticated MCP callers cannot self-assert CEPIO roles.

---

# Users, competency, generalization and assurance

- [Target Users / Personas](wiki/19-Target-Users-Personas.md)
- [Competency & Assurance](wiki/20-Competency-Assurance.md)
- [Generalization & Competency Harness](generalization-harness.md)
- [Drilling Semantic Remediation](drilling-semantic-remediation-v0.2.md)
- [Operational Assurance](../generalization/OPERATIONAL_ASSURANCE.md)
- [Operator v0.6](../generalization/OPERATOR_V06.md)

Competency quality should be read across separate layers:

- semantic;
- runtime;
- procedural / Skill;
- agent;
- operational.

Do not turn one layer's PASS into a blanket production-readiness claim.

---

# Public API, SDK and operations

- [API v1 Client Guide](api-client-guide.md)
- [API Reliability Semantics](api-reliability.md)
- [Representative API Examples](api-examples.md)
- [REST Security / Entra](rest-security.md)
- [Typed Query Contract](query-contract.md)
- [Query Load Baseline](query-load-baseline.md)
- [API Versioning](api-versioning.md)
- [Reference Deployment Profiles](deployment-profiles.md)
- [Observability / OpenTelemetry](observability.md)

---

# Wiki map

The canonical navigation lives in [Wiki Home](wiki/Home.md).

New capability pages have landed in parallel and some retain duplicate historical numeric filename prefixes. Treat the Wiki Home map as canonical navigation; do not infer ordering or versioning from the numeric filename prefix alone.

Current newer pages include:

- Domain Onboarding Workflow;
- Compounding Industrial Intelligence;
- Management Control Plane;
- Memory and Context;
- Retrieval and Indexing;
- Compiled Industry IQ;
- Enterprise Performance Graph;
- Industry Performance Packs.

---

# Documentation authority model

Use these layers together:

1. **implementation contracts, code, ontologies, mappings, tests and accepted ADRs** â€” authoritative behavior/implementation evidence;
2. **`current-state.md`** â€” current narrative mainline snapshot;
3. **`roadmap.md`** â€” product release-gate authority;
4. **`config/v1-scorecard.yaml`** â€” numeric v1 maturity authority;
5. **`RELEASE.md`** â€” published v0.4 support boundary;
6. **`docs/wiki/`** â€” explanatory/navigation layer.

Historical benchmark documents remain historical evidence and should not be rewritten simply to adopt newer product terminology.

## Documentation definition of done

A material PR should update the relevant focused technical docs and the appropriate narrative/index surfaces in the same PR.

At minimum consider:

- `current-state.md`;
- root `README.md`;
- this index;
- Wiki Home;
- Architecture;
- Roadmap;
- Version Naming;
- relevant focused technical docs and ADRs.

If a change genuinely has no documentation impact, the PR should explicitly state why.
