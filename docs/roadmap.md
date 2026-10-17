# CEPIO Execution Roadmap

## North Star

> **Aim for CEPIO to provide the same class of enterprise operating abstraction that Palantir Ontology provides — specialized for Energy & Process Industries and native to the Microsoft ecosystem.**

CEPIO owns the canonical industrial semantic and operational contract. Microsoft services provide the data, semantic materialization, AI, application hosting and infrastructure planes on which that contract is realized.

`CEPIO semantic contract -> Microsoft platform bindings -> customer deployment`

The governing product rule from v0.4 onward is:

> **Every CEPIO release must prove a stronger operating capability, not merely introduce more ontology vocabulary.**

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

# Current — v0.4 Microsoft Platform Extension + Developer Preview

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

## Current critical path

### #6 — Runtime observability / OpenTelemetry

- structured events for query, repository, function, policy, MCP, action and adapter execution;
- latency / success / failure metrics;
- distributed trace correlation across Foundry -> MCP -> CEPIO -> adapter;
- OpenTelemetry-compatible hook boundary;
- no unauthorized industrial data in telemetry payloads.

Implementation is in PR #66 and must pass CI before #6 is complete.

### #50 — Developer Preview release gate

Required artifacts:
- stable `/api/v1` and committed OpenAPI baseline;
- Python and TypeScript client validation/generation;
- authentication guide;
- pagination/query guide;
- error, ETag/If-Match and idempotency guide;
- App Service or AKS deployment quickstart;
- diagnostics/OpenTelemetry quickstart;
- representative API examples;
- measured query/load baseline.

## Deferred / non-blocking for v0.4

- #20 Purview governance and lineage bridge.
- #25 GPU AKS / cuGraph validation and benchmarking.

## v0.4 release gate

A Microsoft-native reference deployment should demonstrate:

1. CEPIO canonical semantics materialized through Fabric/Fabric IQ;
2. Foundry/MCP consumption without bypassing CEPIO policy;
3. Entra-authenticated `/api/v1` with stable OpenAPI, error, concurrency and pagination contracts;
4. production query execution without normal full in-process scans;
5. App Service or AKS reference deployment;
6. runtime observability through OpenTelemetry-compatible hooks;
7. all CEPIO core tests remain cloud-independent and executable offline;
8. #50 Developer Preview gate passes.

Sequence:

`API hardening ✓ -> query scale ✓ -> deployment ✓ -> #6 observability -> #50 Developer Preview gate -> v0.4 tag`

Release designation: **CEPIO v0.4 — Developer Preview**.

---

## Drilling-contractor domain qualification v0.4 — independent lab milestone

The frozen drilling domain-qualification benchmark is a domain milestone, not the CEPIO v0.4 product release. It adds enterprise, performance/optimization, contract, and digital/AI personas; tests enterprise, operational-optimization, and agentic-operations challenges; and retains its initial CORE gap classifications before ontology remediation. Its pack version and historical results remain independent of product release numbering.

See [Drilling Domain Qualification v0.4](drilling-domain-qualification-v0.4.md) and [ADR-0010](adr/ADR-0010-drilling-domain-qualification.md). The isolated qualification workflow publishes benchmark evidence without changing existing product gates.

---

# v0.5 — Live Industrial Integration

**Epic:** #51

**Outcome:** prove that CEPIO can operate over real industrial systems and close the governed writeback loop.

## Prerequisite

- #2 Property provenance and lineage kernel must be completed before broad live-system onboarding.

## Work packages

- #52 Integration adapter SDK and connector contract.
- #53 SAP S/4HANA maintenance and enterprise adapter.
- #54 AVEVA PI operational state adapter.
- #55 OSDU subsurface and upstream context adapter.
- #56 Primavera P6 project and schedule adapter.
- #57 External identity reconciliation and governed writeback.
- #58 Live industrial compressor reference scenario.

## Recommended dependency order

`#2 -> #52 -> (#53 + #54) -> #57 -> #58`

Then add at least one engineering/project context path:

`#55 or #56 -> #58`

## Reference architecture

`SAP + PI + OSDU/P6 -> CEPIO identity/state/provenance -> reasoning/decision -> policy -> action -> source-system writeback -> reconciliation/audit`

## Adapter contract

Every live source adapter should implement equivalent capabilities for:

`discover() -> read() -> subscribe() -> map() -> reconcile() -> write() -> verify()`

with source identity, timestamps, mapping version, provenance, reconciliation status and stable error/retry semantics.

## Reference proof

For one compressor, CEPIO should combine:
- enterprise identity/maintenance context from SAP;
- operational measurements/events/state from PI;
- engineering/project context from OSDU or P6;
- CEPIO provenance, reasoning, Decision and Action records;
- one human-authorized external maintenance writeback;
- source-system verification and reconciliation.

Reference flow:

`PI anomaly -> CEPIO event/state -> reliability reasoning -> Decision -> human authorization -> CEPIO Action -> SAP work order -> verification -> reconciliation/audit`

## v0.5 release gate

One industrial asset is represented using context from at least three source-system domains, material values/state are explainable through provenance, and one external writeback is authorized, idempotent, verified and reconciled.

---

# v0.6 — Kinetic Runtime + Reference Industrial Applications

**Application epic:** #59  
**Kinetic runtime:** #67

**Outcome:** turn CEPIO from an ontology/runtime that can execute isolated functions and actions into a controlled enterprise operating abstraction that can orchestrate complete industrial business processes, then prove that capability in a reference industrial application.

## #67 — Kinetic runtime and workflow orchestration

CEPIO already has typed Functions, Decision records, governed Actions, preconditions, policy authorization, idempotency, audit and basic compensation. The missing layer is first-class orchestration across those capabilities.

### Primary kinetic model

`Event/State -> Trigger -> Workflow -> Function -> Decision -> Approval -> Action -> Verify -> Outcome`

First-class kinetic concepts:
- Function;
- Decision;
- Action;
- Workflow;
- Trigger;
- Task;
- Approval;
- Constraint;
- Policy;
- Compensation;
- Outcome.

### Required runtime capabilities

- `WorkflowDefinition` and durable `WorkflowInstance` contracts;
- event, state, time and authenticated manual triggers;
- ordered workflow steps that invoke CEPIO Functions, Decisions and Actions;
- human approval tasks with pause/resume semantics;
- async and long-running Action execution;
- retries, timeout, cancellation and terminal-failure states;
- compensation / rollback orchestration;
- completion and Outcome tracking;
- deterministic workflow history and audit linkage;
- policy evaluation at every governed step;
- replay-safe/idempotent execution;
- sanitized telemetry through the CEPIO observability contract;
- external side effects only through governed adapter/action/writeback paths.

### Architecture rules

- semantic object/state remains separate from workflow execution state;
- workflows reference canonical CEPIO objects/functions/actions rather than source-specific types;
- no workflow or agent path may bypass CEPIO identity, policy, Action Runtime or audit;
- long-running workflow state must survive process restart;
- external side effects use #57 reconciliation/writeback and are verified before the workflow records successful completion;
- agent-initiated workflows remain bounded by the same permissions and approval requirements as human/API callers.

### Kinetic runtime gate

A reliability/maintenance workflow can be triggered by an operational event, call a typed Function, persist a Decision, pause for human approval, execute a governed Action, verify an external result, record an Outcome, survive restart/replay and expose a complete audit/telemetry chain.

Recommended sequence:

`v0.5 live integrations -> #57 governed writeback/reconciliation -> #67 kinetic runtime -> #59 reference application`

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

Prefer bounded agents such as Reliability, Maintenance Planning, Operations Risk, Materials and Cost agents, all operating through CEPIO policy, workflow and action contracts.

Follow-on applications:
- Refinery Margin / Constraint Optimization;
- Turnaround Planning.

**v0.6 gate:** one reference application demonstrates the complete `Observe -> Understand -> Reason -> Decide -> Authorize -> Act -> Observe outcome` loop over live v0.5 integrations using the first-class kinetic runtime rather than application-specific orchestration.

---

# v0.7 — Developer Platform

**Epic:** #60

**Outcome:** independent engineering teams can extend CEPIO without modifying CEPIO-Core.

Key deliverables:
- Python SDK;
- TypeScript SDK;
- CLI;
- profile/adapter/application scaffolding;
- package/module/profile conventions;
- generated API/SDK documentation;
- ontology/profile validation tooling;
- developer templates and examples.

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

Key workstreams:
- horizontal scale and stateless service patterns;
- HA persistence;
- queue/event processing, retries and dead-letter handling;
- adapter circuit breakers and backpressure;
- workload identity/private networking/Key Vault;
- immutable and auditable action/workflow history;
- security testing;
- backup/restore and disaster recovery;
- operational dashboards and SLO/error-budget program.

Tenancy position: prefer one enterprise deployment boundary initially while preserving explicit tenant/isolation primitives for future shared deployments.

**Gate:** CEPIO survives node/service restart, duplicate messages, stale writes and adapter/dependency outages without semantic or workflow corruption, with measured SLOs and operational runbooks.

---

# v0.9 — Second Enterprise Adoption

**Epic:** #62

**Outcome:** prove that CEPIO is portable across materially different Energy & Process Industry enterprises.

Preferred proof: use a substantially different operating model from the refinery/process reference. ARO Drilling is a strong candidate because it tests offshore drilling semantics, workflows and personas against the same canonical platform.

Measure:
- canonical class reuse;
- canonical relationship reuse;
- profile-specific additions;
- CEPIO-Core code modifications required;
- adapter reuse;
- application/workflow reuse;
- migration impact on customer #1.

**Gate:** customer #2 is implemented primarily through profiles, adapters and application configuration, and customer #1 remains stable.

---

# v1.0 — Production Platform

**Epic:** #63

**Outcome:** establish explicit production guarantees rather than simply add more features.

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
- customer #2 does not destabilize customer #1;
- published documentation supports teams other than original authors.

**Gate:** v0.4-v0.9 gates complete, compatibility/security/SLO/DR guarantees are qualified, two-enterprise portability evidence exists, and a clean-room deployment succeeds from published documentation.

---

# Program view

| Release | Product claim | GitHub epic |
| --- | --- | --- |
| v0.4 | deployable Microsoft-native industrial semantic runtime | #22 / gate #50 |
| v0.5 | live operation over industrial source systems | #51 |
| v0.6 | durable kinetic orchestration + reference industrial applications | #67 + #59 |
| v0.7 | independent developers can extend CEPIO | #60 |
| v0.8 | enterprise-operable runtime | #61 |
| v0.9 | portable across enterprises | #62 |
| v1.0 | production guarantees | #63 |

## Current execution order

### NOW — finish v0.4
- #6 Runtime observability / OpenTelemetry — implementation PR #66.
- #50 Developer Preview release gate.

### THEN — v0.5 live integration
- #2 Property provenance and lineage kernel.
- #52 adapter contract.
- #53 SAP adapter.
- #54 PI adapter.
- #57 identity reconciliation/governed writeback.
- #55 or #56 engineering/project context adapter.
- #58 live compressor reference scenario.

### THEN — v0.6 kinetic + application
- #67 Kinetic runtime and workflow orchestration.
- #59 Asset Reliability / Maintenance Command Center.

### DEFERRED / NON-BLOCKING
- #20 Purview governance + lineage bridge.
- #25 GPU AKS cuGraph validation / benchmarking.
