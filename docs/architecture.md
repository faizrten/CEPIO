# CEPIO Architecture

## Design target

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

CEPIO is not intended to become a proprietary data platform, model runtime or duplicate system of record. It provides a stable, governed industrial operating contract over replaceable enterprise systems and data platforms, then concentrates differentiated value in reusable industrial competence.

## Product architecture

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
 Skills · competency contracts · risk/failure patterns
 decision patterns · constraints · KPI/economic logic
 workflows · evaluation benchmarks
                         |
                         v
          Headless persona-adaptive experiences
```

The governing rule is:

> **Keep infrastructure thin and replaceable; concentrate CEPIO IP in reusable industrial intelligence.**

## Thin operating core

The Core provides abstractions that should remain stable across domains, customers and platform choices:

- canonical object and relationship identity;
- events and operational state;
- valid time and transaction time;
- evidence and provenance;
- uncertainty/confidence;
- Functions and Decisions;
- governed Actions;
- policy, authority and audit;
- compatibility and migration contracts.

The Core should not absorb every customer term, workflow or external platform feature.

## Thick Industry IQ

Industry IQ Packs carry reusable industrial operating competence, including:

- Skills and procedures;
- competency questions;
- evidence requirements;
- failure and degradation patterns;
- risk and barrier patterns;
- decision/intervention patterns;
- constraints;
- KPI and economic logic;
- workflow patterns;
- evaluation and assurance benchmarks;
- domain semantic compositions.

The architectural goal is rising competency coverage with decreasing Core churn.

## Five-plane runtime view

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

The five planes describe runtime responsibilities. They do not imply that CEPIO should own the infrastructure implementing every plane.

## Runtime components

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

## Persistence boundary

Domain-facing repository interfaces isolate CEPIO contracts from storage technology. In-memory and SQLite implementations remain reference backends; enterprise persistence may be implemented through different technology choices without changing the CEPIO operating contract.

## Platform binding strategy

Bindings are replaceable. Use the architectural rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable operating intelligence.**

Examples:

- OSDU or ADME remains authoritative for subsurface technical data structures;
- SAP remains authoritative for enterprise transactions it owns;
- PI or another historian remains authoritative for raw time-series observations;
- Fabric or Cognite may supply enterprise context and data-product capabilities;
- CEPIO adds reusable operating semantics, evidence requirements, Skills, Decisions, authority and governed action patterns above them.

## Source-system invariants

1. CEPIO canonical identity remains stable when external identifiers change.
2. External facts and transactions remain traceable to their authoritative source.
3. Writeback is never invoked before CEPIO authorization and validation.
4. External execution is verified and reconciled back into CEPIO audit/evidence.
5. Source data is not persistently duplicated without a clear runtime reason.

## Headless-first experience

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

Applications, copilots and agents consume the same governed CEPIO contract. Persona adaptation belongs in the experience layer rather than in competing versions of enterprise truth.

## Agent boundary

AI agents are software consumers of CEPIO. They can be given broad reasoning context while remaining constrained by authenticated identity, evidence visibility, policy and action authority.

The core principle is:

```text
Knowledge != Authority
Recommendation != Execution
```

## Microsoft-native, not Microsoft-dependent

Microsoft Fabric, Fabric IQ, Foundry, Entra, App Service and AKS are the primary reference implementation ecosystem. They may implement CEPIO capabilities but do not define CEPIO industrial semantics.

The same competency, Skill and Decision contracts should remain portable across alternative environments such as Cognite Data Fusion and OSDU-based stacks.

## Architecture success criteria

CEPIO architecture is improving when:

- Core remains stable as domains expand;
- more value is delivered through reusable Industry IQ Packs;
- competency coverage rises;
- the same Skill/Decision contract works over different bindings;
- customer-specific knowledge stays isolated in profiles/private extensions;
- humans and agents receive evidence-backed, policy-bounded context;
- verified outcomes feed future evaluation and learning.
