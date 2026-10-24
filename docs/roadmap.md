# CEPIO Execution Roadmap

See [Version naming and delivery status](version-naming.md) for version scopes, [Current State](current-state.md) for the dated mainline snapshot and [v1.0 completion scorecard](v1-completion-scorecard.md) for independently governed maturity scoring.

## North Star

**Product North Star:** The indispensable expert companion for every industrial professional.

**Technology North Star:** CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.

The [Industry IQ Product North Star & Strategic Doctrine](strategy/industry-iq-product-north-star.md) defines proposed moat-building services, professional adoption measurements and the drilling reliability Companion wedge. These are strategic overlays—not new release labels, maturity credits or replacements for the gates below.

The governing product rule is:

> **Every CEPIO release must prove a stronger operating capability, not merely introduce more ontology vocabulary or infrastructure.**

Product progression:

```text
v0.4 FOUNDATION
      -> v0.5 CONNECT
      -> v0.6 EXECUTE
      -> v0.7 EXTEND
      -> v0.8 OPERATE
      -> v0.9 GENERALIZE
      -> v1.0 GUARANTEE
```

Palantir Ontology remains a capability benchmark, not the CEPIO product identity.

Microsoft is the primary reference ecosystem, but CEPIO remains portable at its industrial contract boundary. For agentic workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

---

## Delivery model — gate-based releases, accelerated parallel implementation

CEPIO product releases remain sequential and gate-based, but implementation is intentionally parallel when a reusable capability reduces critical-path risk.

This means later-stage foundations may already exist on `main` without changing the current release designation.

Current product position:

```text
v0.4 FOUNDATION     qualified
v0.5 CONNECT        current / partial
v0.6 EXECUTE        future gate; substantial foundations on main
v0.7 EXTEND         future gate; substantial foundations on main
v0.8 OPERATE        future gate; partial foundations on main
v0.9 GENERALIZE     future gate; synthetic/semantic portability evidence exists
v1.0 GUARANTEE      future gate
```

Execution principle:

> **Pull reusable foundations forward when they reduce risk; never reinterpret component, pack, Lab, scorecard or runtime completion as product-release qualification.**

---

# Completed foundations

## v0.1 — Semantic Scaffold

**Proof:** CEPIO can express a modular common industrial semantic foundation.

Key outcomes:

- Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology architecture;
- objects, relationships, events and Functions;
- initial Actions and policy roles;
- refinery reference scenario and traversal foundation.

## v0.2 — Operational Kernel

**Proof:** CEPIO semantics can drive executable runtime behavior.

Key outcomes:

- repository abstractions and SQLite reference persistence;
- optimistic concurrency;
- immutable Action audit;
- actor/action/target-scoped idempotency;
- RDF-driven type and relationship validation;
- policy engine boundary;
- Functions, Decisions and Actions;
- Python SDK and MCP-ready facade;
- reference adapter contracts.

## v0.3 — Temporal + Provenance Kernel

**Proof:** CEPIO can explain what was true, what was known, where evidence came from and what produced operational state.

Key outcomes:

- IRI-first identity;
- canonical property contracts;
- property-level provenance;
- valid time and transaction time;
- bitemporal object/relationship history;
- deterministic event-state projection;
- compatibility/migration discipline.

---

# v0.4 FOUNDATION — Developer Preview

**Status:** qualified.

**Question answered:**

> Can developers build against a coherent CEPIO industrial operating contract?

Qualified release outcomes include:

- canonical industrial semantics and state/provenance foundation;
- Functions, Decisions and governed Actions;
- versioned `/api/v1`;
- Python + TypeScript client surfaces;
- Entra-aware security boundary;
- Fabric / Fabric IQ and Foundry integration contracts;
- reference App Service / AKS deployment profiles;
- observability and release qualification;
- Generalization and Competency Harness foundations.

The v0.4 release guarantee remains narrower than current repository `main`. See `RELEASE.md`.

---

# v0.5 CONNECT — Live Industrial Integration

**Status:** current / partial.  
**Epic:** #51.

**Question:**

> Can CEPIO operate over authoritative industrial systems while keeping those systems authoritative and close one governed external action loop?

This remains the dominant **product release** critical path even though many later-stage foundations have already landed.

## CONNECT architecture

```text
Authoritative source
    -> Binding Contract
    -> CEPIO identity/state/evidence
    -> Industry IQ / Skill / Decision
    -> policy / authority
    -> governed Action
    -> source execution
    -> read-back / verification
    -> reconciliation
    -> Outcome
```

## Foundations already on main

- source-neutral Binding Contract v0.1;
- provenance and source-reference foundation;
- external identity resolution and fail-closed ambiguity handling;
- external write/verify/reconcile runtime foundation;
- durable workflow wait for verification and immutable Outcomes;
- Fabric/Fabric IQ binding and live-proof transport path;
- OSDU-first subsurface boundary and runtime bindings;
- source-neutral retrieval, with PostgreSQL durable memory/full-text integration as the preferred next implementation;
- live-environment deployment/OIDC foundations.

## Remaining P0 product proof

### SAP S/4HANA / EAM

Target:

- equipment / functional-location context;
- maintenance notifications and work orders;
- maintenance history;
- material/spare context where required;
- governed work-order write;
- source acknowledgement/read-back;
- idempotent reconciliation and failure handling.

### AVEVA PI / historian

Target:

- source-authoritative measurement/event context;
- CEPIO asset/tag identity mapping;
- event-time preservation;
- condition/state evidence;
- provenance from source observation into reasoning.

### Third authoritative domain

At least one additional source domain must participate meaningfully in the release proof, such as:

- OSDU/subsurface;
- P6/project schedule;
- Fabric enterprise context;
- another qualified industrial source under the Binding Contract.

The third source must add real decision context, not exist only to satisfy a numeric count.

## CONNECT lighthouse — K-201 reliability scenario

```text
PI anomaly
 -> CEPIO ConditionObservation/state/provenance
 -> Reliability Industry IQ / Skill
 -> failure/degradation reasoning
 -> consequence + ProductionExposure + uncertainty
 -> Decision
 -> contextual policy / authority
 -> human approval where required
 -> durable workflow
 -> SAP work-order Action
 -> SAP read-back
 -> verification / reconciliation
 -> WorkflowOutcome
 -> audit / assurance evidence
```

## v0.5 release gate

One industrial asset must:

- use context from at least **three authoritative source-system domains**;
- preserve explainable provenance for material values/state;
- support a real industrial Decision through reusable CEPIO capability;
- enforce authenticated identity/policy/authority;
- perform one external writeback;
- be idempotent;
- read the source result back;
- verify/reconcile the result;
- produce an auditable Outcome.

**No CEPIO product-version advancement until this gate is qualified.**

---

# v0.6 EXECUTE — Governed Industrial Outcomes

**Status:** future product gate; substantial runtime/application foundations already on main.  
**Primary application epic:** #59.  
**Kinetic runtime epic:** #67.

**Question:**

> Can CEPIO turn authoritative context and Industry IQ into governed, verified industrial outcomes through a serious reference application?

## Runtime capability substantially pulled forward

Mainline already includes much of the originally expected execution foundation:

- `WorkflowDefinition` / `WorkflowInstance`;
- Function, Decision, Approval and Action steps;
- human pause/resume;
- restart-safe workflow state;
- trigger-key deduplication foundations;
- bounded Function retry/timeout and workflow cancellation;
- governed compensation for supported completed Actions;
- asynchronous external Action lifecycle;
- identity revalidation and dispatch consistency;
- external-verification waiting;
- immutable `WorkflowOutcome`;
- contextual policy / obligations / deny-dominant composition;
- exact workflow policy-version pinning;
- Skill runtime admission, READY preflight and host dispatch;
- Application Contract and protocol convergence.

Remaining production/application gaps include event/state/time trigger integration at the required product level, public workflow-control surfaces where needed, distributed worker scheduling/recovery and complete live integration proof from CONNECT.

## EXECUTE lighthouse — Asset Reliability / Maintenance Command Center

Primary personas:

- Reliability Engineer;
- Maintenance Planner;
- Operations Engineer;
- Maintenance Manager;
- Plant Manager.

Core loop:

```text
Detect degradation
 -> explain asset/context/evidence
 -> assess consequence and uncertainty
 -> inspect work/materials/production constraints
 -> generate intervention options
 -> compare risk / cost / availability impact
 -> recommend
 -> authorize
 -> act
 -> verify Outcome
 -> learn / evaluate
```

The application should contain minimal hidden industrial business logic. Reusable logic belongs in CEPIO Industry IQ, Skills, Functions, Performance Contracts, Decision definitions, policies and workflows.

## Microsoft-native agentic execution

The Reliability Agent Lighthouse defines the Microsoft-native boundary:

> **Microsoft owns agent execution. CEPIO owns industrial agency.**

The program spans Foundry-hosted agent execution, CEPIO MCP, Reliability Industry IQ, event triggering, approval, governed SAP action, evaluation and provider portability.

The G1 qualification path exists on main; a repository merge does not equal a successful live G1 run.

## v0.6 release gate

One reference application demonstrates the complete governed loop:

```text
Observe -> Understand -> Reason -> Decide -> Authorize -> Act -> Verify -> Learn
```

over qualified CONNECT integrations, using first-class CEPIO contracts rather than application-specific hidden business logic.

Follow-on reference applications can include refinery margin/constraint optimization and turnaround planning.

---

# v0.7 EXTEND — Industrial Developer Platform

**Status:** future product gate; significant extension/control-plane foundations already on main.  
**Epic:** #60.

**Question:**

> Can independent teams add Industry IQ, customer specialization and platform bindings safely without modifying CEPIO Core?

## Foundations already on main

- versioned REST Application Contract;
- Python and TypeScript client surfaces;
- MCP protocol projection;
- customer/profile architecture;
- Binding Contract;
- Skill Registry and executable Skill contracts;
- Industry IQ Pack Registry;
- trusted catalogue/provenance and supply-chain policy;
- Capability Registry;
- Domain Onboarding workflow;
- Compounding Industrial Intelligence;
- compatibility/migration gates;
- Management Contract/read projection;
- strong technical documentation and ADR discipline.

## Required EXTEND productization

- mature SDK coverage of supported operations;
- supported CLI;
- profile/binding/Industry-IQ/application scaffolding;
- generated/current API and SDK documentation;
- pack authoring and validation workflows;
- dependency/version tooling;
- clear public vs protected Industry IQ packaging guidance;
- clean-room developer qualification;
- stable management/diagnostic experience for Studio and platform builders.

Target flows:

```text
cepio new-profile <name>
cepio new-binding <provider>
cepio new-skill <name>
cepio new-pack <domain>
cepio validate
cepio test
cepio query
cepio migrate
cepio deploy
```

## v0.7 release gate

A clean-room developer can build and qualify:

- a customer profile/specialization;
- a platform binding;
- a bounded Industry IQ capability/pack;
- a small CEPIO-powered application or agent experience;

through supported tooling without editing canonical Core modules.

---

# v0.8 OPERATE — Enterprise Runtime

**Status:** future product gate; some security/deployment/reliability foundations are already on main.  
**Epic:** #61.

**Question:**

> Can an industrial enterprise depend on CEPIO for sustained critical workloads?

## Foundations already pulled forward

- Governance v2;
- compatibility/release evidence controls;
- CodeQL/security ratchets;
- SBOM/provenance generation;
- managed/workload identity patterns;
- App Service/AKS reference profiles;
- hosted REST + Management + MCP composition;
- runtime observability;
- workflow restart/idempotency correctness;
- external verification/reconciliation;
- Azure AI Search prototype (now retired under ADR-0039; future PostgreSQL adapter is the successor milestone).

## Remaining enterprise-runtime qualification

- horizontal scale and stateless service qualification;
- production persistence topology;
- queues/event processing and distributed workers;
- leases/distributed workflow recovery;
- retries/DLQ/backpressure across real dependencies;
- adapter circuit breakers;
- private networking and workload identity hardening;
- secrets/key management as required by deployment;
- backup/restore;
- disaster recovery exercises;
- penetration/security qualification;
- enterprise observability dashboards;
- measured SLO/error-budget program;
- capacity/performance envelopes.

## v0.8 release gate

CEPIO survives node/service restart, duplicate messages, stale writes and source/dependency outages without semantic, authority or workflow corruption, with measured SLOs, tested recovery and operational runbooks.

---

# v0.9 GENERALIZE — Multi-Enterprise Portability

**Status:** future product gate.  
**Epic:** #62.

**Question:**

> Is CEPIO genuinely portable Industrial Operating Intelligence rather than one sophisticated deployment?

## Generalization evidence already achieved

The repository already contains strong synthetic/deterministic evidence:

- refinery/process-manufacturing capability pressure and semantic normalization;
- drilling-contractor semantic and runtime qualification;
- cross-operating-model drilling qualification without customer-specific Core overrides;
- OSDU-first subsurface boundary;
- Capability Registry / Compounding Intelligence promotion discipline;
- provider-neutral Binding Contract and Fabric parity proofs;
- customer/profile isolation;
- reusable Industry Performance Reference Packs.

This is meaningful evidence but does **not** satisfy the real adoption gate.

## Multi-enterprise proof

Enterprise #2 should be implemented primarily through:

```text
existing CEPIO Core
+
reusable Industry IQ
+
Customer Profile / specialization
+
Bindings
+
configuration
```

rather than a Core/runtime fork.

Measure:

- canonical class/relationship reuse;
- capability and pack reuse;
- Skill/Decision/workflow reuse;
- Performance Contract/reference-pack reuse;
- profile-specific additions;
- binding reuse;
- Core modifications required;
- application reuse;
- migration impact on Enterprise #1.

## Platform portability proof

A strategic test is the same capability contract over different context providers:

```text
Fabric --------+
               |
Cognite -------+--> same CEPIO competency / Skill / Decision
               |
OSDU ----------+
```

The underlying evidence locations may differ. The industrial operating contract should remain stable.

## v0.9 release gate

A second materially different real enterprise deployment is implemented mainly through profiles, bindings, Industry IQ and configuration while the first enterprise remains stable and Core change remains minimal.

---

# v1.0 GUARANTEE — Production Guarantees

**Status:** future product gate.  
**Epic:** #63.

**Question:**

> Can enterprises adopt CEPIO with stable contracts and explicit production guarantees?

v1.0 should be a guarantee milestone, not another feature explosion.

## Required guarantees

### Semantic compatibility

- versioned module/contracts;
- explicit migrations for breaking semantic changes;
- stable profile/pack dependency rules.

### Application / API / protocol compatibility

- stable supported Application Contract and `/api/v1` surface;
- SDK compatibility tests;
- documented deprecation policy;
- explicit Management/MCP support boundaries.

### Industry IQ compatibility

Versioned contracts for:

- packs/capabilities;
- Skills;
- competency/evidence requirements;
- Performance reference semantics;
- Decisions and Actions;
- evaluation/assurance evidence.

### Security and authority

- authenticated identity;
- actor-scoped authorization;
- immutable governed Action/workflow history;
- security/penetration qualification;
- no model or client self-asserted authority.

### Runtime reliability

- repeatable deployment;
- HA/scale qualification;
- backup/restore and DR;
- telemetry/runbooks;
- measured SLOs.

### Integration

- production-quality reference source bindings;
- governed verified/reconciled writeback.

### Portability/adoption

- at least two materially different real enterprise deployments;
- Enterprise #2 does not destabilize Enterprise #1;
- clean-room deployment/adoption from published documentation.

## v1.0 release gate

Prior product gates are complete and compatibility, security, SLO/DR, portability/adoption and Industry IQ assurance guarantees are explicitly qualified.

---

# Continuous workstreams

## Industry IQ

Differentiated CEPIO value should increasingly live in reusable industrial competence:

- capabilities;
- packs;
- Skills;
- competency questions;
- evidence requirements;
- failure/risk/decision patterns;
- Performance Contracts;
- constraints;
- KPI/economic logic;
- workflows;
- evaluation benchmarks.

## Competency & assurance

```text
Persona
 -> Responsibility
 -> Decision
 -> Competency question
 -> Required capability/evidence
 -> Skill / Function / Decision / Action
 -> PASS / PARTIAL / FAIL / NOT_RUN
```

Maturity spans semantic, runtime, procedural/Skill, agent and operational competency.

## Generalization and compounding

New domains should require progressively fewer Core changes.

```text
More domains + higher competency coverage + more capability reuse + less Core churn
= stronger reusable Industry IQ
```

## Memory / retrieval / compiled IQ

Durable Industry IQ may grow, but model context, retrieval fan-out and compiled runtime activation must remain explicitly bounded. Memory, indexes and caches must preserve tenant/IP boundaries and never become ungoverned authority.

## Policy and authority

```text
Knowledge != Authority
Recommendation != Execution
Model output != Evidence
Cache != Authority
```

## Headless experiences

CEPIO remains headless at its core and persona-adaptive at its surface.

> **Same industrial reality. Different experience for every decision-maker.**

---

# Roadmap vs canonical v1 scorecard

The roadmap and v1 scorecard answer different questions.

- **Roadmap:** which proof must be completed before a product release advances?
- **Scorecard:** how much evidence-backed v1 maturity exists overall?

The canonical scorecard currently remains **69/100**, pinned to its governed evidence snapshot. Later merges may create scorecard drift but do not change the canonical number until a governed score update qualifies the evidence.

Scorecard dimensions are intentionally not one-to-one aliases for release labels. See [Version Naming](version-naming.md) for the mapping discipline.

---

# Roadmap success measure

The goal is not to build the largest ontology or the heaviest industrial platform.

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

The product goal is to build the strongest portable **Industry IQ for governed industrial work** while keeping infrastructure thin, replaceable and subordinate to the industrial operating contract.
