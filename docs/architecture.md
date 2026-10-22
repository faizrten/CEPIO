# CEPIO Architecture

## Design target

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

CEPIO is not intended to become a proprietary data platform, model runtime, search engine or duplicate system of record. It provides a stable, governed industrial operating contract over replaceable enterprise systems and platform services, then concentrates differentiated value in reusable industrial competence.

The architecture is Microsoft-native in reference implementation while remaining source-, platform- and model-neutral at the CEPIO contract boundary.

For Microsoft-hosted agent scenarios:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

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
 capabilities · Skills · competencies · performance contracts
 failure/risk/decision patterns · constraints · KPI/economic logic
 workflows · assurance/evaluation contracts
                         |
                         v
        Governed intelligence/context control plane
 Capability Registry · Memory · Retrieval · Compiled Industry IQ
                         |
                         v
              Protocol / management surfaces
 REST Application Contract · Management Contract · MCP
                         |
                         v
        Apps · Studio · copilots · agents · workflows
```

The governing architecture rule is:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

## Runtime planes

The original five-plane model remains useful, but it is now augmented by an explicit intelligence/control-plane view.

```text
Apps · Studio · Copilots · Agents · Analytics
                       |
               EXPERIENCE PLANE
                       |
Skills · Functions · Decisions · Actions · Workflows
                       |
                  KINETIC PLANE
                       |
Objects · Relationships · Events · State · Evidence · Performance
                       |
                 SEMANTIC PLANE
                       |
Policy · Authority · Time · Provenance · Audit · Compatibility
                       |
                GOVERNANCE PLANE
                       |
SAP · PI · OSDU · Fabric · Cognite · P6 · MES
                       |
               INTEGRATION PLANE
```

Cross-cutting those planes are the **Industry IQ control-plane capabilities** that make industrial knowledge reusable and bounded:

```text
Capability Registry
      |
      +--> Industry IQ Pack Registry / trusted catalogue
      +--> Domain Onboarding / Compounding Intelligence
      +--> Memory
      +--> Retrieval & Indexing
      +--> Compiled Industry IQ
      +--> Competency / Assurance
      +--> Performance Contracts / reference packs
```

These are not separate systems of industrial truth. They govern how reusable industrial competence is admitted, selected, compiled, executed and assured.

## Thin operating core

Core should contain abstractions that remain stable across domains, customers and platform choices:

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

Core should not absorb every domain term, customer workflow, source field or platform feature.

## Thick Industry IQ

CEPIO's differentiated intelligence should accumulate above Core in reusable capability and pack contracts:

- domain semantic compositions;
- personas and competency questions;
- evidence requirements;
- industrial Skills and procedures;
- failure and degradation patterns;
- risk/barrier patterns;
- decision/intervention patterns;
- operating constraints;
- KPI, performance and economic logic;
- reusable workflow patterns;
- evaluation and assurance benchmarks.

The product-design objective is:

> **More industrial competency with less Core churn.**

## Capability Registry and compounding intelligence

The Capability Registry answers what CEPIO can legitimately claim it knows how to do, where that capability was proven and what evidence supports it.

```text
Domain Onboarding
      |
      v
qualified capability evidence
      |
      v
Capability Registry
      |
reuse / promotion candidate
      |
      v
cross-domain regression
      |
      v
human-governed promotion
```

This remains distinct from:

- **Industry IQ Pack Registry** — executable reusable industrial intelligence that is deployed;
- **Skill Registry** — procedures that are admissible/executable in a concrete runtime;
- **Capability Registry** — evidence-backed product competence claims.

Customer/profile evidence cannot silently justify global Core/Common promotion.

## Memory and context

CEPIO separates durable knowledge from ephemeral model/agent context.

Durable memory kinds include Semantic, Procedural, Episodic and Profile memory. Working context is assembled for one execution under explicit budgets.

Core invariant:

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

PROFILE/customer knowledge remains explicitly tenant-bound.

## Retrieval and indexing

Retrieval is a governed control plane, not a new source of truth.

```text
request
 -> CapabilityRouter
 -> bounded RetrievalPlan
 -> structured / lexical / vector / graph backends
 -> deterministic rank fusion
 -> tenant/expiry re-check
 -> required-evidence qualification
 -> ContextAssembler
```

Indexes are rebuildable projections. Memory/source evidence remains authoritative.

PostgreSQL is the preferred next durable memory/retrieval backend; the independent contract remains semantic authority. CEPIO's existing SQLite repository remains live until the PostgreSQL adapter is qualified.

## Compiled Industry IQ

Compiled Industry IQ accelerates reusable capability activation:

```text
CapabilityRoutingResult
       |
       v
CompiledCapabilityResolver
       |
  hit / deterministic compile
       |
       v
immutable compiled capability bundle
       |
       v
reasoning / retrieval / Skill / workflow runtime
```

Compiled bundles and caches are deterministic acceleration projections. The Capability Registry remains authoritative.

`PROFILE` capabilities/customer context are hard-excluded from the shared compiled cache.

## Performance intelligence

Performance Contracts provide a reusable grammar for objectives, KRs, KPIs, guardrails, accountability, contribution relationships and governed response bindings.

Specialization follows:

```text
Industry Reference
      -> Organization
      -> Role / Persona
      -> Individual
```

Sparse patches/suppressions avoid copying complete contracts while preserving fail-closed graph validation and auditability.

Industry Performance Reference Packs provide organization-neutral patterns. Customer formulas, targets, thresholds, organizational structure and data bindings remain customer-owned specialization.

## Binding boundary

Bindings connect CEPIO to systems of record, observation and enterprise context.

Examples include:

- SAP S/4HANA / EAM;
- AVEVA PI or other historians;
- OSDU / Azure Data Manager for Energy;
- Microsoft Fabric / Fabric IQ;
- Cognite Data Fusion;
- Primavera P6;
- MES and engineering systems.

Bindings should preserve these invariants:

1. CEPIO canonical identity remains stable when source identifiers change.
2. Source systems remain authoritative for facts/transactions they own.
3. Evidence remains traceable to source.
4. External side effects occur only through governed CEPIO authority/action paths.
5. External success is verified/reconciled rather than inferred from local success.
6. Raw source data is not persistently duplicated without a clear runtime reason.

## Hosted protocol architecture

The hosted CEPIO composition now separates three first-class surfaces:

```text
/api/v1/*          Application Contract / REST
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

### Application Contract

REST, SDK and MCP protocol projections converge on shared CEPIO application/runtime contracts rather than implementing independent semantics.

### Management Contract

Management is a separate control-plane projection for runtime health/capability inspection. The remote surface is authenticated and read-only. It must not become a back door around application policy or an ungoverned remote administration API.

### MCP

The hosted MCP gateway uses authenticated host-injected actor identity. Tool callers do not provide their own CEPIO roles.

The existence of an action tool does not confer action authority; normal CEPIO policy and preconditions still apply.

## Microsoft-native industrial agency

The reference boundary is:

```text
Microsoft Foundry / Copilot
        |
 generic agent execution
        |
        v
 authenticated CEPIO MCP / Application Contract
        |
        v
 CEPIO industrial agency
 semantics · evidence · Skills · Decisions
 policy · authority · Actions · Outcomes
```

Do not build duplicate generic model-routing/session/agent infrastructure inside CEPIO unless a concrete industrial contract cannot be implemented through existing platform capabilities.

## Persistence boundary

Domain-facing repositories and logical store protocols isolate CEPIO contracts from storage technology.

Current/reference implementations include in-memory and SQLite storage for several contracts. PostgreSQL is the preferred next durable memory/retrieval adapter, not yet qualified for the hosted CEPIO runtime. Future Fabric/graph/distributed backends must implement source-neutral logical contracts.

## Headless-first experience

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

Persona adaptation belongs in applications, Studio, copilots and agents above the governed CEPIO contract. The UI must not become a competing store of industrial business logic.

## Security and authority boundaries

Core invariants:

```text
Knowledge != Authority
Recommendation != Execution
Cache != Authority
Index != Source of Truth
Model Output != Evidence
```

Actor identity must originate from trusted authentication context. Policy/authority is re-evaluated at sensitive execution boundaries.

## Architecture success criteria

CEPIO architecture is improving when:

- new industrial domains require fewer changes to Core;
- more value is delivered through reusable Industry IQ capabilities/packs;
- competency coverage rises;
- the same competency/Skill/Decision contract works over different platform bindings;
- customer/profile knowledge remains isolated unless intentionally generalized;
- working context remains bounded as durable Industry IQ grows;
- caches/indexes remain rebuildable projections rather than authority;
- agent autonomy increases only with equivalent evidence, identity, policy and assurance controls;
- verified Outcomes feed future evaluation and governed learning.

## Current architecture status

See [`current-state.md`](current-state.md) for the dated mainline capability snapshot, [`roadmap.md`](roadmap.md) for release gates and [`v1-completion-scorecard.md`](v1-completion-scorecard.md) for governed v1 maturity scoring.
