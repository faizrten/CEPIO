# CEPIO Wiki

**CEPIO — Common Energy & Process Industry Ontology**

> **An industry operating ontology for Energy & Process Industries — connecting enterprise data, operational state, industrial semantics, AI reasoning, decisions and governed action.**

## North Star

CEPIO aims to provide the same **class of enterprise operating abstraction** that Palantir Ontology provides, specialized for Energy & Process Industries and natively realized across the Microsoft ecosystem.

The governing principle is simple:

> **Applications and AI agents interact with CEPIO concepts, not directly with source-system schemas.**

CEPIO therefore sits between enterprise reality and the applications, agents and workflows that operate on it.

```text
Enterprise reality
      |
      v
SAP · AVEVA PI · OSDU · P6 · MES · SQL · Fabric · other systems
      |
      v
+-------------------------------------------------------+
|                         CEPIO                          |
| Objects · Relationships · Properties · Events · State |
| Time · Provenance · Functions · Decisions · Actions   |
| Policy · Audit · Versioning · Migration contracts     |
+-----------------------------+-------------------------+
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
             Applications             AI Agents
                  |                       |
                  +-----------+-----------+
                              v
                     Governed operations
```

## What CEPIO is

CEPIO is an **industrial operating abstraction**. It defines the meaning and operating contract for industrial objects, relationships, state, time, logic, decisions and actions while allowing underlying technology platforms and source systems to evolve independently.

CEPIO is designed to answer questions such as:

- What industrial object does this data represent?
- How is it related to the rest of the enterprise?
- What is its current state?
- What was its state at a specific valid time?
- What did CEPIO know at a specific transaction time?
- Where did each value come from?
- Which events produced a derived state?
- Which functions or calculations are applicable?
- Which decision follows from the available evidence?
- Which action is recommended?
- Who or what is authorized to execute that action?
- How can ontology evolution occur without silently breaking consumers?

## What CEPIO is not

CEPIO is not:

- another data lake;
- a replacement for SAP, PI, OSDU, Fabric, P6 or MES;
- a generic graph database product;
- a generic RDF/OWL standards project;
- an agent framework;
- a plant-control or safety-instrumented system;
- a UI product by itself.

CEPIO defines the **industrial semantic and operating contract**. Platforms implement it; applications consume it.

## Current status

**Published release designation:** v0.4.0 — Developer Preview. The [release manifest](../../RELEASE.md) defines the supported boundary, including the public `/api/v1` interface, canonical semantics, temporal/provenance capabilities, governed Functions/Decisions/Actions, Microsoft bindings, reference hosting and observability.

Current repository implementation also includes incremental Skill binding/preflight, durable workflow, resilience, external-verification and constrained Operator work. Component versions and repository implementation do not expand the published release guarantees automatically. See [Functions, Decisions and Actions](08-Functions-Decisions-Actions.md) and the [technical documentation index](../README.md) for scoped contracts.

[Target Users / Personas](19-Target-Users-Personas.md) describes the industrial users and platform builders CEPIO is intended to serve. The checked-in catalogs model 24 drilling and 26 refinery persona entries; they do not establish delivered applications for every role.

[Competency & Assurance](20-Competency-Assurance.md) is a first-class acceptance discipline. Drilling persona pack v0.3 has a checked-in 14/14 semantic PASS expectation; the operational fixture separately expects five assurance gates to pass. Those scopes do not establish complete runtime coverage or production readiness.

## Operating loop

```text
Observe -> Understand -> Reason -> Decide -> Recommend -> Authorize -> Act -> Observe outcome
```

CEPIO's purpose is not merely to describe the enterprise. It is to create a governed operational layer through which people, applications and AI systems can understand and act on the enterprise consistently.

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

Documentation is part of CEPIO's engineering definition of done.

Material changes to ontology semantics, public interfaces, runtime behavior, integrations, deployment, security/governance, examples, release status or roadmap state must update the relevant focused technical documentation and/or wiki page in the **same pull request**.

If a change genuinely has no documentation impact, the PR must explicitly select **No documentation impact** and explain why. The repository pull-request template requires this declaration.

See the [Developer Guide](15-Developer-Guide.md) for the detailed documentation checklist.

## Canonical source of truth

The GitHub repository remains authoritative for executable contracts and implementation details. This wiki is the **narrative and navigational layer** over those contracts.

Key repository references:

- `README.md`
- `ontology-modules.yaml`
- `ontologies/`
- `mappings/`
- `shapes/`
- `docs/architecture.md`
- `docs/query-contract.md`
- `docs/temporal-state-projection.md`
- `docs/foundry-mcp.md`
- `docs/microsoft-platform-extension.md`
- `docs/integrations/`
- `docs/roadmap.md`
