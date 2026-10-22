# CEPIO Runtime

## Role of the runtime

CEPIO turns industrial operating contracts into governed executable behavior.

The runtime is responsible for more than object storage. Current mainline responsibilities include:

- canonical object/relationship identity and validation;
- temporal history and provenance;
- event storage and deterministic state projection;
- governed query execution;
- Function invocation;
- Decision recording;
- policy/authority evaluation;
- governed Action execution;
- durable workflows and Outcomes;
- Skill admission/preflight/execution;
- capability routing;
- memory/context assembly;
- retrieval and compiled Industry IQ activation;
- external binding/write/verify/reconcile orchestration;
- application, management and MCP protocol projections;
- audit and observability.

The runtime should remain **thin in generic infrastructure** and concentrate on CEPIO-specific industrial contracts.

## Runtime architecture

```text
                  CEPIO runtime contracts
                           |
      +--------------------+--------------------+
      |                    |                    |
 semantics/state      governance/evidence   Industry IQ
      |                    |                    |
      +--------------------+--------------------+
                           |
             Capability / Skill / Policy
                           |
              Memory / Retrieval / Compile
                           |
                 Function / Decision
                           |
                  Workflow / Action
                           |
               Verify / Reconcile / Outcome
                           |
                 protocol projections
            REST · Management · hosted MCP
```

## Repository and persistence contracts

Runtime behavior is designed around logical interfaces rather than a single database product.

Reference persistence includes:

- in-memory implementations for tests/examples;
- SQLite for durable local/reference execution.

Enterprise persistence remains a later OPERATE qualification concern. Physical storage must not leak platform-specific semantics into CEPIO application contracts.

## Object and temporal state

Objects use optimistic versioning, while valid time and transaction time distinguish industrial truth from CEPIO knowledge history.

```text
What was true at T?
      !=
What CEPIO knew at T?
```

Events are immutable and derived state is replayable/deterministic.

## Evidence and provenance

Property/state values can retain source references, observation/ingestion time, mapping/transformation lineage and version information.

Evidence/provenance is a runtime trust boundary, not metadata decoration. Decisions, Skills and Actions should operate on governed evidence visible to the current actor.

## Type and semantic registry

RDF/OWL modules drive canonical type identity, inheritance and relationship constraints.

Runtime responsibilities include:

- IRI-first identity;
- alias ambiguity fail-closed behavior;
- class inheritance;
- relationship domain/range validation;
- module/version metadata.

## Function runtime

Functions perform typed calculations/reasoning operations without themselves granting side-effect authority.

Functions should be deterministic where practical, expose explicit inputs/outputs and remain policy-authorized when sensitive.

## Decision runtime

Decisions are first-class evidence-bearing records and remain distinct from Actions.

A Skill or agent may be authorized to propose/persist a Decision while being denied authority to execute the named Action.

```text
Knowledge != Authority
Recommendation != Execution
```

## Action and external execution runtime

Actions govern side effects.

Current external execution model includes:

```text
Decision / Action intent
 -> authenticated policy/authority
 -> preconditions
 -> idempotent dispatch
 -> binding/source execution
 -> acknowledgement/read-back
 -> verification
 -> reconciliation
 -> immutable Outcome / audit
```

External success is never inferred merely from local CEPIO success.

## Kinetic workflow runtime

Mainline now includes substantial durable workflow capability:

- versioned `WorkflowDefinition` / durable `WorkflowInstance`;
- Function, Decision, Approval and Action steps;
- human pause/resume;
- retry/timeout/cancellation;
- supported compensation;
- asynchronous external execution lifecycle;
- external-verification waiting;
- workflow policy-version pinning;
- immutable terminal `WorkflowOutcome`.

Production distributed worker/queue/recovery qualification remains later OPERATE work.

## Skill runtime

Skill execution is explicitly governed:

```text
Skill dependency declaration
 -> runtime binding
 -> actor-aware preflight
 -> READY / BLOCKED
 -> restricted execution host
 -> evidence + Functions
 -> Decision/recommendation
```

Only READY Skills dispatch. Skills do not receive raw repository/source-client authority by default.

## Capability Registry / Industry IQ runtime

The runtime distinguishes:

- Capability Registry — evidence-backed competence claims;
- Industry IQ Pack Registry — deployable reusable industrial intelligence;
- Skill Registry — executable procedure admission.

Domain Onboarding and Compounding Industrial Intelligence can produce promotion candidates, but global capability promotion remains governed.

## Memory and context

Durable memory and per-task working context are separate.

Current memory classes include Semantic, Procedural, Episodic and Profile records.

`ContextAssembler` applies explicit budgets and fails closed when required context cannot fit.

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

## Retrieval and indexing

Retrieval is capability-routed and bounded:

```text
RetrievalIntent
 -> CapabilityRouter
 -> RetrievalPlan
 -> structured / lexical / vector / graph backends
 -> deterministic fusion
 -> tenant/expiry re-check
 -> required-evidence qualification
 -> ContextAssembler
```

Search/index backends are rebuildable projections, not authority.

PostgreSQL is the preferred next backend behind this logical contract; existing CEPIO SQLite reference storage remains until repository qualification.

## Compiled Industry IQ

Compiled Industry IQ deterministically materializes reusable capability bundles for runtime acceleration.

- Capability Registry remains authoritative;
- cache identity is capability/content based;
- cache loss recompiles without semantic change;
- activation remains bounded;
- PROFILE/customer context is prohibited from the shared compiled cache.

## Performance runtime

Performance Contracts provide runtime/evaluation semantics for:

- objectives;
- key results;
- KPIs;
- guardrails;
- accountability;
- contribution/driver relationships;
- recommend-only workflow response bindings.

Specialization can refine/suppress reference semantics across industry -> organization -> role/persona -> individual layers without copying entire contracts.

## Graph intelligence

CEPIO includes backend-neutral graph analytics. Reference execution uses NetworkX with optional `nx-cugraph` acceleration.

GPU acceleration is an optimization; CEPIO semantic meaning remains authoritative.

## Protocol surfaces

Current hosted target composition:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

REST/SDK/MCP project shared application/runtime contracts. Management is separate and observation-only.

## Runtime maturity

### Implemented / substantial mainline foundation

- in-memory and SQLite persistence;
- typed queries and temporal state;
- provenance and deterministic projection;
- Functions / Decisions / governed Actions;
- durable workflows / verification / Outcomes;
- policy and Skill readiness/execution;
- Capability Registry / Industry IQ controls;
- memory/context/retrieval/compiled IQ;
- Performance Contracts and reference packs;
- Fabric/provider binding contracts;
- authenticated hosted REST + Management + MCP composition;
- observability hooks;
- graph analytics.

### Still open for product/production qualification

- live SAP S/4HANA qualification;
- live PI/historian qualification;
- v0.5 three-source CONNECT lighthouse;
- real governed writeback/read-back/reconciliation release proof;
- live Foundry Reliability G1 qualification evidence;
- production distributed persistence;
- distributed worker/queue/lease recovery;
- enterprise HA/scale;
- complete production source adapters;
- measured production SLOs;
- DR/restore qualification;
- penetration/security qualification;
- second real enterprise portability/adoption.

See [Current State](../current-state.md) and [Roadmap](17-Roadmap.md) for claim boundaries.
