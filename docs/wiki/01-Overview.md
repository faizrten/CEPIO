# CEPIO Overview

## Purpose

Industrial enterprises increasingly have capable data platforms, source systems and frontier models. The harder problem is not storing more data or obtaining more general intelligence. It is giving humans and AI systems enough **industrial operating competence** to understand what the enterprise means, what evidence is trustworthy, which decisions matter, what authority applies and how action should be governed.

CEPIO exists to provide that reusable competence.

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

A compressor may simultaneously exist as an SAP equipment record, PI tags, an engineering hierarchy node, a maintenance subject, a cost object and a 3D geometry node. CEPIO does not attempt to replace those systems. It binds them into a stable operating model and adds reusable industrial intelligence above them.

## North Star

> **Thin infrastructure. Thick industrial intelligence.**

The core product thesis is:

```text
General intelligence
       +
Enterprise context
       +
CEPIO Industry IQ
       +
Governance
       =
Safe industrial operating intelligence
```

Frontier models provide general reasoning capability. Fabric, Cognite, OSDU and other platforms provide data and enterprise context. CEPIO provides reusable industrial semantics, evidence requirements, Skills, decision patterns, failure/risk patterns, authority, Actions, workflows and competency/evaluation contracts.

Palantir Ontology remains a capability benchmark. It is not CEPIO's product identity.

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
3. Thick Industry IQ Packs
   Skills · competency questions · risk/failure patterns
   decision patterns · constraints · KPI/economic logic
   workflows · evaluation benchmarks
            |
            v
4. Headless experiences
   apps · copilots · agents · analytics · workflows
```

This separation is central to portability and product focus.

## What belongs in CEPIO Core

Core should contain only abstractions that remain useful across multiple Energy & Process Industry domains and implementations, such as:

- object and relationship identity;
- operational state and events;
- valid time and transaction time;
- evidence and provenance;
- uncertainty/confidence;
- Functions, Decisions and Actions;
- policy, authority and audit;
- compatibility and migration contracts.

Core should remain deliberately thin.

## Where CEPIO should become thick

CEPIO's differentiated IP should accumulate in reusable Industry IQ Packs:

- domain semantics that generalize;
- industrial Skills and procedures;
- competency questions;
- evidence requirements;
- failure and degradation patterns;
- risk and barrier patterns;
- decision and intervention patterns;
- operating constraints;
- KPI and economic logic;
- governed workflows;
- evaluation and assurance benchmarks.

The desired signal is not ontology growth. It is increasing industrial competency with decreasing Core disruption.

## Customer operating knowledge

Customer-specific proprietary logic should normally remain in **Customer Profiles** or private Industry IQ extensions rather than leaking into canonical Core.

This preserves two things at once:

1. CEPIO can generalize across enterprises;
2. each enterprise can retain proprietary operating knowledge and decision logic.

## Design principles

### 1. Bind authoritative systems rather than recreate them

Use the rule:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable operating intelligence.**

### 2. Canonical semantics before source schemas

A source field maps into a CEPIO property, relationship, observation, provenance assertion or profile-specific extension. Source-system structure is not copied blindly.

### 3. Evidence before inference

An answer, recommendation or decision should be traceable to evidence available to the actor at that time.

### 4. Time and uncertainty are first-class

CEPIO distinguishes valid time from transaction time and should explicitly represent uncertainty rather than hide it inside model prose.

### 5. Recommendation is not authority

Knowledge, recommendation, decision authority and execution authority are separate concerns.

### 6. Actions are governed

Actions that alter enterprise state require policy, preconditions, idempotency, audit and outcome verification.

### 7. Headless first

CEPIO is headless at its core. UI, copilots and agents are persona-adaptive experiences over the same operating contract.

> **Same industrial reality. Different experience for every decision-maker.**

### 8. Microsoft-native, not Microsoft-dependent

Microsoft Fabric, Foundry, Entra and Azure services are the primary reference ecosystem, but they implement CEPIO capabilities rather than define CEPIO semantics. CEPIO should preserve the same operating contract across alternative industrial data environments such as Cognite and OSDU-based stacks.

## Industry scope

CEPIO is designed first for Energy & Process Industries and shared asset-intensive patterns:

- upstream oil and gas;
- drilling;
- midstream;
- refining;
- petrochemicals and chemicals;
- process manufacturing;
- EPCIC / capital projects;
- shared reliability, maintenance, HSE, workforce, supply and commercial patterns.

The same architectural principles may later extend into mining, power and utilities where shared industrial patterns hold.

## Target users

The primary value is created for engineers, planners and operational leaders whose decisions require context across multiple systems. Platform/data/AI teams are the builders that expose CEPIO through applications and agents. Governance users define the authority and evidence boundaries. AI agents are first-class software consumers operating under those same boundaries.

See [Target Users / Personas](19-Target-Users-Personas.md).

## Competency as product proof

CEPIO should be judged by how much real industrial work it can support through a stable, reusable and governed contract.

```text
Persona
  -> Responsibility
  -> Decision
  -> Competency question
  -> Required capabilities
  -> Evidence / Skill / Function / Decision / Action
  -> PASS / PARTIAL / FAIL / NOT_RUN
```

See [Competency & Assurance](20-Competency-Assurance.md).

## Operating loop

```text
Understand -> Reason -> Decide -> Act -> Learn
```

Expanded:

```text
Observe -> Understand -> Reason -> Decide -> Recommend
        -> Authorize -> Act -> Verify -> Learn
```

## Core value proposition

CEPIO is valuable when it reduces:

- repeated semantic integration;
- application coupling to enterprise systems;
- agent reasoning directly over source schemas;
- duplicated industrial business logic;
- missing evidence/provenance;
- hidden uncertainty;
- unsafe AI-to-action pathways;
- customer-specific contamination of reusable semantics;
- migration risk when data platforms or source systems change.

The objective is not to build the largest industrial ontology. The objective is to build the strongest reusable **Industry IQ** for governed industrial work.
