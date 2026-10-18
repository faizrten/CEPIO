# Target Users / Personas

## Who CEPIO is for

CEPIO is built for **industrial engineers, planners and operational leaders who need trusted cross-system intelligence to make and execute decisions**, and for the digital, data and AI teams building the applications and agents that support them.

The new North Star sharpens this further:

> **CEPIO is not primarily a UI product or infrastructure platform. It is the reusable Industry IQ that sits behind persona-specific experiences.**

The person using a CEPIO-powered reliability application may never interact with a product labelled "CEPIO." The application, copilot or agent consumes CEPIO's operating contract and Industry IQ on that person's behalf.

## User classes

### 1. Industrial decision-makers

These are the primary value-realization users. They make cross-system decisions where industrial semantics, evidence, state, risk, economics and authority must be combined.

Representative groups include:

- Reliability Engineer;
- Maintenance Engineer / Planner;
- Operations Engineer;
- Production Engineer;
- Process Engineer;
- Asset Integrity Engineer;
- Process Safety Engineer;
- Planning / Scheduling Engineer;
- Drilling Engineer / Superintendent;
- Asset / Operations Manager;
- Plant / Rig / Site leadership.

Their interaction is usually through a CEPIO-powered application, copilot, workflow or agent rather than the CEPIO runtime directly.

### 2. Industrial application and AI builders

These users build on CEPIO directly:

- AI Engineer;
- Agent Developer;
- Data Scientist;
- Application Developer;
- Digital Product Team;
- Solution Architect.

They consume CEPIO through APIs, SDKs, MCP, Skills, competency contracts and governed runtime capabilities rather than rebuilding industrial context independently for each application.

### 3. Industrial platform and data teams

These users connect enterprise reality to CEPIO:

- Industrial Data Architect;
- Enterprise Architect;
- Ontology / Domain Engineer;
- Data Engineer;
- Integration Engineer;
- OT / IT Platform Engineer.

Their job is to bind SAP, PI, OSDU, Fabric, Cognite, MES, engineering systems and other authoritative platforms into CEPIO while preserving source ownership and canonical identity.

### 4. Governance and assurance users

These users define or inspect the trust boundary:

- Technical Authority;
- Operations / Asset Manager;
- Risk and Compliance;
- Data Steward;
- Security / Identity Administrator;
- HSE / Process Safety authority;
- Assurance / audit roles.

They care about evidence requirements, policy, authority, approvals, provenance, temporal correctness, audit and outcome verification.

### 5. AI agents as software consumers

AI agents are first-class CEPIO consumers, but not autonomous sources of authority.

An agent may:

- discover industrial context;
- retrieve authorized evidence;
- invoke permitted Functions;
- execute a bounded Skill;
- create or evaluate Decisions;
- recommend an Action.

Execution authority remains a separate policy decision.

```text
Knowledge != Authority
Recommendation != Execution
```

## Economic buyers and sponsors

Likely sponsors include:

- CIO / CTO / CDO;
- Chief AI / Digital Officer;
- VP / EVP Digital;
- Head of Industrial Digitalization;
- COO / EVP Operations;
- Asset or Manufacturing leadership.

This is a product/GTM hypothesis rather than evidence of established purchasing behavior. CEPIO's economic buyer and daily operational user are usually different roles.

```text
CIO / CDO / CTO / COO
      Economic sponsor
             |
             v
Industrial AI / digital platform
             |
      +------+------+
      |             |
Platform builders   Domain teams
      |             |
      |       engineers / planners / leaders
      |             |
      +-------> CEPIO-powered decisions
```

## Primary persona design anchor

The initial product-design center of gravity should be **engineers, planners and operational managers whose decisions span multiple systems**.

This is where CEPIO's differentiators are strongest:

- cross-system semantic context;
- evidence and provenance;
- uncertainty;
- failure/risk/constraint patterns;
- KPI and economic logic;
- governed decision/action patterns.

Frontline operators and technicians can consume CEPIO-powered experiences, but they should not force CEPIO Core or the product architecture toward a monolithic frontline UI.

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

Personas should not merely be catalog entries. Each persona should map to the industrial decisions and competencies CEPIO must support.

```text
Persona
  -> Jobs / responsibilities
  -> Decisions
  -> Competency questions
  -> Required evidence
  -> Required Industry IQ
     - semantics
     - Skills
     - failure/risk patterns
     - constraints
     - KPI/economic logic
     - authority/action patterns
  -> Assurance result
```

Example — Maintenance Planner:

> Which currently degraded critical assets require intervention within the next seven days, and which work orders are constrained by spare-part availability, permits or production windows?

That competency requires more than a `WorkOrder` class. It requires integrated asset criticality, condition evidence, failure context, work state, inventory, permits, production constraints, temporal state and provenance.

## Persona-adaptive experience principle

CEPIO is **headless at its core and adaptive at its surface**.

> **Same industrial reality. Different experience for every decision-maker.**

A Reliability Engineer, Plant Manager and AI agent may see different representations of the same operational reality, but they should reason against the same underlying governed facts, evidence and authority model.

## Current persona artifacts

The repository currently includes broad refinery/process-manufacturing and drilling-contractor persona catalogs. Their presence establishes modeled demand and competency targets, not complete delivered applications for every role.

See:

- [Drilling persona catalog](../../generalization/personas/drilling-contractor-v0.2.yaml)
- [Refinery persona catalog](../../generalization/personas/refinery-process-manufacturing-v0.2.yaml)
- [Competency & Assurance](20-Competency-Assurance.md)
- [Roadmap](17-Roadmap.md)
