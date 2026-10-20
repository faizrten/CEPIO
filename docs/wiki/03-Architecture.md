# Architecture

## Architecture North Star

> **Thin infrastructure. Thick Industry IQ.**

CEPIO should remain thin in storage, hosting, search/index infrastructure, model runtime and source-system duplication while becoming thick in reusable industrial operating competence.

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES
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
 capabilities · Skills · competency contracts · performance contracts
 risk/failure/decision patterns · constraints · KPI/economic logic
 workflows · assurance/evaluation contracts
                         |
                         v
         INTELLIGENCE / CONTEXT CONTROL PLANE
 Capability Registry · Memory · Retrieval · Compiled Industry IQ
                         |
                         v
               REST · MANAGEMENT · MCP
                         |
                         v
          HEADLESS / PERSONA-ADAPTIVE EXPERIENCE
```

For Microsoft-hosted agent workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

## Five-plane runtime view

```text
Applications · Studio · Copilots · Agents
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

The five planes describe runtime responsibilities. They do **not** mean CEPIO must own the physical infrastructure implementing every plane.

## Intelligence/control-plane view

Several newer capabilities cut across the five planes:

```text
Capability Registry
      |
      +-- Industry IQ Pack Registry / trusted catalogue
      +-- Domain Onboarding / Compounding Intelligence
      +-- Memory & Context
      +-- Retrieval & Indexing
      +-- Compiled Industry IQ
      +-- Competency & Assurance
      +-- Performance Contracts / reference packs
      +-- Management Contract
```

These capabilities govern how industrial intelligence is admitted, selected, compiled, specialized, executed and assured.

## Thin operating core

Core should contain stable cross-domain abstractions:

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
- compatibility/migration contracts.

Core should not absorb every source field, customer workflow or platform feature.

## Thick Industry IQ

Reusable Industry IQ should contain:

- domain semantic compositions;
- personas and competency questions;
- evidence requirements;
- Skills/procedures;
- failure/degradation/risk patterns;
- decision/intervention patterns;
- operating constraints;
- KPI/performance/economic logic;
- workflow patterns;
- evaluation and assurance benchmarks.

The objective is **more industrial competence with less Core churn**.

## Capability Registry and compounding intelligence

The Capability Registry records evidence-backed competence claims. It remains distinct from the Industry IQ Pack Registry and Skill Registry.

```text
Domain Onboarding
 -> qualified evidence
 -> Capability Registry
 -> reuse/promotion candidate
 -> cross-domain regression
 -> human-governed promotion
```

PROFILE/customer evidence cannot silently promote global Core/Common capability.

## Memory and context

Durable Industry IQ and per-task working context are separate.

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

Semantic, Procedural, Episodic and Profile memory records remain governed by ownership/tenant boundaries. Working context is assembled under explicit budgets.

## Retrieval and indexing

Retrieval routes by governed capability and remains bounded:

```text
request
 -> CapabilityRouter
 -> bounded RetrievalPlan
 -> structured / lexical / vector / graph backends
 -> deterministic fusion
 -> tenant/expiry re-check
 -> ContextAssembler
```

Indexes are rebuildable projections, not memory truth. Azure AI Search is one optional implementation behind the same logical contract.

## Compiled Industry IQ

Compiled Industry IQ deterministically creates reusable runtime bundles and uses bounded cache acceleration.

- Capability Registry remains authoritative.
- cache loss must not alter semantics;
- unrelated capability growth should not invalidate stable capability bundles unnecessarily;
- PROFILE/customer context is prohibited from shared compilation.

## Performance intelligence

Performance Contracts connect industrial state to objectives, KRs, KPIs, guardrails, accountability, contributions and governed response bindings.

Specialization follows:

```text
Industry reference -> Organization -> Role / Persona -> Individual
```

Industry Performance Packs provide reusable reference semantics without universalizing customer-specific formulas, targets or thresholds.

## Binding boundary

Bindings isolate external implementation details while preserving CEPIO identity, evidence and authority.

Three durable rules become six in the current architecture:

1. CEPIO IDs remain stable across source changes.
2. Source systems remain authoritative for facts/transactions they own.
3. Evidence remains traceable to source.
4. Writeback occurs only after CEPIO authorization/validation.
5. Source acknowledgement is verified/reconciled rather than inferred.
6. Raw source data is not duplicated without a clear runtime need.

Use:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

## Hosted protocol architecture

Current hosted target composition:

```text
/api/v1/*          Application Contract / REST
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

REST, SDK and MCP project shared CEPIO application/runtime contracts. Management remains a separate observation/control-plane projection.

## Microsoft-native industrial agency

```text
Foundry / Copilot
      |
 generic agent execution
      |
      v
CEPIO MCP / Application Contract
      |
      v
Industrial agency
semantics · evidence · Skills · Decisions
policy · authority · Actions · Outcomes
```

Do not create a second general-purpose agent framework inside CEPIO when Microsoft or another host platform already supplies the generic execution layer.

## Persistence boundary

CEPIO runtime and memory/retrieval contracts remain backend-neutral.

Current/reference physical implementations include:

- in-memory stores;
- SQLite;
- Azure AI Search as a retrieval projection.

Future Fabric, PostgreSQL/Azure SQL, graph, distributed cache/search or sovereign backends should implement logical CEPIO contracts without defining CEPIO semantics.

## Headless experience

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

The UI should consume CEPIO capability and evidence contracts rather than become another location for hidden industrial business logic.

## Authority invariants

```text
Knowledge != Authority
Recommendation != Execution
Index != Source of Truth
Cache != Authority
Model Output != Evidence
```

## Architecture success criteria

Architecture is improving when:

- new domains require fewer Core changes;
- more value arrives as reusable Industry IQ;
- competency coverage rises;
- the same Skill/Decision/competency works over different bindings;
- customer/profile knowledge remains isolated unless intentionally generalized;
- context remains bounded as durable knowledge grows;
- indexes/caches remain rebuildable projections;
- autonomy increases only with corresponding evidence, identity, authority and assurance controls.

See [Current State](../current-state.md) for the dated mainline snapshot and the focused [Architecture document](../architecture.md) for the authoritative narrative.
