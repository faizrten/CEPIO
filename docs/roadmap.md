# CEPIO Execution Roadmap

See [Version naming and delivery status](version-naming.md) for product, component, Lab and API version scopes.

## North Star

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

The governing product principle is:

> **Keep infrastructure thin and replaceable; concentrate CEPIO IP in reusable industrial intelligence.**

Palantir Ontology remains a useful capability benchmark, not CEPIO's product identity. Microsoft remains the primary reference ecosystem, but the CEPIO operating contract must stay portable across alternative industrial data platforms and source environments.

The roadmap therefore progresses through stronger operating proof rather than ontology growth:

```text
v0.4 Foundation
   -> v0.5 Connect
   -> v0.6 Execute
   -> v0.7 Extend
   -> v0.8 Operate
   -> v0.9 Generalize
   -> v1.0 Guarantee
```

Every release must prove a stronger industrial operating capability.

---

## Product architecture that guides the roadmap

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES
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
          Headless persona-adaptive experiences
```

Roadmap choices should favor reusable industrial competence over proprietary infrastructure.

---

# Completed foundations

## v0.1 — Semantic Scaffold

**Proof:** CEPIO can express a modular common industrial semantic foundation.

Key outcomes:

- modular Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology;
- object, relationship, event and Function concepts;
- initial actions, roles and refinery reference scenario.

## v0.2 — Operational Kernel

**Proof:** CEPIO semantics can drive executable runtime behavior.

Key outcomes:

- repositories and SQLite reference persistence;
- concurrency, idempotency and immutable action audit;
- RDF-driven type/relationship validation;
- policy interface;
- Functions, Decisions and Actions;
- Python SDK and MCP-ready facade;
- reference adapter contracts.

## v0.3 — Temporal + Provenance Kernel

**Proof:** CEPIO can explain what was true, what was known, where evidence came from and which events produced state.

Key outcomes:

- canonical industrial modules;
- IRI-first identity;
- property provenance;
- valid-time and transaction-time history;
- deterministic event-state projection;
- compatibility/migration discipline.

## v0.4 — Developer Preview

**Proof:** developers can build against a coherent CEPIO operating contract.

Release designation: **CEPIO v0.4 — Developer Preview**.

Key outcomes include:

- canonical semantics and state/provenance foundation;
- Functions, Decisions and governed Actions;
- versioned `/api/v1`;
- Python and TypeScript client surfaces;
- Entra-aware security boundary;
- Fabric / Fabric IQ and Foundry integration patterns;
- App Service / AKS reference deployment;
- observability and release qualification;
- Generalization and Competency Harness foundations.

**Status:** qualified.

---

# Current — v0.5 Connect
## Live Industrial Integration

**Question answered:**

> Can CEPIO operate over real industrial systems while keeping those systems authoritative and avoiding unnecessary duplication?

This is the current product critical path.

Primary outcomes:

- production-grade source-neutral adapter lifecycle;
- SAP S/4HANA / EAM integration;
- AVEVA PI / historian integration;
- OSDU / subsurface integration;
- Fabric-native operational binding;
- external identity reconciliation;
- event ingestion and reconciliation;
- evidence lineage to authoritative sources;
- governed writeback;
- execution verification and source read-back;
- operational telemetry around adapters and writeback.

Architectural rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable operating intelligence.**

### v0.5 lighthouse proof

The K-201 reliability scenario remains the convergence gate:

```text
PI anomaly
 -> CEPIO observation/state/evidence
 -> reliability Skill / reasoning
 -> uncertainty + consequence
 -> Decision
 -> policy / human approval
 -> governed workflow
 -> SAP work order
 -> read-back / verification
 -> Outcome
 -> audit / learning evidence
```

### v0.5 release gate

One industrial asset must use context from at least three source-system domains, retain explainable provenance, and complete one authorized, idempotent, verified and reconciled external writeback.

The release should prove **connection to industrial truth**, not a larger ontology.

---

# v0.6 Execute
## Kinetic Runtime + Reference Industrial Applications

**Question answered:**

> Can CEPIO turn industrial context and Industry IQ into governed, verified operational outcomes?

Primary outcomes:

- durable WorkflowDefinition / WorkflowInstance;
- event/state/time triggers;
- Functions, Decisions, approvals and Actions;
- human pause/resume;
- retries, timeouts and cancellation;
- asynchronous execution;
- compensation;
- external verification;
- deterministic workflow history;
- policy enforcement at every sensitive boundary;
- `WorkflowOutcome` and learning evidence.

Substantial kinetic foundations are already on `main`; v0.6 should therefore emphasize **application proof**, not infrastructure for its own sake.

### Lighthouse application

**Asset Reliability / Maintenance Command Center**

Primary personas:

- Reliability Engineer;
- Maintenance Planner;
- Operations Engineer;
- Maintenance Manager;
- Plant Manager.

Core loop:

```text
Detect degradation
 -> explain context and evidence
 -> assess consequence / uncertainty
 -> inspect work, materials and production context
 -> generate intervention options
 -> compare risk / cost / availability impact
 -> recommend
 -> authorize
 -> act
 -> verify outcome
 -> learn
```

Follow-on reference applications may include refinery constraint/margin optimization and turnaround planning.

### v0.6 release gate

One reference application demonstrates the complete governed loop over qualified live integrations using first-class CEPIO contracts rather than application-specific hidden business logic.

---

# v0.7 Extend
## Industrial Developer Platform

**Question answered:**

> Can independent teams extend CEPIO by adding Industry IQ without modifying CEPIO Core?

Primary outcomes:

- mature Python and TypeScript SDKs;
- CLI and developer tooling;
- Skill development framework and registry;
- capability discovery and dependency declarations;
- runtime preflight;
- profile / adapter / app scaffolding;
- ontology/profile validation tooling;
- package/version/migration tooling;
- generated API/SDK documentation;
- reusable examples and clean-room developer qualification.

The key architectural proof is that new value arrives through **Industry IQ Packs, profiles and bindings**, not through uncontrolled Core expansion.

### v0.7 release gate

A clean-room developer can create a customer profile, platform binding and bounded Industry IQ extension through supported tooling without editing canonical Core modules.

---

# v0.8 Operate
## Enterprise Runtime

**Question answered:**

> Can an industrial enterprise depend on CEPIO for sustained critical workloads?

Primary outcomes:

- horizontal scale and HA;
- production persistence;
- queue/event processing and distributed workers;
- retries, dead-letter handling and backpressure;
- adapter circuit breakers;
- workload identity and private networking;
- backup/restore and disaster recovery;
- security hardening and penetration qualification;
- enterprise observability;
- SLO/error-budget program;
- lifecycle and supportability controls.

The product should resist becoming infrastructure-heavy: enterprise runtime work exists to make the operating contract dependable, not to create a competing industrial cloud platform.

### v0.8 release gate

CEPIO survives restart, duplicate messages, stale writes and dependency outages without semantic or workflow corruption, with measured SLOs and tested operational runbooks.

---

# v0.9 Generalize
## Portability + Second-Enterprise Adoption

**Question answered:**

> Is CEPIO genuinely portable industrial operating intelligence rather than a deployment-specific solution?

Generalization evidence already includes substantial refinery/process and drilling competency work, customer-model qualification and explicit source-neutral boundaries such as OSDU-first subsurface design.

v0.9 requires real deployment proof across materially different enterprises and/or platform environments.

Primary measures:

- canonical class and relationship reuse;
- Industry IQ Pack reuse;
- Skill and Decision reuse;
- customer-profile additions;
- Core modifications required;
- binding/adapter reuse;
- application/workflow reuse;
- migration impact on enterprise #1;
- platform portability where feasible.

A strategic portability test is:

```text
Fabric context ----+
                   |
Cognite context ---+--> same competency / Skill / Decision contract
                   |
OSDU context ------+
```

### v0.9 release gate

Enterprise #2 is implemented primarily through profiles, bindings and Industry IQ configuration while enterprise #1 remains stable and Core change remains minimal.

---

# v1.0 Guarantee
## Production Guarantees

**Question answered:**

> Can customers adopt CEPIO with stable contracts and explicit production guarantees?

v1.0 is not another large feature wave. It is the transition from evolving platform to supported production contract.

Required guarantees include:

### Semantic compatibility

- versioned ontology/module contracts;
- explicit migrations for breaking changes;
- stable profile and Industry IQ Pack dependency/version rules.

### API and developer compatibility

- stable supported API surface;
- SDK compatibility tests;
- documented deprecation policy.

### Security and authority

- authenticated identity;
- actor-scoped authorization;
- immutable governed action/workflow history;
- security review and penetration testing.

### Runtime reliability

- repeatable deployment;
- HA/scale qualification;
- backup/restore and DR;
- telemetry/runbooks;
- measured SLOs.

### Integration

- production-quality reference source bindings;
- governed, verified and reconciled writeback.

### Industry IQ assurance

- versioned competency contracts;
- deterministic regression evidence;
- explicit coverage/gap reporting;
- reproducible Skill/Decision/Action assurance.

### Adoption

- at least two materially different enterprise deployments;
- enterprise #2 does not destabilize enterprise #1;
- published documentation supports teams beyond the original authors.

### v1.0 release gate

v0.4-v0.9 product gates are complete and compatibility, security, SLO/DR, portability and Industry IQ assurance guarantees are explicitly qualified.

---

# Continuous workstreams

The following are not isolated release milestones; they mature continuously.

## Industry IQ Packs

The differentiated product should increasingly live in reusable packs containing:

- domain semantic compositions;
- Skills;
- competency questions;
- evidence requirements;
- failure/risk patterns;
- decision/intervention patterns;
- constraints;
- KPI/economic logic;
- workflows;
- evaluation benchmarks.

## Competency & Assurance

Competency is a product quality metric:

```text
Persona
 -> Job / responsibility
 -> Decision
 -> Competency question
 -> Required capabilities
 -> Evidence / Skill / Function / Decision / Action
 -> PASS / PARTIAL / FAIL / NOT_RUN
```

Maturity progresses through semantic, runtime, procedural/Skill, agent and operational competency.

## Generalization

New domains should require progressively fewer Core changes.

```text
More domains + higher competency coverage + less Core churn
= stronger reusable Industry IQ
```

## Policy & Authority

Increasing autonomy must preserve:

```text
Knowledge != Authority
Recommendation != Execution
```

## Headless experiences

CEPIO remains headless at its core and persona-adaptive at its surface.

> **Same industrial reality. Different experience for every decision-maker.**

---

# Roadmap success measure

The roadmap is successful when CEPIO supports progressively more real industrial work without becoming a heavier infrastructure platform.

Conceptually:

```text
CEPIO maturity
=
Competency Coverage
x Runtime Capability
x Generalization
x Evidence Quality
x Governed Actionability
x Operational Reliability
```

The goal is not to build the largest industrial ontology.

The goal is to build the strongest portable **Industry IQ** for governed industrial work.
