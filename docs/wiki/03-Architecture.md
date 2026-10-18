# Architecture

## Architecture North Star

> **Thin infrastructure. Thick industrial intelligence.**

CEPIO should remain thin in storage, hosting, model runtime and source-system duplication, while becoming thick in reusable industrial operating competence.

The architectural center of gravity is therefore not a proprietary data platform. It is a portable operating contract plus reusable Industry IQ.

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES · engineering systems
                         |
                         v
               REPLACEABLE BINDINGS
                         |
                         v
                THIN OPERATING CORE
 semantics · identity · state · time · evidence · provenance
 uncertainty · policy · authority · Functions · Decisions · Actions
                         |
                         v
                  THICK INDUSTRY IQ
 Skills · competency contracts · risk/failure patterns
 decision patterns · constraints · KPI/economic logic
 workflows · evaluations · domain competence
                         |
                         v
          HEADLESS / PERSONA-ADAPTIVE EXPERIENCE
 apps · copilots · agents · analytics · workflows
```

## Five-plane view

The existing five-plane model remains useful, but the new North Star changes where CEPIO should accumulate differentiated IP.

```text
Applications · Workspaces · Copilots · Agents
                       |
               EXPERIENCE PLANE
                       |
Skills · Functions · Decisions · Actions · Workflows
                       |
                  KINETIC PLANE
                       |
Objects · Relationships · Events · State · Evidence
                       |
                 SEMANTIC PLANE
                       |
Policy · Time · Provenance · Authority · Audit · Compatibility
                       |
                GOVERNANCE PLANE
                       |
SAP · PI · OSDU · Fabric · Cognite · P6 · MES
                       |
               INTEGRATION PLANE
```

The planes are runtime concerns. The product packaging should be understood as:

- **thin stable Core** across semantic, governance and kinetic primitives;
- **thick Industry IQ Packs** containing reusable industrial competence;
- **replaceable bindings** into data and operational platforms;
- **headless persona-adaptive experiences** above the contract.

## Thin operating core

Core should contain abstractions that remain stable across domains and platform choices:

- canonical identity;
- objects and relationships;
- events and operational state;
- valid time and transaction time;
- evidence and provenance;
- uncertainty/confidence;
- Functions;
- Decisions;
- governed Actions;
- policy and authority;
- audit;
- compatibility and migration contracts.

Core should not absorb every domain term, customer workflow or platform feature.

## Thick Industry IQ

CEPIO's differentiated intelligence should accumulate in reusable packs above Core:

- industrial Skills and procedures;
- competency questions and acceptance contracts;
- evidence requirements;
- failure and degradation patterns;
- risk/barrier patterns;
- decision and intervention patterns;
- operating constraints;
- KPI and economic logic;
- reusable workflow patterns;
- evaluation and assurance benchmarks;
- domain-specific semantic compositions.

The design objective is **more industrial competence with less Core churn**.

## Replaceable platform bindings

Bindings connect CEPIO to systems of record, systems of observation and data platforms.

Examples include:

- SAP S/4HANA / EAM;
- AVEVA PI or other historians;
- OSDU / Azure Data Manager for Energy;
- Microsoft Fabric / Fabric IQ;
- Cognite Data Fusion;
- Primavera P6;
- MES and engineering systems.

Bindings should preserve three invariants:

1. CEPIO canonical identity remains stable even when source identifiers change.
2. Source systems remain authoritative for the facts or transactions they own.
3. CEPIO records evidence, authorization, execution and reconciliation without unnecessary source duplication.

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable operating intelligence.**

## Experience plane: headless first

The experience plane contains:

- industrial applications;
- engineering workspaces;
- copilots;
- AI agents;
- analytics;
- domain-specific visualization.

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

The UI must not become a second source of business logic. Persona adaptation happens above the governed CEPIO contract.

## Kinetic plane

The kinetic plane defines what the enterprise can reason about and do:

- Skills;
- Functions;
- Decisions;
- recommendations;
- Actions;
- workflows;
- constraints;
- preconditions;
- approvals;
- verification and Outcomes.

The new North Star makes Skills and decision patterns especially important because they are reusable industrial competence rather than infrastructure.

## Semantic plane

The semantic plane provides the canonical meaning required for cross-system reasoning:

- objects;
- relationships;
- properties;
- events;
- state;
- observations;
- evidence;
- KPIs and risks.

The semantic model should support competency and reasoning contracts, not grow as a catalog of every industry noun.

## Governance plane

The governance plane makes industrial intelligence trustworthy:

- authenticated actor identity;
- policy;
- decision and execution authority;
- valid and transaction time;
- provenance;
- audit;
- compatibility;
- migration;
- evidence lineage.

Knowledge is distinct from authority, and recommendation is distinct from permission to execute.

## Runtime architecture

```text
                         CEPIO Runtime
                              |
      +-----------------------+------------------------+
      |                       |                        |
Object/Event State      Evidence/Provenance      Audit/Outcome
      |                       |                        |
      +-----------------------+------------------------+
                              |
                     Ontology / Type Registry
                              |
                        Policy / Authority
                              |
          +-------------------+-------------------+
          |                   |                   |
       Skills             Functions          Decisions
          |                   |                   |
          +-------------------+-------------------+
                              |
                     Workflow / Action Runtime
                              |
                       Adapter Boundary
        SAP · PI · OSDU · Fabric · Cognite · P6 · others
```

## Microsoft-native, not Microsoft-dependent

Microsoft remains the primary reference ecosystem for deployment and realization:

- Fabric / OneLake / RTI for data and operational context;
- Fabric IQ for semantic materialization;
- Foundry for model and agent execution;
- Entra for authenticated identity;
- App Service / AKS for hosting.

These services implement CEPIO capabilities; they do not define CEPIO industrial meaning. The same CEPIO competency, Skill and Decision contracts should be portable to alternative data environments.

## Architecture success criteria

The architecture is moving in the right direction when:

- new industrial domains require fewer changes to Core;
- more functionality is delivered through Industry IQ Packs rather than infrastructure growth;
- the same competency/Skill/Decision contract works over different platform bindings;
- source-system facts remain authoritative and traceable;
- customer-specific operating knowledge stays isolated in profiles/extensions;
- experiences remain headless and persona-adaptive;
- agent autonomy increases only with equivalent evidence, authority and assurance controls.
