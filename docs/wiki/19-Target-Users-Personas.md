# Target Users / Personas

**Product North Star:** [The indispensable expert companion for every industrial professional](../strategy/industry-iq-product-north-star.md). The **professional** is the ultimate beneficiary; an authenticated AI agent, Studio or application is a delivery/execution channel, not the principal reason the product exists. Trustworthy job completion, professional learning and verified industrial outcomes—not merely tooling reuse—must guide persona priorities.

## Who CEPIO is for

CEPIO is built for **industrial engineers, planners and operational leaders who need trusted cross-system intelligence to make and execute decisions**, and for the digital, data, integration and AI teams building the applications and agents that support them.

The current North Star sharpens this distinction:

> **CEPIO is not primarily a UI product or generic infrastructure platform. It is reusable Industry IQ behind persona-specific experiences.**

A Reliability Engineer may never use a product screen labelled "CEPIO." A reliability application, Studio experience, copilot or agent consumes CEPIO's governed industrial operating contract and Industry IQ on that user's behalf.

## Primary user classes

### 1. Industrial decision-makers

These users realize the operational value. Their work crosses multiple systems and requires semantics, evidence, time, uncertainty, risk, performance/economic context and authority.

Representative roles include:

- Reliability Engineer;
- Maintenance Engineer / Planner;
- Operations Engineer;
- Production Engineer;
- Process Engineer;
- Asset Integrity Engineer;
- Process Safety Engineer;
- Planning / Scheduling Engineer;
- Drilling Engineer / Superintendent;
- Reservoir / subsurface roles where applicable;
- Asset / Operations / Plant / Rig leadership.

Their interaction is normally through a CEPIO-powered application, copilot, workflow or agent rather than the runtime directly.

### 2. Industrial application and AI builders

These users build directly on CEPIO contracts:

- AI Engineer;
- Agent Developer;
- Data Scientist;
- Application Developer;
- Digital Product Team;
- Solution Architect.

They use CEPIO APIs, SDKs, MCP, Skills, competency contracts, Performance Contracts and governed runtime capabilities instead of rebuilding industrial context separately for every application.

### 3. Industrial platform and integration teams

These users connect enterprise reality to CEPIO:

- Industrial Data Architect;
- Enterprise Architect;
- Ontology / Domain Engineer;
- Data Engineer;
- Integration Engineer;
- OT / IT Platform Engineer.

Their job is to bind SAP, PI, OSDU, Fabric, Cognite, MES, engineering systems and other authoritative providers into CEPIO while preserving source ownership, canonical identity, provenance and write/verify/reconcile boundaries.

### 4. Governance and assurance users

These users define or inspect the trust boundary:

- Technical Authority;
- Operations / Asset Manager;
- Risk and Compliance;
- Data Steward;
- Security / Identity Administrator;
- HSE / Process Safety authority;
- assurance / audit roles.

They care about evidence requirements, policy, authority, approvals, provenance, temporal correctness, audit, pack trust and outcome verification.

### 5. AI agents as software consumers

AI agents are first-class CEPIO consumers, but they are not autonomous sources of industrial authority.

An agent may:

- discover governed industrial context;
- retrieve authorized evidence;
- invoke permitted Functions;
- evaluate a READY Skill;
- create/evaluate a Decision;
- recommend an Action.

Execution authority remains a separate policy decision.

```text
Knowledge != Authority
Recommendation != Execution
Model Output != Evidence
```

For Microsoft-hosted workloads:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

## Economic buyers and sponsors

Likely sponsor roles include:

- CIO / CTO / CDO;
- Chief AI / Digital Officer;
- VP / EVP Digital;
- Head of Industrial Digitalization;
- COO / EVP Operations;
- Asset / Manufacturing leadership.

This remains a product/GTM hypothesis rather than proof of established purchasing behavior.

Buyer and daily user are often different:

```text
CIO / CDO / CTO / COO
      economic sponsor
             |
             v
Industrial AI / digital platform
             |
      +------+------+
      |             |
platform builders   domain teams
      |             |
      |       engineers / planners / leaders
      |             |
      +-------> CEPIO-powered decisions
```

## Primary persona design anchor

The initial product-design center of gravity remains **engineers, planners and operational managers whose decisions span multiple systems**.

This is where CEPIO's differentiation is strongest:

- cross-system semantic context;
- evidence and provenance;
- uncertainty;
- failure/risk/constraint patterns;
- performance/KPI/economic logic;
- governed Decision/Action patterns;
- reusable Skills and competencies.

Frontline operators and technicians can consume CEPIO-powered experiences, but they should not force CEPIO Core toward a monolithic frontline UI.

## Domain persona families

### Asset / reliability / maintenance

- Reliability Engineer;
- Maintenance Engineer;
- Maintenance Planner;
- Asset Integrity Engineer;
- Rotating Equipment Engineer;
- Maintenance Manager.

### Operations / process manufacturing

- Operations Engineer;
- Production Engineer;
- Process Engineer;
- Shift Supervisor;
- Operations Manager;
- Optimization / APC Engineer;
- Production Scheduler;
- Energy / Quality Engineer.

### Safety / integrity

- HSE Engineer / Manager;
- Process Safety Engineer;
- Inspection / Corrosion Engineer;
- Technical Authority.

### Upstream / subsurface

- Reservoir Engineer;
- Geologist;
- Geophysicist;
- Petrophysicist;
- Production Technologist;
- Well Engineer;
- Field Development Planner.

### Drilling contractor

- Drilling Engineer;
- Rig Manager / Toolpusher;
- Drilling Superintendent;
- Maintenance Superintendent;
- HSE Superintendent;
- Well Control Authority;
- Performance Engineer;
- Commercial Manager.

## Persona-to-Industry-IQ contract

Personas should map to concrete industrial decisions and competency requirements rather than remain role catalogs.

```text
Persona
  -> Jobs / responsibilities
  -> Decisions
  -> Competency questions
  -> Required evidence
  -> Required Industry IQ
     - semantics
     - Skills
     - performance/risk/failure patterns
     - constraints
     - KPI/economic logic
     - authority/action patterns
  -> Assurance result
```

Example — Maintenance Planner:

> Which currently degraded critical assets require intervention within the next seven days, and which work orders are constrained by spare-part availability, permits or production windows?

That competency requires integrated asset criticality, condition evidence, failure context, work state, inventory, permits, production constraints, temporal state and provenance — not merely a `WorkOrder` class.

## Performance/accountability context

Performance Contracts add a governed way to express objectives, KRs, KPIs, guardrails and accountability across organization, role/persona and individual specialization.

Persona/individual accountability must not be confused with universal enterprise ownership or employee-scoring semantics. Industry reference accountability is a reusable operating-model hypothesis that customer organizations explicitly specialize or suppress.

## Persona-adaptive experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

A Reliability Engineer, Plant Manager, CFO and AI agent may receive different representations of the same operational reality while reasoning against the same underlying governed evidence, Performance Contracts and authority model.

## Current persona evidence

The repository contains broad drilling-contractor and refinery/process-manufacturing persona catalogs. Their presence establishes modeled demand and competency targets, not delivered applications or complete runtime coverage for every role.

The strongest current product/application lighthouse remains Reliability / Maintenance. Drilling and refinery/process work provide broader generalization, Industry IQ and performance-reference evidence.

## Related documentation

- [CEPIO Overview](01-Overview.md)
- [Competency & Assurance](20-Competency-Assurance.md)
- [Enterprise Performance Graph](22-Enterprise-Performance-Graph.md)
- [Industry Performance Packs](25-Industry-Performance-Packs.md)
- [Current State](../current-state.md)
- [Roadmap](17-Roadmap.md)
