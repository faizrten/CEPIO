# CEPIO Overview

**What CEPIO is building:** An indispensable expert companion for every industrial professional, beginning with Energy & Process Industries. Its mission is to democratize industrial expertise and elevate professional excellence. The durable moat is a qualified **Industrial Competence Network**; customer-specific intelligence remains sovereign.

See [Product North Star & Strategic Doctrine](../strategy/industry-iq-product-north-star.md). The industrial operating abstraction described below is the **technology foundation**, not the complete professional product promise.

## Purpose

Industrial enterprises increasingly have capable systems of record, data platforms, search/index services and frontier models. The harder problem is giving people and AI systems enough **industrial operating competence** to understand what the enterprise means, what evidence is trustworthy, what uncertainty remains, which decisions matter, who has authority and how action should be governed.

CEPIO exists to provide that reusable competence.

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

A compressor may simultaneously exist as an SAP equipment record, PI tags, an engineering hierarchy node, a maintenance subject, a cost object and a geometry node. CEPIO does not replace those systems. It binds them into a stable industrial operating contract and adds reusable intelligence above them.

## North Star

> **Thin infrastructure. Thick Industry IQ.**

```text
General intelligence
       +
Enterprise context
       +
CEPIO Industry IQ
       +
Governance
       =
Safe Industrial Operating Intelligence
```

Frontier models provide general reasoning capability. Fabric, Cognite, OSDU and other platforms provide data and enterprise context. CEPIO provides reusable industrial semantics, evidence requirements, Skills, performance logic, decision patterns, failure/risk patterns, authority, Actions, workflows and competency/evaluation contracts.

Palantir Ontology remains a capability benchmark. It is not CEPIO's product identity.

For the Microsoft reference ecosystem:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

## Product layers

```text
1. Replaceable bindings
   SAP · PI · OSDU · Fabric · Cognite · P6 · MES · other systems
            |
            v
2. Thin CEPIO operating core
   semantics · identity · state · time · evidence · provenance
   uncertainty · policy · authority · Functions · Decisions · Actions
            |
            v
3. Thick Industry IQ
   capabilities · Skills · competency questions · performance contracts
   risk/failure/decision patterns · constraints · KPI/economic logic
   workflows · assurance/evaluation contracts
            |
            v
4. Governed intelligence/context control plane
   Capability Registry · Memory · Retrieval · Compiled Industry IQ
            |
            v
5. Headless experiences
   apps · Studio · copilots · agents · analytics · workflows
```

This separation is central to portability and product focus.

## Thin Core

Core should contain only abstractions that remain broadly reusable across Energy & Process Industry domains and platform choices:

- object and relationship identity;
- events and operational state;
- valid time and transaction time;
- evidence and provenance;
- uncertainty/confidence;
- Functions, Decisions and governed Actions;
- policy, authority and audit;
- compatibility and migration contracts.

Core should remain deliberately thin.

## Thick Industry IQ

CEPIO's differentiated IP should accumulate in reusable industrial competence:

- domain semantic compositions;
- personas and competency questions;
- evidence requirements;
- Skills and procedures;
- failure/degradation/risk patterns;
- decision/intervention patterns;
- operating constraints;
- KPI, performance and economic logic;
- governed workflows;
- evaluation and assurance benchmarks.

The desired signal is not ontology growth. It is **increasing industrial competency with decreasing Core disruption**.

## Customer operating knowledge

Customer-specific proprietary logic should normally remain in Customer Profiles, tenant-scoped memory or private Industry IQ extensions rather than leaking into canonical Core or global reusable knowledge.

This preserves two things simultaneously:

1. CEPIO can generalize across enterprises;
2. each enterprise can retain proprietary operating knowledge, formulas, thresholds and decision logic.

Customer operational knowledge does not silently train or mutate global CEPIO Industry IQ.

## Compounding intelligence

CEPIO now has an explicit evidence-backed compounding path:

```text
Domain Onboarding
 -> qualified capability evidence
 -> Capability Registry
 -> reuse/promotion candidate
 -> cross-domain regression
 -> human-governed promotion
```

Capability Registry, Industry IQ Pack Registry and Skill Registry serve different purposes:

- Capability Registry — what CEPIO can legitimately claim it knows how to do;
- Industry IQ Pack Registry — what reusable industrial intelligence is deployed;
- Skill Registry — what procedures are admissible/executable in a runtime.

## Memory and model context

CEPIO separates durable knowledge from bounded working context.

> **Industry IQ knowledge may compound continuously; runtime working context remains bounded.**

Memory, retrieval/indexes and compiled caches are controlled runtime mechanisms. They are not new sources of industrial truth or authority.

## Enterprise performance intelligence

Performance Contracts connect objectives, KRs, KPIs, guardrails, accountability and contribution relationships to governed response pathways.

Reference performance semantics may be reusable across an industry, while customer formulas, targets, thresholds, organizational scope and source bindings remain customer specialization.

## Design principles

### 1. Bind authoritative systems rather than recreate them

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

### 2. Canonical semantics before source schemas

A source field maps into a CEPIO property, relationship, observation, provenance assertion or profile-specific extension. Source-system structure is not copied blindly.

### 3. Evidence before inference

An answer, recommendation or Decision should be traceable to evidence visible to the actor at the relevant time.

### 4. Time and uncertainty are first-class

CEPIO distinguishes valid time from transaction time and should represent uncertainty explicitly rather than hiding it inside prose/model output.

### 5. Recommendation is not authority

Knowledge, recommendation, Decision authority and execution authority are separate concerns.

### 6. Actions are governed

External side effects require authenticated identity, policy, preconditions, idempotency, audit and source verification/reconciliation.

### 7. Cache/index/model output is not authority

```text
Index != Source of Truth
Cache != Authority
Model Output != Evidence
```

### 8. Headless first

CEPIO is headless at its core. UI, Studio, copilots and agents are persona-adaptive experiences over the same governed operating contract.

> **Same industrial reality. Different experience for every decision-maker.**

### 9. Microsoft-native, not Microsoft-dependent

Microsoft Fabric, Foundry, Entra and Azure services are the primary reference ecosystem, but they implement CEPIO capabilities rather than define CEPIO industrial semantics.

## Industry scope

CEPIO is designed first for Energy & Process Industries and shared asset-intensive patterns:

- upstream oil and gas;
- drilling contractors;
- midstream;
- refining;
- petrochemicals and chemicals;
- process manufacturing;
- EPCIC / capital projects;
- shared reliability, maintenance, HSE, workforce, supply and commercial patterns.

The same architecture may extend into mining, power and utilities where reusable industrial patterns hold.

## Target users

Primary value is created for engineers, planners and operational leaders whose decisions cross multiple systems. Digital/data/AI teams build applications and agents on CEPIO. Platform teams bind authoritative systems. Governance users define evidence and authority boundaries. AI agents are first-class software consumers operating under those same controls.

See [Target Users / Personas](19-Target-Users-Personas.md).

## Competency as product proof

CEPIO should be judged by how much real industrial work it can support through a stable, reusable and governed contract.

```text
Persona
 -> Responsibility
 -> Decision
 -> Competency question
 -> Required capability/evidence
 -> Skill / Function / Decision / Action
 -> PASS / PARTIAL / FAIL / NOT_RUN
```

See [Competency & Assurance](20-Competency-Assurance.md).

## Product and repository status

- **Published release:** CEPIO v0.4 FOUNDATION — Developer Preview.
- **Current release gate:** CEPIO v0.5 CONNECT — open / partial.
- **Repository main:** includes substantial later-stage foundations beyond the v0.4 guarantee.
- **Canonical v1 maturity score:** 69/100 at the governed evidence snapshot.

See [Current State](../current-state.md), [Roadmap](17-Roadmap.md) and [v1 Completion Scorecard](../v1-completion-scorecard.md).

## Core value proposition

CEPIO is valuable when it reduces:

- repeated semantic integration;
- application coupling to source schemas;
- agent reasoning directly over raw enterprise representations;
- duplicated industrial business logic;
- missing evidence/provenance;
- hidden uncertainty;
- unsafe AI-to-action pathways;
- customer-specific contamination of reusable semantics;
- unbounded model context as knowledge grows;
- migration risk when data platforms or source systems change.

The objective is not to build the largest ontology or another industrial platform. It is to build the strongest reusable **Industry IQ for governed industrial work**.
