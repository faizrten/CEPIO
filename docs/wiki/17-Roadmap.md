# Roadmap to CEPIO v1.0

See [version naming](../version-naming.md) for product/component/Lab/API scopes and [execution roadmap](../roadmap.md) for the authoritative release gates.

## Roadmap North Star

> **Thin infrastructure. Thick industrial intelligence.**

The roadmap is not a sequence of ontology-size milestones. Each release must prove stronger governed industrial operating capability while preserving a thin, portable core.

```text
v0.4 Foundation
   -> v0.5 Connect
   -> v0.6 Execute
   -> v0.7 Extend
   -> v0.8 Operate
   -> v0.9 Generalize
   -> v1.0 Guarantee
```

## Completed — v0.1 Semantic Scaffold

**Proof:** modular common industrial semantics can be represented consistently.

## Completed — v0.2 Operational Kernel

**Proof:** CEPIO semantics can drive executable persistence, policy, Functions, Decisions, Actions and audit.

## Completed — v0.3 Temporal + Provenance Kernel

**Proof:** CEPIO can explain what was true, what was known, where evidence came from and which events produced state.

## Completed — v0.4 Developer Preview

**Proof:** developers can build against a coherent CEPIO industrial operating contract.

Developer Preview qualification includes canonical semantics, temporal/provenance contracts, governed Functions/Decisions/Actions, `/api/v1`, Microsoft platform bindings, reference deployment and observability.

## Current — v0.5 Connect
### Live Industrial Integration

**Question:** Can CEPIO operate over real industrial systems without becoming another system of record?

Focus:

- SAP and historian/PI integration;
- OSDU/Fabric and additional platform bindings;
- source identity reconciliation;
- event ingestion;
- evidence lineage;
- governed writeback;
- execution verification and reconciliation.

Gate:

> One industrial asset uses context from at least three source domains and completes an authorized, idempotent, verified and reconciled external writeback.

## v0.6 Execute
### Kinetic Runtime + Reference Industrial Applications

**Question:** Can CEPIO turn context and Industry IQ into governed, verified outcomes?

Focus:

- durable workflow;
- triggers;
- approvals;
- async Actions;
- retries/cancellation/compensation;
- policy at each sensitive step;
- outcome verification;
- Asset Reliability / Maintenance Command Center.

Gate:

> One reference application demonstrates the complete Observe/Understand/Reason/Decide/Authorize/Act/Verify loop over qualified live integrations.

## v0.7 Extend
### Industrial Developer Platform

**Question:** Can independent teams add Industry IQ without modifying CEPIO Core?

Focus:

- mature SDKs and CLI;
- Skill framework and registry;
- profiles and bindings;
- scaffolding;
- validation and migration tooling;
- clean-room developer flows.

Gate:

> A clean-room developer can build a profile, binding and bounded Industry IQ extension through supported tooling without editing canonical Core.

## v0.8 Operate
### Enterprise Runtime

**Question:** Can an enterprise depend on CEPIO for sustained critical workloads?

Focus:

- HA and scale;
- production persistence;
- queues/workers/backpressure;
- security hardening;
- DR;
- enterprise observability and SLOs.

Gate:

> CEPIO tolerates restart, duplicates, stale writes and dependency outages without semantic/workflow corruption and with tested operational runbooks.

## v0.9 Generalize
### Portability + Second-Enterprise Adoption

**Question:** Is CEPIO portable Industry IQ rather than a deployment-specific solution?

Focus:

- second real enterprise profile;
- cross-domain competency reuse;
- Industry IQ Pack reuse;
- Skill/Decision reuse;
- minimal Core change;
- platform portability proof where feasible.

Gate:

> Enterprise #2 is implemented mainly through profiles, bindings and reusable Industry IQ while enterprise #1 remains stable.

## v1.0 Guarantee
### Production Guarantees

**Question:** Can customers adopt CEPIO with stable contracts and explicit operational guarantees?

Expected guarantees:

- semantic/API compatibility;
- migration/deprecation policy;
- security and authority boundary;
- HA/SLO/DR qualification;
- production-grade source bindings;
- governed verified writeback;
- versioned competency/assurance contracts;
- repeatable multi-enterprise adoption.

## Continuous workstreams

### Industry IQ

Thick reusable intelligence should accumulate in Skills, competency questions, evidence requirements, failure/risk/decision patterns, constraints, KPI/economic logic, workflows and evaluation benchmarks.

### Competency & Assurance

Competency is a product-quality metric spanning semantic, runtime, Skill, agent and operational layers.

### Generalization

The desired signal is more domains and personas with fewer changes to Core and fewer customer-specific exceptions.

### Policy & Authority

`Knowledge != Authority` and `Recommendation != Execution` remain invariant as autonomy increases.

### Headless experiences

CEPIO stays headless at its core and persona-adaptive at its surface.

## What it takes to reach v1.0

The dominant work is no longer ontology vocabulary creation. The critical path is:

```text
live context
 -> governed execution
 -> reusable Industry IQ
 -> developer extensibility
 -> enterprise reliability
 -> cross-enterprise portability
 -> explicit production guarantees
```

The goal is not the largest ontology. It is the strongest portable Industry IQ for governed industrial work.
