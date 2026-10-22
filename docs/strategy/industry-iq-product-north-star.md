# CEPIO / Industry IQ — Product North Star & Strategic Doctrine

**Adopted product direction:** 2026-10-22  
**Status:** strategic product doctrine; proposed service and roadmap investments are not delivered capabilities or release qualifications.  
**Audience:** CEPIO product, architecture, engineering, Industry IQ Studio, CEPIO Labs, partners, and product leadership.

> This document states **what we seek to achieve**, **why a professional should use Industry IQ**, and **what we will deliberately own**. Technical implementation and product readiness are governed by their respective contracts, ADRs, release gates, and evidence.

## 1. Four levels of strategy

| Level | Statement | Interpretation |
| --- | --- | --- |
| **Mission — why** | **Democratize industrial expertise and elevate human professional excellence.** | Help every industrial professional make better decisions and grow their competence, without displacing accountable human judgment. |
| **Product North Star — what** | **The indispensable expert companion for every industrial professional.** | A trustworthy companion that understands the person's work, proactively surfaces what matters, reasons with industrial rigor, and helps turn insight into governed, verified outcomes. |
| **Technology North Star — how** | **Thin infrastructure. Thick Industry IQ.** | Portable Industrial Operating Intelligence for Energy & Process Industries; maximize reusable industrial competence, not infrastructure duplication. |
| **Engineering doctrine — how we build** | **Reuse → Bind → Extend → Own.** | Own reusable industrial semantics, competence, assurance, decisions, authority and outcomes; bind to data platforms, identity, generic models, agent runtimes and systems of record. |

These statements are complementary, not a replacement of CEPIO's existing architecture. We begin with energy, drilling, reliability and process industries, and expand through validated generalization—not through unsupported claims of universal competency.

**Long-term aspiration:** one million professionals making better decisions because Industry IQ is part of how they work. This is an aspiration, not a current metric or forecast.

## 2. The professional promise

The product must earn the right to be the first place an engineer, technician, planner, operator, or operational leader turns for their next consequential industrial decision.

Seven experience principles:

1. **Understand my profession:** role, objectives, responsibilities, task, asset, operating context, and applicable standards—not generic conversation alone.
2. **Know what deserves attention:** prioritized, authorized, evidence-backed signals; be useful before receiving a sophisticated prompt.
3. **Reason like an industrial expert:** competing hypotheses, deterministic tools where warranted, physical/operating constraints, uncertainty, and justified abstention.
4. **Help complete real work:** prepare decisions, hand off for human authorization, orchestrate permitted actions, and verify outcomes through authoritative systems.
5. **Help me become better:** explain reasoning, tutor and challenge appropriately, and preserve reusable professional lessons without rating or surveilling workers by default.
6. **Be worthy of trust:** precise evidence/provenance and freshness, scope and qualification status, authorization boundaries, refusal, and verifiable audit—not opaque or invented confidence.
7. **Meet me where I work:** headless REST/MCP first, presented through Teams, Copilot, web, mobile and embedded applications as appropriate.

The professional should not need to inspect ontology, YAML, Skill packages, or engineering infrastructure to perceive value. Expert Mode should provide bounded, licensed/public-knowledge usefulness before enterprise integration; Connected Mode uses authorized enterprise context; Action Mode adds explicitly governed execution and verification. No demo or synthetic observation may masquerade as live asset evidence.

**Central product hypothesis:** repeated professional usefulness, not breadth of AI features, determines adoption.

## 3. Product boundaries and ownership

- **CEPIO Core:** headless, source-neutral industrial operating contract, evidence/identity/state/time, qualified Industry IQ, performance, Skills, policy, authority, Decisions, governed Actions, memory/context and verifiable Outcomes.
- **CEPIO Labs (protected):** expert knowledge development, scenario/casebook research, synthetic data, independent evals, protected Skills, holdouts, value-assurance and promotion proposals. Lab test results are not field proof.
- **Industry IQ Studio:** builder/operator/technical-authority surface for inspecting, configuring, evaluating, qualifying, publishing and operating Industry IQ through governed CEPIO contracts. Studio is *not* the personal day-to-day workspace by default.
- **Industry IQ Companion (proposed logical experience):** profession-adaptive daily guidance, investigations, evidence-led decisions, learning, attention, and outcome continuity. Delivered through existing hosts and interfaces; **not** a fourth industrial runtime or automatically a fourth repository.

CEPIO must not depend on Studio or Companion. They consume its stable contracts; Labs may support both with approved, protected interfaces. Generic model planning/agent execution belongs to host platforms; industrial authority stays within CEPIO. For Microsoft reference deployments: **Microsoft owns generic agent execution; CEPIO owns industrial agency.**

### Existing foundations to reuse

The current codebase contains Industry IQ Packs, Capability/Skill registries, persona-scoped ICC qualification, Profile/Semantic/Procedural/Episodic memory contracts, Performance Contracts and specialization, provenance, policy/authority, governed workflow/Outcome foundations, REST/MCP/Management projections, Teams Attention foundations, and a Foundry reliability lighthouse path.

These are foundations, **not** proof that Companion, proactive operations, live SAP/PI, or enterprise value outcomes are product-qualified.

## 4. Strategic moat: the Industrial Competence Network

**Thesis:** our defensible advantage must be accumulated **qualified industrial competence** and trust, rather than commodity AI models, prompts, ontology size, cloud infrastructure, or a generic agent host.

Five mutually reinforcing, differently mature moats:

1. **Proprietary industrial competence:** reviewed failure patterns, diagnostic methods, technical constraints, decision procedures, reusable executable Skills and validated cross-domain abstractions.
2. **Industrial assurance:** difficult independent holdouts, specialist rubrics, negative/refusal cases, evidence and policy checks, model/tool parity experiments, qualification provenance and transparent limits.
3. **Decision-to-outcome learning:** where contracts and consent permit, link evidence → hypotheses → Decision → human approval → Action → observed Outcome; promote only generalized, reviewed lessons.
4. **Professional trust and workflow presence:** reliable recurring usefulness, familiar role-aware experiences, and safely preserved task continuity; no customer or personal lock-in through data hostage-taking.
5. **Capability ecosystem:** *later*, OEMs, independent experts and specialist vendors contribute licensed, qualified capabilities subject to governance, IP review, compatibility, liability and distribution terms.

**Compounding flywheel:** qualified expert input → versioned capability → independently tested competence → professional use → permitted outcome feedback → governed generalization and review → stronger qualified capability. More users or raw data do not automatically create a moat. Human review and isolation are hard requirements.

**Core doctrine:** **Own the competence. Prove the competence. Distribute the competence. Compound the competence.**

## 5. Service portfolio: build logically, reuse physically

These are **product capabilities / logical services**, not an instruction to create six standalone microservices or duplicate existing registries.

| Service | Priority | Responsibility | Starting foundation |
| --- | --- | --- | --- |
| **Industry IQ Capability Service** | **P0** | Discover, version, scope, resolve and distribute reusable industrial capabilities and competency maps | Industry IQ Pack/Skill/Capability Registry, ICC, Binding and Performance Contracts |
| **Industry IQ Assurance Service** | **P0** | Independent scenario qualification, domain expert review, casebook/holdout governance, transparency of capability scope and provenance | Labs Scenario Lab, Industrial Evals, value assurance, Capability Registry |
| **Industry IQ Companion Service** | **P0** | Role-adaptive professional entry point: daily work, investigation, recommendation, learning and continuity | Persona bindings, Profile/Episodic Memory, Performance Contracts, CEPIO REST/MCP and host UX |
| **Industrial Attention Service** | **P0** | Filter signals, prioritize relevance, prepare defensible alerts, escalation and task focus | OperationalEvent, workflows, Teams Attention, Foundry G3 planned trigger |
| **Outcome & Value Intelligence Service** | **P1** | Verified Decision/Action/Outcome lineage, operational baselines, effort and attributable economic value, with negative findings included | WorkflowOutcome, Performance Contracts, protected Enterprise Value Assurance |
| **Industrial Expert Network Service** | **P2** | Expert panels, permissioned case contributions, OEM/specialist participation, eventual qualified-capability distribution | Protected Labs, supply-chain/pack trust, capability promotion governance |

**Capability Passport (P0 presentation contract):** show job/persona supported, pack/version, sources/evidence required, methods, authority ceiling, runtime readiness, test scope, withheld/unproven claims and independent review provenance. Do not claim external certification absent a genuine independent certification.

**Industrial Casebook (P0 protected asset):** curate hard, expert-reviewed cases and alternate hypotheses, with provenance, IP rights, held-out answers and permitted-use boundaries. Synthetic volume alone does not establish competence or field reliability.

**Professional Experience Contract (P0 proposed composition):** Who am I? What matters? What do we know? What can I do? What happened? Compose existing identity, persona, memory, Performance, Capability, policy, Decision and Outcome contracts instead of inventing a second source of truth.

## 6. What we own versus leverage

| CEPIO owns | CEPIO reuses/binds |
| --- | --- |
| Industrial meaning, competency/Skill contracts, failure/decision patterns, constraints and engineering/economic methods | Frontier models and generic agent hosting (Foundry/Copilot or replaceable hosts) |
| Qualification/assurance methodology and qualified capability claims | Enterprise data/context platforms (Fabric/Fabric IQ, Cognite, OSDU, etc.) |
| Industrial evidence, authority, policy, Decision/Action/Outcome semantics | Entra or other enterprise identity, plus SAP/Maximo/PI/MES/EAM as authoritative systems |
| Provider-neutral capability registry, specialization and promotion boundaries | Cloud hosting, physical storage, search, observability, scheduling and generic orchestration |
| Governed reusable expert experience contracts and value assurance | Teams, Copilot, web/mobile surfaces, provider integrations |

Never create a generic CEPIO agent framework, proprietary graph database, undifferentiated storage/search platform, or standalone model runtime as a moat project. Own extra infrastructure only when an explicit industrial contract cannot be met otherwise.

## 7. Beachhead: drilling-contractor reliability

The initial professional reference journey is **Reliability Engineer — Top Drives and Mud Pumps**. Prove:

1. Professional receives or initiates a justified attention/investigation.
2. CEPIO resolves authorized asset context and source freshness.
3. Relevant Industry IQ and Skill execute evidence-first diagnostic hypotheses, including alternatives, uncertainty and refusal.
4. User can see the engineering rationale, constraints, and permitted next steps.
5. Where equipped and authorized, a human approves downstream action; CEPIO verifies external Outcome and records learning evidence.

Use CEPIO **API/MCP as the sole industrial authority surface**, the Microsoft Foundry/Teams host where appropriate, and CEPIO Labs for versioned test evidence. Synthetic/demo mode remains plainly labelled and cannot qualify live operational readiness.

**Release independence:** The existing v0.5 CONNECT three-authoritative-source, source-authoritative, verified and reconciled writeback gate—including SAP/PI and current compressor lighthouse requirements—remains open and unchanged. Drilling reliability is the Companion value wedge, not a silent substitute for that release gate. The G0–G7 Reliability Agent Lighthouse remains authoritative for its own qualification.

## 8. Sequencing and decision gates

| Horizon | Strategic outcome | Decision gate / evidence |
| --- | --- | --- |
| **0–3 months** | One compelling reliability companion and Capability Passport; high-quality top-drive/mud-pump casebook; controlled baseline comparisons | Under matched model/data/tool conditions, material reasoning improvement with no critical policy/safety failures; credible review of UX usefulness |
| **3–6 months** | Real design-partner workflows, role-aware attention, independent outcome feedback | Verified bounded pilot, repeat usage, measured preparation effort, documented abstentions and actual approvals |
| **6–12 months** | Reuse into adjacent rotating equipment and roles; platform/customer portability | Pass cross-domain regression, preserve equivalent authority/evidence, demonstrate portability beyond a single environment |
| **12–24 months** | If justified, OEM/expert capability distribution and marketplace pilot | Supply, demand, IP licensing, independent qualification and unit economics established before marketplace investment |

These horizons are **planning hypotheses**, not existing delivery commitments, release dates or verified traction.

## 9. How success is measured

**North Star outcome:** *Industrial professionals making materially better, safer decisions with Industry IQ as part of their recurring work.* Count active professionals **only with qualified usefulness/decision evidence**, not raw chat sessions.

Companion and moat scorecard (distinct from canonical v1 engineering maturity score):

- **Incremental reasoning benefit:** matched B-versus-C comparisons with the same model, evidence, tools, policy and evaluators (CEPIO Labs EVA/VA-1 discipline).
- **Qualified coverage:** proportion of high-value persona decisions supported by versioned, expert-reviewed capability and appropriate refusal behavior.
- **Professional usefulness:** time-to-evidence, investigation preparation effort, repeat weekly usage, returning-user cohorts and user-rated relevance.
- **Verified decision quality:** material evidence correctness, useful recommendations, negative cases, escalation quality and zero unauthorized execution.
- **Outcome/value:** provenance-linked Decision → approved Action → observed Outcome; separately measured KPI effect and finance-validated attribution where possible.
- **Compounding efficiency:** cross-domain reusable qualified capabilities, regression survival and reduced marginal domain onboarding effort.
- **Distribution health:** activated enterprise design partners, recurring professionals and (later) licensed, qualified external capabilities.

**Illustrative pilot targets** (to refine before a study, not current results): at least 95% auditable evidence coverage for consequential recommendations; 40% less investigation preparation effort; 60% follow-on weekly use among activated pilot professionals; **zero** unauthorized operational actions; one demonstrable capability reuse into a second context. Treat all as hypotheses with frozen rubrics, denominators and baselines.

Use the separate Enterprise Value Assurance levels: technical/intelligence superiority does **not** establish operational impact, and operational impact does **not** establish finance-approved enterprise ROI. Include negative results and all lifecycle costs.

## 10. Commercial hypothesis

1. **Professional access/subscriptions:** day-one bounded expert guidance, learning and role-based workflows; test repeat use before scaling marketing.
2. **Enterprise licensing:** qualified capabilities, integrated context, governed operations, support and value assurance; probable initial economic anchor, not an established business fact.
3. **Future ecosystem distribution:** qualifying, licensing and distributing third-party capabilities after permission, verification and clear unit economics.

Buyer and user differ: CIO/COO/digital and operational leaders may sponsor; engineer/operator/planner must experience actual daily value. Distribute through existing workplace surfaces without mandating a particular cloud suite.

## 11. Guardrails and anti-goals

- **Human accountability:** knowledge ≠ authority; recommendation ≠ execution; model output ≠ evidence; synthetic benchmark ≠ field proof; operational KPI ≠ finance-validated ROI.
- **Source sovereignty and IP:** customer context and outcome histories stay customer-controlled; do not copy customer-specific information into shared Labs or globally train on it. Reuse requires licensing/consent, review, sanitized abstraction and independent regression.
- **Worker dignity and privacy:** professional profile and feedback require justified purpose, tenant/role controls and appropriate consent; do not create an employee-surveillance or unaccountable individual scoring system.
- **No premature qualification:** a prototype, demo, passing deterministic test, or merged PR is not a live production claim. Declare uncertainty and unproven limits.
- **No infrastructure distraction:** avoid recreating generic hosts, workflow schedulers, storage/search engines or complex middleware without a demonstrated industrial contract gap.
- **No premature sprawl:** reject unqualified persona/industry expansion, dozens of new contracts that replicate existing contracts, and marketplace features before traction.

## 12. Relationship to existing authoritative artifacts

- [CEPIO README](../../README.md): current technical architecture and runtime boundaries.
- [Execution roadmap](../roadmap.md): authoritative product release gates; unchanged by this doctrine.
- [Current state](../current-state.md): dated shipped/merged/unqualified status.
- [Canonical v1 scorecard](../../config/v1-scorecard.yaml): evidence-backed **engineering maturity**, not a score for professional adoption or moat.
- [Persona-scoped ICC qualification](../icc-persona-qualification-v0.1.md): role-specific qualified capability binding.
- [Memory & Context](../memory-context-architecture.md): bounded context, isolation and memory contracts.
- [Capability Registry / Compounding Intelligence](../capability-registry-and-compounding-intelligence.md): human-reviewed generalization, not auto-learning.
- [Reliability Agent Lighthouse](../reliability-agent-lighthouse.md): Foundry + CEPIO MCP technical/operational proof.
- [Teams Attention](../teams-action-surface-v0.1.md): initial proactive experience foundation.
- [CEPIO Labs protected strategy](https://github.com/faizrten/CEPIO-Labs): detailed casebook, assurance and moat execution remain protected.
- [Industry IQ Studio](https://github.com/faizrten/industry-iq-studio): operator/builder/technical-authority experience; companion is a separate **logical** professional product surface.

**Decision principle for future work:** an investment must improve *professional competence, decision quality, verified execution, qualified reuse, or demonstrated business outcomes*. Infrastructure is a means to those ends, not a separate North Star.
