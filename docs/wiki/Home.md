# CEPIO Wiki

**CEPIO — Common Energy & Process Industry Ontology**

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

## North Star

> **Thin infrastructure. Thick industrial intelligence.**

Frontier models supply general intelligence. Data and industrial platforms supply storage, compute and enterprise context. CEPIO supplies reusable industrial operating competence: semantics, evidence requirements, Skills, failure/risk patterns, decision patterns, authority, Actions, workflows and competency/evaluation contracts.

Palantir Ontology remains a useful architectural benchmark, but it is no longer CEPIO's product identity. CEPIO's identity is a portable **Industrial Operating Intelligence / Industry IQ** layer specialized for Energy & Process Industries.

For Microsoft deployments, CEPIO can be understood as the layer that turns general Microsoft/Fabric/Foundry capability into **Industrial IQ**. Microsoft-native does not mean Microsoft-dependent.

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
 semantics · state · evidence · time · provenance · uncertainty
 policy · authority · Functions · Decisions · Actions
                         |
                         v
                 Thick Industry IQ
 Skills · competencies · decision/risk/failure patterns
 constraints · KPI/economic logic · workflows · evaluations
                         |
                         v
          Headless, persona-adaptive experiences
 apps · copilots · agents · analytics · workflows
                         |
                         v
                 Governed outcomes
```

The governing architecture rule is:

> **Keep infrastructure thin and replaceable; concentrate CEPIO IP in reusable industrial intelligence.**

## What CEPIO is

CEPIO is a governed industrial operating intelligence layer that lets humans, applications and AI agents understand, reason over, decide against and safely act upon industrial enterprise context through a stable contract.

CEPIO should answer questions such as:

- What industrial object does this evidence refer to?
- What is its current and historical state?
- What evidence supports that state?
- What uncertainty remains?
- What failure, risk, constraint or economic pattern applies?
- Which Skill, Function or decision pattern is relevant?
- What options exist and what are their consequences?
- Who is authorized to decide or act?
- What happened after execution?
- Did the intervention work?

## What CEPIO is not

CEPIO is not:

- another data lake or warehouse;
- a replacement for SAP, PI, OSDU, Fabric, Cognite, P6 or MES;
- a generic graph database product;
- a frontier-model or model-hosting platform;
- a generic agent framework;
- a plant-control or safety-instrumented system;
- a monolithic UI product.

CEPIO binds these layers and concentrates reusable industrial operating intelligence above them.

## Current status

**Published release designation:** v0.4.0 — Developer Preview.

The published boundary includes canonical semantics, temporal/provenance capabilities, governed Functions/Decisions/Actions, `/api/v1`, Microsoft bindings, reference hosting and observability. Repository `main` also contains capabilities pulled forward from later stages; implementation on `main` does not automatically expand the published release guarantee.

## Target users

CEPIO serves four human user classes plus machine consumers:

1. industrial decision-makers — engineers, planners and operational leaders;
2. industrial application and AI builders;
3. industrial platform/data/integration teams;
4. governance and assurance users;
5. AI agents operating under authenticated, policy-bounded authority.

The primary near-term product center of gravity is cross-system industrial decision work: reliability, maintenance, operations, process engineering, safety/integrity and planning.

See [Target Users / Personas](19-Target-Users-Personas.md).

## Competency & Assurance

Competency is a first-class product-quality mechanism, not a side experiment.

```text
Persona
  -> Responsibility
  -> Decision
  -> Competency Question
  -> Required CEPIO capabilities
  -> Evidence / Skill / Function / Decision / Action
  -> PASS / PARTIAL / FAIL / NOT_RUN
```

CEPIO assurance progresses through semantic, runtime, procedural/Skill, agent and operational competency. Generalization measures reuse; assurance measures whether a claim or action is justified.

See [Competency & Assurance](20-Competency-Assurance.md).

## Operating loop

```text
Understand -> Reason -> Decide -> Act -> Learn
```

Expanded governed loop:

```text
Observe -> Understand -> Reason -> Decide -> Recommend
        -> Authorize -> Act -> Verify -> Learn
```

## Experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

The UI is therefore not the architecture. Apps, copilots and agents consume the same governed operating contract and adapt the experience to the persona and decision.

## Wiki map

### Start here

1. [CEPIO Overview](01-Overview.md)
2. [Core Concepts](02-Core-Concepts.md)
3. [Architecture](03-Architecture.md)
4. [Ontology Model](04-Ontology-Model.md)
5. [Runtime](05-Runtime.md)

### Interfaces

6. [API, SDK and MCP](06-API-SDK-MCP.md)
7. [Query Model](07-Query-Model.md)
8. [Functions, Decisions and Actions](08-Functions-Decisions-Actions.md)

### Data, time and trust

9. [Temporal State and Provenance](09-Temporal-State-Provenance.md)
10. [Integration Architecture](10-Integration-Architecture.md)
11. [Microsoft Platform Extension](11-Microsoft-Platform.md)
12. [Standards Federation](12-Standards-Federation.md)

### Operations and engineering

13. [Security and Governance](13-Security-Governance.md)
14. [Deployment and Operations](14-Deployment-Operations.md)
15. [Developer Guide](15-Developer-Guide.md)
16. [Reference Scenarios](16-Reference-Scenarios.md)
17. [Roadmap to v1.0](17-Roadmap.md)
18. [Glossary](18-Glossary.md)

### Users and acceptance

19. [Target Users / Personas](19-Target-Users-Personas.md)
20. [Competency & Assurance](20-Competency-Assurance.md)

## Documentation governance

Documentation is part of CEPIO's engineering definition of done. Material changes to semantics, public interfaces, runtime behavior, integrations, security/governance, product positioning, release status or roadmap state must update the relevant documentation in the same pull request.

## Canonical source of truth

The GitHub repository remains authoritative for executable contracts and implementation details. The wiki is the narrative and navigational layer over those contracts.

Key references:

- `README.md`
- `RELEASE.md`
- `ontology-modules.yaml`
- `ontologies/`
- `generalization/`
- `docs/architecture.md`
- `docs/generalization-harness.md`
- `docs/roadmap.md`
