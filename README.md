# CEPIO

**Common Energy & Process Industry Ontology**

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

CEPIO gives humans, applications and AI agents a shared operating understanding of industrial assets, processes, work, risk, decisions and actions while preserving each enterprise's proprietary operating knowledge.

## North Star

> **Thin infrastructure. Thick industrial intelligence.**

Frontier models provide general intelligence. Data and industrial platforms provide storage, compute and enterprise context. CEPIO provides reusable **industrial operating competence**:

- industrial semantics and operational state;
- evidence requirements and provenance;
- uncertainty and confidence;
- Skills and procedural knowledge;
- failure, risk and constraint patterns;
- KPI and economic logic;
- decision patterns and authority;
- governed Actions and workflows;
- competency and evaluation benchmarks.

The product objective is not to recreate Fabric, Cognite, OSDU, SAP, PI, a graph database, an agent platform or a model runtime. CEPIO binds those systems behind a stable industrial operating contract.

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES · engineering systems
                         |
                         v
               Replaceable bindings
                         |
                         v
              Thin CEPIO operating core
 semantics · state · evidence · time · provenance · policy · authority
                         |
                         v
                 Thick Industry IQ
 skills · competencies · decision patterns · risk/failure patterns
 constraints · KPI/economic logic · workflows · evaluations
                         |
                         v
       Humans · applications · copilots · AI agents
                         |
                         v
                 Governed outcomes
```

**Palantir Ontology remains a useful capability benchmark, not CEPIO's product identity.** CEPIO's identity is an open, portable Industrial Operating Intelligence layer specialized for Energy & Process Industries.

For Microsoft deployments, CEPIO can be understood as the layer that turns general Microsoft/Fabric/Foundry intelligence into **Industrial IQ**. Microsoft-native does not mean Microsoft-dependent: the CEPIO contract must remain portable across platform environments.

---

## Current release

Current Python package version: **`0.4.0`**.  
Release designation: **CEPIO v0.4 — Developer Preview**.

v0.4 qualifies the core developer/runtime contract: canonical semantics, temporal state and provenance, Functions, Decisions, governed Actions, public `/api/v1`, Entra-aware security boundaries, Microsoft bindings, reference deployment profiles and observability.

Repository `main` may contain capabilities pulled forward from later roadmap stages. Component completion does not automatically change the published product-release guarantee.

Start with:

- [Developer Preview guide](docs/developer-preview.md)
- [Release manifest and support boundary](RELEASE.md)
- [Execution roadmap](docs/roadmap.md)
- [CEPIO Wiki](docs/wiki/Home.md)
- [Target Users / Personas](docs/wiki/19-Target-Users-Personas.md)
- [Competency & Assurance](docs/wiki/20-Competency-Assurance.md)

---

## Product model

CEPIO separates four durable concerns:

```text
1. Replaceable platform bindings
   Where enterprise context comes from

2. Thin operating core
   Stable semantics, identity, state, time, evidence, provenance,
   uncertainty, policy, authority, Functions, Decisions and Actions

3. Thick Industry IQ Packs
   Reusable domain competence: Skills, competency questions,
   decision/risk/failure patterns, constraints, KPI/economic logic,
   workflows and evaluation benchmarks

4. Headless experiences
   Persona-adaptive apps, copilots, agents, analytics and workflows
```

The governing architecture rule is:

> **Keep infrastructure thin and replaceable; concentrate CEPIO IP in reusable industrial intelligence.**

### What CEPIO owns

CEPIO should own the reusable industrial operating contract:

- canonical industrial meaning;
- cross-system identity;
- operational state and time;
- evidence and provenance requirements;
- uncertainty/confidence abstractions;
- industrial Functions and Skills;
- decision and authority patterns;
- governed Actions and workflow semantics;
- competency and assurance contracts;
- outcome/evaluation semantics.

### What CEPIO normally binds rather than owns

- raw historian measurements;
- ERP transactions;
- seismic files and reservoir grids;
- engineering documents and 3D files;
- data-lake or warehouse storage;
- model hosting and frontier-model capability;
- source-native process models;
- customer-specific proprietary operating logic unless explicitly packaged as a customer profile.

---

## Operating loop

```text
Understand -> Reason -> Decide -> Act -> Learn
```

The detailed governed loop is:

```text
Observe -> Understand -> Reason -> Decide -> Recommend
        -> Authorize -> Act -> Verify -> Learn
```

CEPIO exists to make that loop reusable, evidence-backed and governed across industrial systems.

---

## Target users

CEPIO serves both humans and machine consumers.

**Primary industrial users** are engineers, planners and operational leaders whose decisions require context across multiple systems, including reliability, maintenance, operations, process engineering, safety/integrity, planning and domain-specialist roles.

**Platform users** include industrial data architects, ontology/domain engineers, AI engineers, application developers, integration engineers and platform/security teams that build governed industrial applications and agents on CEPIO.

**AI agents** are first-class software consumers, but they receive knowledge and execution authority separately. Persona context never grants permission to act.

See [Target Users / Personas](docs/wiki/19-Target-Users-Personas.md).

---

## Competency as a product quality metric

CEPIO maturity is not measured by ontology size.

```text
Persona
  -> Job / responsibility
  -> Decision
  -> Competency question
  -> Required CEPIO capabilities
  -> Evidence / Skill / Function / Decision / Action
  -> PASS / PARTIAL / FAIL / NOT_RUN
```

The assurance model progresses through:

1. semantic competency;
2. runtime competency;
3. procedural / Skill competency;
4. agent competency;
5. operational competency.

The Generalization Lab and Competency Harness exist to prove reusable industrial competence without contaminating Core with customer-specific vocabulary.

See [Competency & Assurance](docs/wiki/20-Competency-Assurance.md) and [Generalization Harness](docs/generalization-harness.md).

---

## Headless-first experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

Applications, copilots and agents consume the same governed CEPIO contract while presenting context appropriate to the persona and decision at hand.

---

## Microsoft-native, not Microsoft-dependent

Microsoft remains the primary reference implementation ecosystem:

| Platform | CEPIO role |
|---|---|
| **Fabric / OneLake / RTI** | enterprise data and operational/analytical context |
| **Fabric IQ / Ontology / Graph** | Microsoft-native semantic materialization |
| **Microsoft Foundry** | model/agent execution grounded through CEPIO tools |
| **Microsoft Entra** | authenticated human, application and agent identity |
| **Azure App Service / AKS** | reference hosting profiles |
| **Purview** | governance/catalog/lineage bridge direction |

But Microsoft services implement CEPIO capabilities; they do not define CEPIO industrial semantics. The same operating contract should be able to bind to other industrial data environments such as Cognite Data Fusion and OSDU-based platforms.

---

## Standards federation

CEPIO federates strong industry standards instead of recreating them. Current or targeted references include `OSDU`, `ISA-95 / IEC 62264`, `ISO 15926`, `CFIHOS`, `DEXPI`, `BIM / IFC`, selected `FIBO` concepts, IADC, WITSML and PPDM where appropriate.

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

Open `http://localhost:8000/docs` and use `/api/v1/...` routes.

---

## Repository structure

```text
ontologies/                     canonical CEPIO semantic modules
ontology-modules.yaml           module catalogue, versions and dependencies
mappings/                       source mappings + canonical property contract
shapes/                         SHACL validation contracts
generalization/                 archetypes, personas, competency and gap packs
src/cepio/                      runtime, policy, query, Skills, workflow, SDK
src/cepio/integrations/         platform/source bindings
openapi/                        accepted public API v1 route baseline
clients/                        reference clients
compatibility/                  compatibility baselines + migrations
actions/                        declarative Actions
policies/                       authorization examples
deploy/                         reference deployment profiles
tests/                          semantic/runtime/platform/assurance tests
docs/                           architecture, domains, roadmap, wiki
```

---

## Roadmap

The roadmap is organized around progressively stronger operating proof:

- **v0.4 — Foundation is usable:** Developer Preview qualified.
- **v0.5 — Connect:** live industrial integration and governed writeback.
- **v0.6 — Execute:** Kinetic Runtime + reference industrial applications.
- **v0.7 — Extend:** Industrial Developer Platform.
- **v0.8 — Operate:** enterprise runtime, HA, resilience, SLOs and DR.
- **v0.9 — Generalize:** real second-enterprise portability and domain reuse.
- **v1.0 — Guarantee:** stable production contracts and explicit guarantees.

See [docs/roadmap.md](docs/roadmap.md) for the authoritative execution plan.

---

## Design philosophy

Industrial enterprises already have data platforms, source systems and increasingly capable frontier models. CEPIO should not compete by rebuilding those layers.

Its differentiation is reusable industrial operating intelligence:

```text
GENERAL INTELLIGENCE
        +
ENTERPRISE CONTEXT
        +
CEPIO INDUSTRY IQ
        +
GOVERNANCE
        =
SAFE INDUSTRIAL OPERATING INTELLIGENCE
```

That is the direction of CEPIO.
