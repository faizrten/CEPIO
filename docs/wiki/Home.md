# CEPIO Wiki

**CEPIO — Common Energy & Process Industry Ontology**

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

The Wiki is the reader-oriented narrative/navigation layer over the executable contracts, ADRs, tests, ontologies, mappings and focused technical documentation in the repository.

For the latest repository posture, start with [CEPIO Current State](../current-state.md).

For the drilling synthetic testbed's move to Labs, see
[Scenario Lab migration](../scenario-lab-migration.md).

## North Star

> **Thin infrastructure. Thick Industry IQ.**

Frontier models supply general intelligence. Industrial/data platforms supply enterprise context and infrastructure. CEPIO supplies reusable industrial operating competence:

- canonical industrial meaning and state;
- evidence and provenance;
- uncertainty/confidence;
- Skills and procedures;
- failure/risk/constraint patterns;
- performance/KPI/economic logic;
- Decisions and authority;
- governed Actions/workflows;
- competency and assurance contracts.

Palantir Ontology remains a useful capability benchmark, not CEPIO's product identity.

For Microsoft-hosted agent workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

## Product shape

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES
                         |
                         v
               Replaceable bindings
                         |
                         v
              Thin CEPIO operating core
 semantics · state · evidence · time · provenance · uncertainty
 policy · authority · Functions · Decisions · Actions
                         |
                         v
                 Thick Industry IQ
 capabilities · Skills · competencies · performance contracts
 patterns · constraints · KPI/economic logic · workflows · evaluations
                         |
                         v
       Governed intelligence/context control plane
 Capability Registry · Memory · Retrieval · Compiled Industry IQ
                         |
                         v
              REST · Management · MCP
                         |
                         v
        Apps · Studio · copilots · agents
```

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

## Current status

### Product release

**CEPIO v0.4 FOUNDATION — Developer Preview** is the current qualified published release.

### Current release gate

**CEPIO v0.5 CONNECT — Live Industrial Integration** remains open / partial. The decisive proof is a real multi-source industrial asset context plus one authenticated, governed, idempotent, verified and reconciled external action.

### Mainline capability

Repository `main` is ahead of the v0.4 release guarantee and already includes substantial later-stage foundations, including:

- durable workflow/action verification and Outcomes;
- Binding Contract and Fabric live-proof path;
- Capability Registry / Compounding Industrial Intelligence;
- Industry IQ Pack Registry, trusted catalogue and supply-chain policy;
- Memory & Context;
- Retrieval & Indexing;
- Compiled Industry IQ;
- Performance Contracts and Industry Performance Reference Packs;
- authenticated read-only Management projection;
- authenticated hosted `/mcp` gateway;
- Microsoft Foundry Reliability G1 qualification path.

Merged implementation does not automatically qualify a product release or live environment proof.

See [Current State](../current-state.md) for the dated snapshot.

## Operating loop

```text
Observe -> Understand -> Reason -> Decide -> Recommend
        -> Authorize -> Act -> Verify -> Learn
```

## Experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

The UI is not the architecture. Apps, Studio, copilots and agents consume the same governed operating contract while adapting presentation to persona and decision context.

## Target users

CEPIO serves:

1. industrial decision-makers — engineers, planners and operational leaders;
2. application/AI builders;
3. platform/data/integration teams;
4. governance and technical-authority users;
5. AI agents as authenticated software consumers.

See [Target Users / Personas](19-Target-Users-Personas.md).

## Competency & Assurance

Competency is a first-class product-quality mechanism.

```text
Persona
 -> Responsibility
 -> Decision
 -> Competency question
 -> Required capability/evidence
 -> Skill / Function / Decision / Action
 -> Assurance result
```

CEPIO assurance spans semantic, runtime, procedural/Skill, agent and operational competency. Generalization asks whether the capability is reusable; assurance asks whether a claim or action is justified.

See [Competency & Assurance](20-Competency-Assurance.md).

## Roadmap taxonomy

```text
v0.4 FOUNDATION
 -> v0.5 CONNECT
 -> v0.6 EXECUTE
 -> v0.7 EXTEND
 -> v0.8 OPERATE
 -> v0.9 GENERALIZE
 -> v1.0 GUARANTEE
```

See [Roadmap to v1.0](17-Roadmap.md) and the authoritative [Execution Roadmap](../roadmap.md).

## v1 maturity score

The governed scorecard currently reports **69/100 (69%)** at its pinned evidence snapshot. That score is independent of product release gates and does not update automatically when new PRs merge.

See [v1.0 completion scorecard](../v1-completion-scorecard.md).

---

# Wiki map

> **Navigation note:** several newer capability pages landed in parallel and currently retain historical numeric filename prefixes that are not unique. The links below are the canonical navigation map; do not infer architecture order from filename numbers alone. Renaming historical files is deferred unless needed for link correctness.

## Product and architecture

- [CEPIO Overview](01-Overview.md)
- [Core Concepts](02-Core-Concepts.md)
- [Architecture](03-Architecture.md)
- [Ontology Model](04-Ontology-Model.md)
- [Runtime](05-Runtime.md)

## Interfaces and execution

- [API, SDK and MCP](06-API-SDK-MCP.md)
- [Query Model](07-Query-Model.md)
- [Functions, Decisions and Actions](08-Functions-Decisions-Actions.md)

## Data, time and trust

- [Temporal State and Provenance](09-Temporal-State-Provenance.md)
- [Integration Architecture](10-Integration-Architecture.md)
- [Microsoft Platform](11-Microsoft-Platform.md)
- [Standards Federation](12-Standards-Federation.md)

## Operations and engineering

- [Security and Governance](13-Security-Governance.md)
- [Deployment and Operations](14-Deployment-Operations.md)
- [Developer Guide](15-Developer-Guide.md)
- [Reference Scenarios](16-Reference-Scenarios.md)
- [Roadmap to v1.0](17-Roadmap.md)
- [Glossary](18-Glossary.md)

## Users, competency and domain evolution

- [Target Users / Personas](19-Target-Users-Personas.md)
- [Competency & Assurance](20-Competency-Assurance.md)
- [Domain Onboarding Workflow](20-Domain-Onboarding-Workflow.md)
- [Compounding Industrial Intelligence](21-Compounding-Industrial-Intelligence.md)

## Management and hosted control plane

- [Management Control Plane](21-Management-Control-Plane.md)

The hosted remote projection is authenticated and read-only. It is separate from the Application Contract and must not become an authority bypass.

## Memory, retrieval and runtime intelligence

- [Memory and Context](22-Memory-and-Context.md)
- [Retrieval and Indexing](23-Retrieval-and-Indexing.md)
- [Compiled Industry IQ](24-Compiled-Industry-IQ.md)

These implement the principle:

> **Industry IQ may compound continuously; runtime working context remains bounded.**

## Enterprise performance intelligence

- [Enterprise Performance Graph](22-Enterprise-Performance-Graph.md)
- [Industry Performance Packs](25-Industry-Performance-Packs.md)

Performance Contracts connect objectives, KRs, KPIs, guardrails, accountability and contribution relationships to governed response pathways without making customer formulas/targets universal CEPIO semantics.

## Skill examples

- [Maintenance Deferral Skill v0.3](CEPIO-Skills-Maintenance-Deferral-v0.3.md)

---

# Key focused technical documents

The Wiki summarizes; focused docs define bounded technical contracts. Important current entry points include:

- [Current State](../current-state.md)
- [Architecture](../architecture.md)
- [Execution Roadmap](../roadmap.md)
- [Version Naming](../version-naming.md)
- [v1 Completion Scorecard](../v1-completion-scorecard.md)
- [Application Contract](../application-contract-v0.2.md)
- [Protocol Convergence](../protocol-convergence-v0.3.md)
- [Binding Contract](../developer/platform-bindings.md)
- [Fabric Live Binding Proof](../integrations/microsoft-fabric-live-binding-proof.md)
- [Kinetic Runtime](../kinetic-runtime.md)
- [External Action Runtime](../external-action-runtime.md)
- [Memory & Context Architecture](../memory-context-architecture.md)
- [Retrieval & Indexing Architecture](../retrieval-indexing-architecture.md)
- [Compiled Industry IQ](../compiled-industry-iq.md)
- [Capability Registry / Compounding Intelligence](../capability-registry-and-compounding-intelligence.md)
- [Industry Performance Packs](../industry-performance-packs.md)
- [Foundry + MCP](../foundry-mcp.md)
- [Reliability Agent Lighthouse](../reliability-agent-lighthouse.md)
- [Remote Management Read Projection](../remote-management-read-projection.md)

## Documentation governance

Documentation is part of CEPIO's engineering definition of done.

Material changes to semantics, public/application contracts, runtime behavior, integrations, deployment, security/governance, Industry IQ, product positioning, release status or roadmap state must update relevant documentation in the same PR.

At minimum, material architecture/product changes should consider updating:

- `docs/current-state.md`;
- `README.md`;
- `docs/README.md`;
- this Wiki Home;
- `docs/architecture.md` / Wiki Architecture;
- `docs/roadmap.md` / Wiki Roadmap;
- relevant focused technical docs and ADRs.

If a change genuinely has no documentation impact, the PR should explicitly state why.

## Canonical source of truth

Use these sources together:

1. implementation contracts, code, ontologies, mappings, tests and accepted ADRs — behavior/implementation authority;
2. `docs/current-state.md` — dated narrative mainline snapshot;
3. `docs/roadmap.md` — product release-gate authority;
4. `config/v1-scorecard.yaml` — numeric v1 maturity authority;
5. `RELEASE.md` — published release boundary;
6. this Wiki — explanatory and navigational layer.
