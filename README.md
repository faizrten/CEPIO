# CEPIO

**Common Energy & Process Industry Ontology**

> **Industry IQ product North Star: The indispensable expert companion for every industrial professional.**

CEPIO is the headless, portable Industrial Operating Intelligence layer that makes this professional experience possible: **thin infrastructure, thick Industry IQ**.

CEPIO gives humans, applications and AI agents a shared operating understanding of industrial assets, processes, work, risk, performance, decisions and governed actions while preserving authoritative source systems and enterprise-specific operating knowledge.

## Product and technology North Stars

**Mission:** Democratize industrial expertise and elevate human professional excellence.

**Product North Star:** The indispensable expert companion for every industrial professional.

**Technology North Star:** Thin infrastructure. Thick Industry IQ.

**Strategic moat:** The Industrial Competence Network—qualified industrial expertise, independently tested capabilities, professional trust, and governed decision-to-outcome learning.

**Doctrine:** Own the competence. Prove the competence. Distribute the competence. Compound the competence.

See the [Industry IQ Product North Star & Strategic Doctrine](docs/strategy/industry-iq-product-north-star.md) for professional experience principles, differentiating moat, proposed services, guarded learning flywheel, portfolio boundaries, sequencing, success measures and anti-goals.

Industry IQ Companion is a **proposed logical professional experience** consuming the CEPIO API/MCP and host surfaces, not a new agent runtime; Industry IQ Studio remains the technical control/qualification experience. The current v0.5 CONNECT release gate and canonical v1 maturity score are unchanged.

Frontier models provide general intelligence. Data and industrial platforms provide storage, compute and enterprise context. CEPIO provides reusable **industrial operating competence**:

- industrial semantics and operational state;
- evidence requirements and provenance;
- uncertainty and confidence;
- Skills and procedural knowledge;
- failure, risk and constraint patterns;
- KPI, performance and economic logic;
- decision patterns and authority;
- governed Actions and workflows;
- competency and evaluation benchmarks.

Palantir Ontology remains a useful **capability benchmark**, not CEPIO's product identity.

For the Microsoft reference ecosystem, the architectural boundary is:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

Microsoft Foundry, Copilot, Fabric, Entra and Azure provide generic platform capabilities. CEPIO provides the industrial semantics, evidence, competence, Decisions, authority, governed Actions and Outcomes that make those capabilities industrially useful and safe.

---

## Product shape

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES · engineering systems
                         |
                         v
               Replaceable bindings
                         |
                         v
              Thin CEPIO operating core
 semantics · identity · state · time · evidence · provenance
 uncertainty · policy · authority · Functions · Decisions · Actions
                         |
                         v
                 Thick Industry IQ
 capabilities · Skills · competencies · performance contracts
 failure/risk/decision patterns · constraints · KPI/economic logic
 workflows · assurance/evaluation contracts
                         |
                         v
       Governed intelligence runtime and context plane
 Capability Registry · Memory · Retrieval · Compiled Industry IQ
                         |
                         v
                  Protocol surfaces
 REST /api/v1 · Management /management/v1 · MCP /mcp
                         |
                         v
        Apps · Studio · copilots · agents · workflows
```

The governing architecture rule is:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

CEPIO should not recreate Fabric, Cognite, OSDU, SAP, PI, a graph database, a search engine, a frontier-model runtime or a generic agent framework.

---

## Current state

### Published release

**CEPIO v0.4 FOUNDATION — Developer Preview**  
Python package version: **`0.4.0`**.

v0.4 qualifies the core developer/runtime contract: canonical semantics, temporal state and provenance, Functions, Decisions, governed Actions, public `/api/v1`, Entra-aware security boundaries, Microsoft bindings, reference deployment profiles and observability.

The published release guarantee is intentionally narrower than current repository `main`.

### Current product gate

**CEPIO v0.5 CONNECT — Live Industrial Integration** is current and remains **open / partial**.

The release gate is not satisfied until one industrial asset uses context from at least three authoritative source-system domains and completes one authorized, idempotent, verified and reconciled external writeback with explainable provenance.

SAP + PI and the K-201 reliability lighthouse remain the decisive product proof.

### Mainline capability ahead of v0.4

`main` already contains substantial foundations pulled forward from later roadmap stages, including:

- durable workflow, external verification/reconciliation and `WorkflowOutcome`;
- contextual policy and exact policy-version lineage;
- Skill Registry, READY preflight and executable Skill/application contracts;
- provider-neutral Binding Contract and Fabric live-proof path;
- Capability Registry and governed Compounding Industrial Intelligence;
- Industry IQ Pack Registry, trusted catalogue and supply-chain trust policy;
- durable Memory & Context, capability-routed Retrieval & Indexing and Compiled Industry IQ;
- source-neutral retrieval; PostgreSQL is the preferred next durable memory/retrieval implementation;
- Performance Contracts, specialization and Refinery/Drilling Industry Performance Reference Packs;
- authenticated read-only `/management/v1/*` projection;
- authenticated hosted Streamable HTTP `/mcp` gateway;
- Microsoft Foundry Reliability G1 qualification path.

Merged implementation does **not** automatically advance a CEPIO product release or prove a live environment qualification.

See **[CEPIO Current State](docs/current-state.md)** for the dated mainline snapshot.

---

## Industrial operating loop

```text
Observe
  -> Understand
  -> Reason
  -> Decide
  -> Recommend
  -> Authorize
  -> Act
  -> Verify
  -> Learn
```

The shorter product loop is:

```text
Understand -> Reason -> Decide -> Act -> Learn
```

CEPIO exists to make that loop reusable, evidence-backed, temporally correct and governed across industrial systems.

---

## What CEPIO owns

CEPIO should own the reusable industrial operating contract:

- canonical industrial meaning and cross-system identity;
- operational state and time;
- evidence/provenance requirements;
- uncertainty/confidence abstractions;
- industrial Functions, Skills and competencies;
- Decision and authority patterns;
- governed Actions and workflow semantics;
- performance/KPI/accountability contracts;
- competency, generalization and assurance contracts;
- outcome/evaluation semantics.

## What CEPIO normally binds rather than owns

- raw historian measurements;
- ERP transactions;
- seismic files and reservoir grids;
- engineering documents and 3D files;
- data-lake/warehouse storage;
- model hosting and frontier-model capability;
- generic agent execution;
- search/index infrastructure;
- customer-specific proprietary operating logic unless represented as an explicit customer/profile specialization.

---

## Industry IQ

CEPIO's differentiated IP should accumulate in reusable **Industry IQ**, not infrastructure volume.

Industry IQ includes:

```text
Domain semantics
+
Personas and competency questions
+
Evidence requirements
+
Skills and procedures
+
Failure / degradation / risk patterns
+
Functions and Decision patterns
+
Constraints and authority
+
KPI / economic / performance logic
+
Governed workflows
+
Evaluation and assurance benchmarks
```

The desired signal is:

> **More industrial competency with less Core churn.**

---

## Compounding intelligence without customer-data training

CEPIO separates global reusable Industry IQ from customer/profile knowledge.

The current control plane includes:

- Capability Registry;
- governed Domain Onboarding;
- evidence-backed capability promotion;
- cross-domain regression;
- Industry IQ Pack Registry;
- trusted catalogue/provenance;
- pack supply-chain policy;
- customer/profile isolation.

Customer operational data or profile knowledge does not silently become global Industry IQ. Promotion to reusable capability requires governed evidence and review.

---

## Memory, retrieval and compiled Industry IQ

CEPIO now separates durable knowledge from bounded per-task model context.

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

```text
Capability Registry
       |
       v
Capability routing
       |
       v
Retrieval / indexing
       |
       v
bounded candidates
       |
       v
Context Assembler
       |
       v
bounded model/agent context
```

Compiled Industry IQ deterministically materializes reusable capability bundles and uses a bounded cache for acceleration. Cache state is never semantic authority, and PROFILE/customer context is excluded from the shared compiled cache.

---

## Enterprise performance intelligence

Performance Contracts connect industrial operating state to objectives, KRs, KPIs, guardrails, accountability and response pathways.

The model supports explicit specialization:

```text
Industry reference
      -> Organization
      -> Role / Persona
      -> Individual
```

Refinery and Drilling Contractor Industry Performance Reference Packs are organization-neutral reference semantics. Customer formulas, targets, thresholds, scopes and accountability remain customer-owned specialization.

---

## Target users

CEPIO serves both humans and machine consumers.

**Primary industrial users** are engineers, planners and operational leaders whose decisions require context across multiple systems, including reliability, maintenance, operations, process engineering, safety/integrity, drilling, subsurface and planning.

**Platform users** include industrial data architects, domain/ontology engineers, AI engineers, application developers, integration engineers and security/platform teams.

**Governance users** define technical authority, evidence, policy and execution boundaries.

**AI agents** are first-class software consumers, but industrial knowledge and execution authority remain separate.

```text
Knowledge != Authority
Recommendation != Execution
```

See [Target Users / Personas](docs/wiki/19-Target-Users-Personas.md).

---

## Competency and assurance

CEPIO maturity is not measured by ontology size.

```text
Persona
 -> Job / responsibility
 -> Decision
 -> Competency question
 -> Required capability and evidence
 -> Skill / Function / Decision / Action
 -> PASS / PARTIAL / FAIL / NOT_RUN
```

The assurance model progresses through:

1. semantic competency;
2. runtime competency;
3. procedural / Skill competency;
4. agent competency;
5. operational competency.

Generalization asks whether the capability remains reusable. Assurance asks whether the answer, recommendation or action is justified.

See [Competency & Assurance](docs/wiki/20-Competency-Assurance.md).

---

## Headless-first experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

A Reliability Engineer, Plant Manager, CFO and AI agent may receive different representations of the same operational reality while relying on the same governed evidence and authority model.

---

## Microsoft-native, not Microsoft-dependent

Microsoft is the primary reference ecosystem, but Microsoft services implement CEPIO capabilities rather than define CEPIO semantics.

| Microsoft capability | CEPIO role |
|---|---|
| **Fabric / OneLake / RTI** | enterprise context and operational/analytical source binding |
| **Fabric IQ / Ontology / Graph** | Microsoft-native semantic materialization |
| **Microsoft Foundry** | model/agent execution using CEPIO contracts and tools |
| **Entra** | authenticated human, application and agent identity |
| **Azure App Service / AKS** | reference hosting/deployment profiles |
| **PostgreSQL** | preferred durable memory / structured and full-text retrieval (mainline adapter pending) |
| **Purview** | governance/catalog/lineage bridge direction |

The CEPIO contract should remain portable across other industrial environments such as Cognite Data Fusion and OSDU-based stacks.

---

## Hosted interfaces

Current hosted target composition:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

The Management surface is observation-only. MCP uses host-injected authenticated actor context; models cannot self-assert CEPIO roles.

---

## Current v1 maturity score

The canonical governed scorecard currently reports:

> **69/100 — 69% toward CEPIO v1.0**

This score is pinned to its evidence snapshot and is independent of product-release qualification. New merges do not automatically earn points; score changes require a governed scorecard update.

See [v1.0 completion scorecard](docs/v1-completion-scorecard.md).

---

## Roadmap taxonomy

| Release | Label | Proof |
|---|---|---|
| **v0.4** | **FOUNDATION** | developers can build against a coherent CEPIO contract |
| **v0.5** | **CONNECT** | CEPIO operates over authoritative industrial truth |
| **v0.6** | **EXECUTE** | CEPIO produces governed, verified industrial outcomes |
| **v0.7** | **EXTEND** | independent teams can add Industry IQ safely |
| **v0.8** | **OPERATE** | an enterprise can depend on CEPIO operationally |
| **v0.9** | **GENERALIZE** | CEPIO is portable across enterprises/platform contexts |
| **v1.0** | **GUARANTEE** | stable production contracts and explicit guarantees |

The current product critical path remains **v0.5 CONNECT**.

See [Execution Roadmap](docs/roadmap.md).

---

## Standards federation

CEPIO federates strong external industry semantics instead of recreating them. Current or targeted references include `OSDU`, `ISA-95 / IEC 62264`, `ISO 15926`, `CFIHOS`, `DEXPI`, `BIM / IFC`, selected `FIBO` concepts, IADC, WITSML and PPDM where appropriate.

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable operating intelligence.**

---

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python examples/demo.py
```

Start the public API locally:

```bash
CEPIO_ENVIRONMENT=test \
CEPIO_DB_URL=memory:// \
CEPIO_AUTH_MODE=dev \
uvicorn cepio.public_api:app --reload
```

For the hosted three-surface composition, see the deployment and MCP documentation rather than assuming the development command above exposes Management or hosted MCP.

---

## Documentation

Start with:

- [Current State](docs/current-state.md)
- [CEPIO Documentation Index](docs/README.md)
- [Wiki](docs/wiki/Home.md)
- [Architecture](docs/architecture.md)
- [Execution Roadmap](docs/roadmap.md)
- [v1 Completion Scorecard](docs/v1-completion-scorecard.md)
- [Version Naming](docs/version-naming.md)
- [Release Manifest](RELEASE.md)

Documentation is part of CEPIO's engineering definition of done. Material capability, architecture, security, release or roadmap changes must update the appropriate narrative and focused technical documentation in the same PR.
