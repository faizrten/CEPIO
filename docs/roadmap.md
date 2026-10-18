# CEPIO Execution Roadmap

See [Version naming and delivery status](version-naming.md) for product, component, Lab and API version scopes.

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and native to the Microsoft ecosystem.**

CEPIO owns the canonical industrial semantic and operational contract. Microsoft services provide the data, semantic materialization, AI, application hosting and infrastructure planes on which that contract is realized.

`CEPIO semantic contract -> Microsoft platform bindings -> customer deployment`

The governing product rule from v0.4 onward is:

> **Every CEPIO release must prove a stronger operating capability, not merely introduce more ontology vocabulary.**

## Current delivery posture — accelerated parallel execution

CEPIO product releases remain gate-based and sequential, but implementation is no longer artificially serial.

Several foundations originally expected primarily in later product releases are already on `main` because they reduce risk for the current v0.5 integration milestone:

- durable workflow orchestration, verification and `WorkflowOutcome`;
- contextual policy, exact policy-version pinning and trusted evaluation lineage;
- Skill registry preflight and READY-only host dispatch;
- evidence, uncertainty, confidence and information-gain semantics in Core;
- OSDU-first subsurface federation and source-neutral domain runtime bindings;
- Kinetic `Opportunity`, `Option` and `OptionRecommendation` semantics;
- deterministic drilling runtime assurance and cross-customer portability qualification;
- CEPIO Governance v2, CodeQL/security ratchets, compatibility controls and release-evidence generation.

This accelerates later roadmap stages but does **not** change the release rule: a CEPIO product version advances only when its own release gate is qualified.

Current product position:

`v0.4 qualified -> v0.5 current/live integration -> v0.6 compressed application proof -> v0.7 developer platform -> v0.8 enterprise runtime -> v0.9 real second-enterprise adoption -> v1.0 production guarantees`

Execution principle:

> **Pull reusable foundations forward when they reduce critical-path risk; never reinterpret component, runtime or Lab completion as product-release qualification.**

---

## Completed — v0.1 Semantic Scaffold

**Outcome:** establish the common ontology foundation.

- modular CEPIO Core / Industrial / Energy / Lifecycle / Enterprise / Kinetic ontology;
- object, relationship, event and function concepts;
- in-memory graph traversal;
- initial actions and policy roles;
- FastAPI scaffold and refinery sample.

---

## Completed — v0.2 Operational Kernel

**Outcome:** move from ontology vocabulary to an executable operational runtime.

- persistent repository abstractions and SQLite backend;
- optimistic object concurrency;
- immutable action audit;
- secure idempotency;
- RDF-driven type registry and relationship validation;
- policy-engine interface with object/property/action controls;
- action preconditions and approval metadata;
- Decision records;
- typed function inputs;
- inverse/multi-hop traversal;
- Python SDK and MCP-ready facade;
- dry-run SAP, AVEVA PI, OSDU, P6 and Fabric contracts;
- SHACL validation path;
- executable KPI -> asset -> event -> decision -> work-order -> spare demo.

---

## Completed — v0.3 Temporal + Provenance Kernel

**Outcome:** CEPIO can explain what an industrial object means, where its values came from, what was true at time T, what CEPIO knew at time T, and which immutable events produced derived operational state.

### Canonical industrial model
- common modules for Asset, Work Management, Reliability, HSE, Supply, Performance, Workforce, Commercial and Agentic Operations;
- domain modules for Process Industry, EPCIC and Drilling;
- SEO refinery/petrochemical + EPC ontology normalized into CEPIO;
- AD asset-heavy/drilling ontology normalized into CEPIO;
- source-property occurrences classified into canonical properties, relationship keys, observations, provenance or profile-specific semantics.

### Semantic contract
- IRI-first identity for classes, relationships and datatype properties;
- fail-closed alias ambiguity;
- semantic module namespaces, versions and dependencies;
- canonical property registry with datatype and authority metadata.

### Provenance + time
- SourceReference, TransformationRun and PropertyProvenance contracts;
- property-level lineage explanations;
- immutable object version history;
- transaction-time reconstruction;
- valid-time queries and bitemporal object views;
- immutable relationship revision history;
- bitemporal graph queries.

### Event -> state
- deterministic ordering `(occurred_at, event_id)`;
- replayable projection contract;
- compressor operating-state reference projector;
- independent projection checkpoints;
- delete/rebuild derived state from immutable source events.

**Gate achieved:** CEPIO can answer `what is true -> where did it come from -> what was true/known at time T -> what events caused the state -> what governed action can follow?`

---

# Completed — CEPIO v0.4 Microsoft Platform Extension + Developer Preview

**Epic:** #22  
**Release gate:** #50

**Outcome:** make CEPIO natively consumable across the Microsoft Data + AI platform while preserving a portable, source-system-neutral canonical contract, then qualify the result as a Developer Preview.

## Completed platform foundation

- #5 Typed query and temporal filter contract — completed via PR #28.
- #7 Microsoft platform extension architecture — completed via PR #17.
- #18 Fabric and Fabric IQ semantic binding — completed via PR #29.
- #19 Foundry agent and CEPIO MCP binding — completed via PR #30.
- #4 Ontology migration manifests and compatibility gates — completed via PR #31.

## Completed product hardening

- #34 / #35 Entra REST identity, anti-spoofing and actor-scoped read authorization — completed via PR #38.
- #36 production runtime configuration, package resources and version source — completed via PR #45.
- #37 first-class customer profile architecture — completed via PR #46.
- #41 versioned `/api/v1` and OpenAPI contract — completed via PR #48.
- #42 standard API errors, ETag/If-Match and idempotency semantics — completed via PR #49.
- #43 repository query pushdown and cursor pagination — completed via PR #64.
- #21 App Service and AKS reference deployment profiles — completed via PR #65.

## Completed qualification

- #6 runtime observability / OpenTelemetry — completed via PR #66.
- #50 Developer Preview release gate — qualified via PR #69.

Release designation: **CEPIO v0.4 — Developer Preview**.

Deferred/non-blocking from v0.4:
- #20 Purview governance and lineage bridge;
- #25 GPU AKS / cuGraph validation and benchmarking.

---

# Current — CEPIO v0.5 Live Industrial Integration

**Epic:** #51

**Outcome:** prove that CEPIO can operate over real industrial systems and close the governed writeback loop.

v0.5 is now the dominant product critical path. Most semantic, policy and kinetic foundations required to consume live integrations already exist; the remaining risk is industrial connectivity and end-to-end qualification rather than core architecture.

## Current state

### Provenance — mostly implemented, final integration/security qualification open

#2 has the property-level kernel on `main`: source references, mapping/transformation versions, observed vs ingestion time, SQLite persistence and property explanation. Remaining work is adapter consumption, authorization qualification and broader lineage/derived-state coverage.

### Adapter SDK — partial

#52 already has the governed `write() -> verify() -> reconcile()` subset and fake-adapter qualification. Complete the source-neutral lifecycle:

`discover() -> read() -> subscribe() -> map() -> reconcile() -> write() -> verify()`

Remaining SDK work includes sync/event-driven lifecycle consistency, stable adapter error semantics, telemetry and full connector contract qualification.

### External identity + writeback — common runtime foundation implemented

#57 has common identity resolution, fail-closed ambiguity handling, idempotent external execution, verification, reconciliation state, workflow lineage and immutable Outcomes through #107/#114/#121/#149.

The remaining gate is **real source qualification**, especially SAP read/write/read-back, failure handling and operational observability.

### SAP + PI — current product bottleneck

- #53 SAP S/4HANA maintenance/enterprise adapter — current P0.
- #54 AVEVA PI operational-state adapter — current P0.

These should be built around the K-201 proof rather than as disconnected generic connector projects.

### Third-domain context

- #55 OSDU/subsurface: OSDU-first boundary, domain runtime bindings and uncertainty/Opportunity semantics are now on `main` via #158/#159; live connector qualification remains open.
- #56 Primavera P6 remains a valid alternative third-domain path.

### v0.5 lighthouse proof — K-201 compressor

#58 is the convergence gate for the product:

`PI anomaly -> CEPIO observation/state/provenance -> reliability reasoning/Skill -> evidence + uncertainty -> Decision -> contextual policy -> human approval -> Kinetic workflow -> SAP work order -> SAP read-back -> verification -> WorkflowOutcome -> audit`

## v0.5 release gate

One industrial asset must be represented using context from at least three source-system domains, material values/state must be explainable through provenance, and one external writeback must be authorized, idempotent, verified and reconciled.

No product-version advancement until this gate is qualified.

---

# v0.6 — Kinetic Runtime + Reference Industrial Applications

**Application epic:** #59  
**Kinetic runtime:** #67

**Outcome:** prove that CEPIO can power a serious industrial application over live integrations using governed orchestration rather than application-specific business logic.

## Delivery status — substantially pulled forward

A large part of the v0.6 runtime foundation is already on `main`:

- durable `WorkflowDefinition` / `WorkflowInstance`;
- Function, Decision, Approval and Action steps;
- human pause/resume;
- restart-safe workflow state;
- replay-safe trigger-key deduplication;
- bounded function retries/timeouts and cancellation;
- governed compensation for supported completed Actions;
- async external Action lifecycle;
- identity revalidation and concurrent dispatch consistency;
- external-verification waiting;
- immutable `WorkflowOutcome`;
- contextual policy, obligations and deny-dominant composition;
- exact workflow policy-version pinning and trusted evaluation lineage;
- Skill runtime admission/preflight and READY-only host dispatch.

Primary kinetic model:

`Event/State -> Trigger -> Workflow -> Function -> Decision -> Approval -> Action -> Verify -> Outcome`

Remaining runtime work before #67 can close:

- event/state/time trigger subscriptions;
- authenticated public workflow-control surfaces;
- REST/SDK/MCP workflow administration;
- workflow-specific OpenTelemetry qualification;
- production worker scheduling, queue/lease semantics and distributed recovery;
- complete live adapter/writeback proof from v0.5.

## Lighthouse application — Asset Reliability / Maintenance Command Center

Primary personas:
- Reliability Engineer;
- Maintenance Planner;
- Operations Engineer;
- Maintenance Manager;
- Plant Manager.

Core workflow:
1. detect degradation;
2. explain affected asset/context;
3. assess operational consequence and risk;
4. inspect work, maintenance and materials context;
5. generate intervention options;
6. compare risk/cost/availability impact;
7. recommend action;
8. authorize;
9. issue governed action/work order;
10. observe and verify outcome.

Prefer bounded agents such as Reliability, Maintenance Planning, Operations Risk, Materials and Cost agents, all operating through CEPIO policy, workflow, Skill and Action contracts.

Because the runtime foundation is already substantially implemented, **v0.6 is now expected to be primarily a live application/integration qualification milestone rather than a large new runtime build.**

**v0.6 gate:** one reference application demonstrates the complete `Observe -> Understand -> Reason -> Decide -> Authorize -> Act -> Observe outcome` loop over qualified v0.5 integrations using first-class CEPIO runtime contracts.

Follow-on applications:
- Refinery Margin / Constraint Optimization;
- Turnaround Planning.

---

# v0.7 — Developer Platform

**Epic:** #60

**Outcome:** independent engineering teams can extend CEPIO without modifying CEPIO-Core.

## Delivery status — partial foundations already exist

Already available or substantially advanced:
- stable `/api/v1` route contract;
- Python client;
- TypeScript reference client;
- package/module/profile conventions;
- first-class customer profiles;
- compatibility/migration gates;
- source-neutral domain binding contracts;
- Skill/runtime extension contracts;
- deployment profiles and strong developer documentation.

Still required for the v0.7 gate:
- full Python and TypeScript SDK coverage of supported public operations;
- CLI;
- profile/adapter/application scaffolding;
- generated API/SDK documentation;
- ontology/profile validation tooling exposed as supported developer flows;
- reusable templates/examples;
- clean-room developer qualification.

Target developer flows:
- `cepio new-profile <name>`
- `cepio new-adapter <system>`
- `cepio new-app <name>`
- `cepio validate`
- `cepio query`
- `cepio migrate`
- `cepio deploy`

**Gate:** a clean-room developer can build a simple customer profile, adapter and application through supported tooling without editing canonical core modules.

---

# v0.8 — Enterprise Runtime

**Epic:** #61

**Outcome:** qualify CEPIO for sustained enterprise operation.

## Foundations already pulled forward

Governance v2, security/static-analysis ratchets, CodeQL, SBOM/provenance generation, workload/deployment patterns, restart/idempotency correctness and runtime observability all reduce the remaining v0.8 scope.

The product gate still requires enterprise-scale operational qualification:
- horizontal scale and stateless service patterns;
- HA persistence;
- production queue/event processing and distributed workers;
- retries/dead-letter handling across real dependencies;
- adapter circuit breakers and backpressure;
- workload identity/private networking/Key Vault;
- backup/restore and disaster recovery;
- security/penetration qualification;
- operational dashboards and SLO/error-budget program.

Tenancy position: prefer one enterprise deployment boundary initially while preserving explicit tenant/isolation primitives for future shared deployments.

**Gate:** CEPIO survives node/service restart, duplicate messages, stale writes and adapter/dependency outages without semantic or workflow corruption, with measured SLOs and operational runbooks.

---

# v0.9 — Second Enterprise Adoption

**Epic:** #62

**Outcome:** prove that CEPIO is portable across materially different Energy & Process Industry enterprises in real deployment, not merely in synthetic qualification.

## Generalization evidence already achieved

The Generalization Lab has materially de-risked this milestone:
- refinery/process-manufacturing normalized semantic benchmark reached 100% capability coverage;
- drilling contractor semantic and runtime qualification is on `main`;
- the same frozen drilling contract has been qualified across synthetic operating models for ARO Drilling, SANAD, Nabors Industries and Arabian Drilling without customer-specific semantic overrides;
- subsurface now follows an explicit OSDU-first extension boundary.

This is strong **semantic/runtime portability evidence**, but it is not the v0.9 gate.

The remaining proof must use at least two materially different real enterprise deployments/profiles and measure:
- canonical class reuse;
- canonical relationship reuse;
- profile-specific additions;
- CEPIO-Core code modifications required;
- adapter reuse;
- application/workflow reuse;
- migration impact on enterprise #1.

**Gate:** enterprise #2 is implemented primarily through profiles, adapters and application configuration while enterprise #1 remains stable.

---

# v1.0 — Production Platform

**Epic:** #63

**Outcome:** establish explicit production guarantees rather than add another major feature wave.

Required guarantees:

### Semantic compatibility
- versioned ontology/module contracts;
- explicit migrations for breaking semantic changes;
- stable profile dependency/version rules.

### API compatibility
- stable `/api/v1`;
- documented deprecation policy;
- SDK compatibility tests.

### Security
- authenticated identity and actor-scoped authorization;
- no client-supplied privilege authority;
- immutable/auditable governed action and workflow history;
- security review/penetration testing.

### Runtime
- repeatable deployment;
- HA/scale qualification;
- backup/restore and disaster recovery;
- telemetry/runbooks;
- defined and measured SLOs.

### Integration
- production-quality SAP and PI baseline;
- OSDU/P6 according to reference deployments;
- governed and reconciled external writeback.

### Kinetic execution
- durable workflow execution;
- replay/idempotency guarantees across workflow steps;
- human approval and policy enforcement;
- async/long-running action handling;
- compensation and verified outcome tracking.

### Adoption
- at least two materially different enterprise profiles/deployments;
- enterprise #2 does not destabilize enterprise #1;
- published documentation supports teams other than original authors.

**Gate:** v0.4-v0.9 product gates complete, compatibility/security/SLO/DR guarantees are qualified, two-enterprise portability evidence exists, and a clean-room deployment succeeds from published documentation.

---

# Program view

| Release | Product claim | Current delivery posture | GitHub epic |
| --- | --- | --- | --- |
| v0.4 | deployable Microsoft-native industrial semantic runtime | **Qualified** | #22 / gate #50 |
| v0.5 | live operation over industrial source systems | **Current critical path** | #51 |
| v0.6 | governed kinetic orchestration + reference industrial application | **Runtime foundations substantially pulled forward; live app proof pending** | #67 + #59 |
| v0.7 | independent developers can extend CEPIO | **Partial foundations already available** | #60 |
| v0.8 | enterprise-operable runtime | **Governance/security/observability foundations pulled forward** | #61 |
| v0.9 | portable across enterprises | **Semantic/runtime generalization de-risked; real deployment proof future** | #62 |
| v1.0 | production guarantees | **Future release gate** | #63 |

## Current execution order

### COMPLETED — CEPIO v0.4 Developer Preview
- Developer Preview qualified through #66/#69 and related platform/API gates.

### NOW — finish CEPIO v0.5 live integration
1. Close remaining #2 provenance integration/security qualification.
2. Complete #52 Adapter SDK beyond the existing write/verify/reconcile subset.
3. Implement #53 SAP and #54 PI around the K-201 scenario.
4. Qualify #57 against real SAP identity/write/read-back/failure behavior.
5. Use #55 OSDU or #56 P6 as the third source-system domain.
6. Execute #58 end-to-end and qualify CEPIO v0.5.

### ALREADY PULLED FORWARD — reduce post-v0.5 scope
- #67 durable Kinetic foundations, verification, Outcomes and contextual policy are substantially implemented.
- Skills runtime admission and READY-only dispatch are on `main`.
- Core evidence/uncertainty and Kinetic Opportunity semantics are on `main`.
- OSDU-first subsurface federation/runtime bindings are on `main`.
- drilling runtime + cross-customer qualification is on `main`.
- refinery/process normalized semantic benchmark is at 100% capability coverage.
- Governance v2 and publication/IP boundaries are active.

### NEXT — CEPIO v0.6 becomes a compressed application qualification milestone
- complete remaining #67 trigger/control/telemetry surfaces needed by the lighthouse;
- build #59 Asset Reliability / Maintenance Command Center on qualified v0.5 integrations;
- prove the complete live operating loop without source-specific business logic in the application.

### THEN — v0.7 / v0.8 can proceed with reduced foundational scope
- v0.7: CLI, scaffolding, complete SDK/tooling and clean-room developer proof;
- v0.8: HA, distributed workers/queues, DR, SLOs and production security/operations qualification.

### LATER — v0.9 / v1.0
- v0.9: real second-enterprise deployment portability proof;
- v1.0: freeze and qualify production guarantees rather than add major new feature families.

### DEFERRED / NON-BLOCKING
- #20 Purview governance + lineage bridge.
- #25 GPU AKS cuGraph validation / benchmarking.

## Near-term roadmap rule

Until v0.5 is qualified, prioritize work in this order:

`live adapter capability -> K-201 end-to-end proof -> remaining lighthouse runtime gap -> reference application -> developer/enterprise platformization`

Avoid broad canonical-semantic expansion unless a frozen domain challenge or live integration demonstrates a reusable gap.
