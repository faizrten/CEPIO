# CEPIO Execution Roadmap

See [Version naming and delivery status](version-naming.md) for product, component, Lab and API version scopes.

## North Star

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**
>
> Frontier models provide general intelligence. CEPIO provides reusable industrial operating competence — semantics, evidence requirements, Skills, decision patterns, authority, actions and evaluation — so that capable models can operate consistently against real enterprise context across platforms such as Microsoft Fabric, Cognite and OSDU.

The governing design rule is:

> **Thin infrastructure. Thick industrial intelligence.**

CEPIO should not rebuild data platforms, knowledge-graph engines, generic agent frameworks, generic LLM reasoning, broad ingestion infrastructure or thick application shells when mature platforms already provide those capabilities well.

CEPIO should concentrate differentiated effort where industrial know-how compounds:

- canonical industrial operating semantics;
- identity across enterprise representations;
- state, time, evidence and provenance contracts;
- Skills and industrial procedures;
- decision and authority semantics;
- governed action contracts;
- failure/risk/KPI/economic patterns;
- domain competency and operating patterns;
- cross-domain generalization;
- model/platform evaluation and assurance.

The strategic architecture is:

```text
                   FRONTIER MODELS / AGENTS
                            |
                            v
                 CEPIO INDUSTRY IQ
        Skills · Competencies · Decision Patterns
        Failure/Risk Models · Constraints · KPIs
        Reference Workflows · Evaluation Benchmarks
                            |
                            v
                     CEPIO CORE
         Identity · Semantics · State · Time · Evidence
          Provenance · Decision · Authority · Action
                            |
            +---------------+---------------+
            |               |               |
            v               v               v
          Fabric          Cognite          OSDU
            |               |               |
            +------- Enterprise Reality ----+
```

CEPIO remains headless. Experience surfaces, agent hosts and data/runtime platforms are replaceable consumers or implementations of the CEPIO contract.

---

# Product structure

CEPIO is now developed as four complementary product layers.

## 1. CEPIO Core — thin, stable, public

Core defines the minimum portable industrial operating contract:

- Object / identity;
- Relationship;
- Observation / Event / State;
- valid time + transaction time;
- Evidence + Provenance;
- Function;
- Decision;
- Authority / Policy;
- Action;
- Outcome;
- Skill capability contract.

Core is not intended to become a comprehensive copy of every industrial standard or source schema.

## 2. CEPIO Industry IQ — thick, differentiated, protected by default

Industry IQ is where product differentiation accumulates:

- industrial Skills;
- persona competencies;
- evidence requirements;
- failure and risk patterns;
- constraints and operating envelopes;
- KPI/economic relationships;
- decision patterns;
- action-selection logic;
- reference workflows;
- domain packs;
- benchmark and evaluation corpora.

Detailed Industry IQ evolves primarily in `CEPIO-Labs`; deliberate contracts, abstractions and sanitized examples may be extracted to public CEPIO.

## 3. CEPIO Platform Bindings — native, replaceable

Bindings make the same CEPIO operating contract usable over existing platforms without making those platforms canonical CEPIO semantics.

Priority bindings:

- Microsoft Fabric / Fabric IQ / RTI / Foundry;
- Cognite Data Fusion Data Modeling / CogniteCore / Process Industries / Atlas;
- OSDU / Azure Data Manager for Energy;
- source-authoritative action bindings such as SAP where required.

Platform-native identifiers, storage models and query mechanics stay inside bindings.

## 4. CEPIO Assurance + Generalization — protected capability factory

Generalization Lab and assurance assets determine whether CEPIO capability is reusable and whether models/platforms conform to the operating contract.

They cover:

- competency questions;
- scenario and benchmark corpora;
- model evaluation;
- Skill trigger/evidence/authority tests;
- cross-domain reuse evidence;
- semantic promotion evidence;
- platform-conformance tests;
- model/provider ablation;
- portability scoring.

---

# What has already been built and remains valuable

The v0.1–v0.4 work remains the durable foundation rather than being discarded.

## Completed — v0.1 Semantic Scaffold

- modular CEPIO ontology architecture;
- industrial objects/relationships/events/functions;
- initial policy/action semantics;
- reference refinery scenario.

## Completed — v0.2 Operational Kernel

- persistent repository abstractions;
- optimistic concurrency and idempotency;
- policy engine;
- typed Functions;
- Decisions and governed Actions;
- audit;
- SDK/MCP foundations;
- SHACL and ontology validation.

## Completed — v0.3 Temporal + Provenance Kernel

- property-level provenance;
- valid time + transaction time;
- object and relationship history;
- deterministic event -> state reconstruction;
- explainable evidence lineage.

## Completed — v0.4 Developer Preview / Microsoft binding

- stable `/api/v1` route contract;
- Python + TypeScript client foundations;
- Entra identity boundary;
- Fabric/Fabric IQ binding;
- Foundry/MCP binding;
- App Service / AKS reference profiles;
- observability;
- compatibility and release qualification.

## Foundations pulled forward after v0.4

Important capabilities already on `main` should be retained but reframed as supporting contracts rather than the primary moat:

- durable workflow orchestration and `WorkflowOutcome`;
- contextual policy and exact policy-version lineage;
- evidence / uncertainty / confidence / information-gain semantics;
- Skill registry binding, actor-aware preflight and READY-only dispatch;
- recommendation-before-act boundaries;
- governed external execution, verification and reconciliation;
- OSDU-first subsurface boundary;
- drilling portability qualification;
- two BOUND protected Skills: equipment degradation and maintenance deferral;
- governance, compatibility and security qualification.

CEPIO-Labs already contains the beginnings of the new strategic moat:

- protected Skill library and runtime-binding experiments;
- Generalization Lab benchmarks/evaluation;
- industry workspaces for drilling, refinery, petrochemical, upstream and EPCIC;
- protected Agent Challenge v0.2 frontier-model qualification;
- protected decision/function/reasoning/optimization workspaces.

---

# What changes now

The previous roadmap over-weighted CEPIO-owned infrastructure and source-by-source integration.

The following work is no longer a strategic objective by itself:

- building a proprietary graph/database platform;
- building a general-purpose agent framework;
- building a proprietary frontier-model reasoning engine;
- building direct read adapters for every enterprise source system;
- making SAP + PI + P6 + OSDU connectors prerequisites for product progress;
- building a thick CEPIO-only UI platform;
- treating generic graph analytics as product differentiation;
- expanding canonical ontology solely for vocabulary coverage;
- enterprise HA/control-plane engineering before a real deployment requires it.

These capabilities may remain useful as reference/conformance infrastructure, but they do not define CEPIO's product advantage.

The new prioritization test is:

> **Does this work increase CEPIO's portable industrial operating competence, or are we rebuilding infrastructure that Fabric, Cognite, OSDU or frontier models already provide better?**

If the latter, prefer a binding, reuse or conformance layer instead.

---

# Current — v0.5 Platform-Native Integration + Portability Proof

**Objective:** prove that CEPIO can operate natively over existing enterprise/industrial data planes without duplicating them, while preserving one portable operating contract.

This replaces the old connector-first v0.5 emphasis.

## P0 — Fabric-first observation plane

Use Fabric as the default Microsoft enterprise data plane where the required data/freshness already exists.

Prove:

- Fabric / OneLake / RTI -> CEPIO canonical object/state/evidence;
- original source identity and provenance survive the Fabric hop;
- CEPIO does not require SAP/PI-specific read integration when Fabric already provides sufficient context;
- the same CEPIO query/Skill can consume Fabric-backed enterprise context.

## P0 — Cognite-native binding proof

Build a bounded Cognite DMS/CogniteCore binding experiment around one compressor/reliability scenario.

Prove:

- CEPIO can operate over the native Cognite graph without copying that graph into a separate CEPIO store;
- Cognite `space`, `externalId`, views/containers and query mechanics remain binding concerns;
- CEPIO Core requires no Cognite-specific canonical concepts;
- CDF evidence remains traceable through CEPIO Evidence/Provenance;
- the same CEPIO Skill operates unchanged over Cognite-backed and Fabric-backed contexts.

## P0 — Provider-neutral industrial data contract

Define the minimal provider contract needed by CEPIO Industry IQ, conceptually covering:

`resolve -> relationships -> observations -> events/history -> evidence -> changes`

Provider implementations may use Fabric, Cognite, the CEPIO reference runtime or another compatible data plane.

## P0 — Cross-platform identity

Prove one industrial identity across representations, for example:

```text
CEPIO Asset/K-101
  <-> Fabric asset key
  <-> Cognite space/externalId
  <-> authoritative source identity
```

Ambiguity must fail closed.

## P1 — Source-authoritative action plane

Direct source integration remains necessary where the system of record owns business action semantics.

First proof: governed SAP maintenance action/writeback.

Required properties:

- CEPIO Decision -> Authority -> Action;
- idempotent execution;
- SAP-side business validation;
- read-back verification;
- reconciliation;
- Outcome + audit lineage.

PI/P6/other direct read connectors are optional unless the platform-native data plane cannot satisfy freshness/fidelity requirements.

## v0.5 release gate

One bounded industrial scenario must demonstrate all of the following:

1. the same canonical CEPIO object identity resolves across Fabric and Cognite representations;
2. one CEPIO Skill runs unchanged over both platform-backed contexts;
3. CEPIO Core changes required solely for either platform = **0**;
4. duplicated authoritative Cognite/Fabric graph persisted by CEPIO = **0** (temporary cache/reference runtime excluded);
5. material recommendations remain evidence-traceable to platform/source records;
6. at least one source-authoritative external Action is authorized, idempotent, verified and reconciled.

**v0.5 product claim:** CEPIO is a portable industrial operating contract over existing data platforms, not another industrial data platform.

---

# v0.6 — Industry IQ v1

**Objective:** prove that CEPIO's differentiated value is reusable industrial operating competence rather than infrastructure.

The first Industry IQ release should prioritize depth over domain count.

## Initial Industry IQ packs

### Reliability / Maintenance

Build around capabilities already proven by the Skill work:

- investigate equipment degradation;
- assess maintenance deferral;
- failure investigation;
- bad-actor analysis;
- maintenance prioritization;
- production/economic exposure;
- intervention recommendation;
- work-order/action handoff.

### Drilling

Use the existing drilling semantic/runtime baseline as the second materially different domain:

- investigate NPT;
- invisible lost-time analysis;
- rig performance assurance;
- maintenance/availability exposure;
- operational assurance;
- governed escalation/recommendation.

A third pack such as Refinery or Subsurface/Petrophysics may progress in parallel, but it is not required to prove the v0.6 product claim.

## Industry IQ artifact model

Each mature capability should define where applicable:

- trigger/intention;
- required CEPIO semantics;
- required evidence;
- industrial procedure / Skill;
- Functions/tools;
- relevant failure/risk/constraint patterns;
- Decision schema;
- authority boundary;
- recommendable/executable Actions;
- Outcome expectations;
- benchmark scenarios;
- failure/insufficient-evidence behavior.

## Model-agnostic execution

Industry IQ must not be tied to a single frontier model or agent host.

Prove at least two frontier-model/provider configurations can execute the same CEPIO Skill/tool/evidence contract without changing the industrial capability definition.

## v0.6 release gate

- at least **10 high-value Industry IQ capabilities** across Reliability/Maintenance and Drilling;
- at least **5 capabilities** executable end-to-end through CEPIO Skills/Decisions/Authority contracts;
- no domain-specific capability may self-authorize external execution;
- every material recommendation has an evidence requirement and fail-closed path;
- same capability definition runs over at least two model/provider configurations;
- platform-specific implementation remains below the CEPIO operating contract.

**v0.6 product claim:** CEPIO packages reusable industrial operating competence that frontier models can execute safely against enterprise context.

---

# v0.7 — Generalization + Industrial Assurance

**Objective:** turn CEPIO from a library of good industrial capabilities into a measurable system for proving capability quality, reuse and portability.

## Generalization Lab

Formalize the promotion process:

`PROFILE -> DOMAIN -> CORE`

Promotion requires evidence across materially different operating contexts. Only reusable abstractions/capability patterns move upward; customer data, thresholds, procedures and proprietary operating logic do not.

## CEPIO Assurance

Build protected qualification around:

- unseen industrial scenario corpora;
- Skill trigger/no-trigger quality;
- evidence completeness;
- authority violations;
- unsupported/fabricated evidence detection;
- decision quality;
- action safety;
- model-provider comparison;
- Fabric vs Cognite platform-ablation;
- cross-domain reuse metrics.

The existing protected Agent Challenge v0.2 becomes one seed for this capability.

## v0.7 release gate

- protected assurance corpus spans at least Reliability/Maintenance + Drilling;
- same Industry IQ capabilities are evaluated across at least two frontier models;
- same capability is evaluated over Fabric-backed and Cognite-backed contexts;
- measured results distinguish model quality from platform-binding quality;
- at least one reusable capability is promoted based on documented Generalization Lab evidence rather than author intuition.

**v0.7 product claim:** CEPIO can measure whether a model/platform combination possesses the required industrial operating competence.

---

# v0.8 — Enterprise Profiles + Native Deployment

**Objective:** prove that CEPIO Industry IQ can be specialized for a real enterprise without forking CEPIO Core or copying the enterprise's platform estate.

Priority work:

- PROFILE packaging;
- customer-specific mappings;
- authority/policy binding;
- enterprise Skills/procedures;
- platform-native deployment pattern;
- private/customer-owned benchmark scenarios;
- governed action integration;
- operations/security requirements driven by the real deployment.

Infrastructure hardening is demand-driven at this stage. Build HA, queues, workers, DR and control-plane components only where the selected enterprise deployment requires CEPIO-owned runtime state that cannot be delegated safely to the host platform.

## v0.8 release gate

One enterprise profile demonstrates:

- no customer IP promoted into shared CEPIO Core;
- most data context is consumed through native platform bindings;
- customer-specific operating logic remains PROFILE/customer-boundary;
- CEPIO Industry IQ can be specialized without forking shared capabilities;
- governed external actions and audit work in the deployed environment;
- operational/SLO/security evidence matches the actual deployment architecture.

**v0.8 product claim:** CEPIO can become enterprise-specific while preserving a common portable industrial intelligence layer.

---

# v0.9 — Multi-Enterprise Portability

**Objective:** prove portability in real enterprises rather than only synthetic/generalization tests.

Use two materially different enterprise operating contexts and ideally different platform combinations.

Measure:

- CEPIO Core changes required;
- Industry IQ capability reuse;
- Skill reuse;
- Decision/action contract reuse;
- PROFILE-specific additions;
- platform-binding reuse;
- benchmark portability;
- impact on enterprise #1 when enterprise #2 is added.

## v0.9 release gate

- enterprise #2 is implemented primarily through bindings, PROFILE specialization and Industry IQ composition;
- enterprise #1 remains stable;
- CEPIO Core changes required for enterprise #2 are zero or supported by independent Generalization Lab evidence;
- at least one capability is reused across both enterprises and at least two materially different platform contexts.

**v0.9 product claim:** CEPIO Industry IQ is portable across enterprises, platforms and frontier-model providers.

---

# v1.0 — Production Industry IQ

**Objective:** establish explicit production guarantees for the CEPIO contract, Industry IQ packs, bindings and assurance model.

v1.0 is not a promise that CEPIO has become a full-stack data/agent/application platform.

Required guarantees:

## Core contract

- versioned semantic contracts;
- explicit migrations/deprecation;
- stable evidence/decision/authority/action semantics;
- compatibility tests.

## Industry IQ

- versioned capability/Skill contracts;
- domain-pack release discipline;
- documented evidence/authority requirements;
- protected evaluation baselines;
- reproducible quality/assurance evidence.

## Platform bindings

- production-qualified Fabric binding;
- production-qualified Cognite binding or equivalent second platform;
- OSDU boundary where relevant;
- source-authoritative action binding for at least one enterprise system;
- no platform-specific semantics leaking into Core.

## Model independence

- at least two frontier model/provider configurations qualified against the same CEPIO assurance corpus;
- model substitution does not require rewriting Industry IQ capability definitions.

## Enterprise adoption

- at least two materially different enterprise profiles/deployments;
- customer #2 does not destabilize customer #1;
- clean-room implementation can consume CEPIO Core + one Industry IQ pack + one platform binding from published/provided contracts.

## Security / operations

Operational guarantees apply to CEPIO-owned runtime components only. Where state/execution is delegated to Fabric, Cognite or another host platform, CEPIO documents and validates the boundary rather than rebuilding equivalent infrastructure.

**v1.0 product claim:** CEPIO is a production-qualified portable Industrial Operating Intelligence layer for Energy & Process Industries.

---

# Program view

| Release | Product claim | Primary proof |
| --- | --- | --- |
| v0.4 | Developer Preview foundation | Core/API/security/Microsoft binding qualified |
| **v0.5** | Platform-independent operating contract | Same Skill over Fabric + Cognite; source-authoritative action proof |
| **v0.6** | Industry IQ v1 | Reusable Reliability + Drilling capabilities |
| **v0.7** | Industrial assurance | Model/platform benchmark + Generalization evidence |
| **v0.8** | Enterprise specialization | Real PROFILE + native deployment |
| **v0.9** | Multi-enterprise portability | Two materially different real enterprise contexts |
| **v1.0** | Production Industry IQ | Stable contract, packs, bindings and assurance guarantees |

---

# Immediate execution order

## NOW — strategy transition

1. Treat v0.1-v0.4 and pulled-forward runtime work as completed foundation/reference infrastructure.
2. Stop making source-by-source read adapters the v0.5 critical path.
3. Preserve SAP writeback/reconciliation as the first authoritative-action proof.
4. Make Fabric the default Microsoft observation/data plane.
5. Start Cognite DMS native-binding hypothesis in CEPIO-Labs.
6. Define provider-neutral identity/query/evidence contract from the Fabric + Cognite comparison.
7. Continue protected Skills work as the seed of CEPIO Industry IQ.
8. Continue protected Agent Challenge/evaluation work as the seed of CEPIO Assurance.

## NEXT — Industry IQ depth

9. Consolidate Reliability/Maintenance capabilities into the first coherent Industry IQ pack.
10. Use Drilling as the second materially different pack and generalization pressure test.
11. Keep Refinery/Petrochemical/Subsurface work focused on reusable operating capability rather than ontology breadth alone.
12. Evaluate frontier models as replaceable reasoning engines through the same CEPIO capability/evidence contracts.

## DEFER unless demanded by a proof/deployment

- broad direct PI/P6 read-adapter work;
- proprietary graph/database scaling;
- general-purpose agent-framework work;
- CEPIO-specific thick UI/platform shell;
- generic graph-analytics expansion;
- production HA/queue/control-plane work not required by a real enterprise deployment.

---

# Governing product tests

Every material roadmap item should now answer at least one of these questions:

1. **Industrial intelligence:** does this encode reusable industrial operating competence?
2. **Portability:** does this make the competence independent of model/platform/vendor?
3. **Grounding:** does this improve identity, state, evidence or provenance?
4. **Governance:** does this strengthen Decision, Authority, Action or Outcome control?
5. **Generalization:** does this prove what belongs in PROFILE, DOMAIN or CORE?
6. **Assurance:** can we measure whether the capability works and fails safely?

If the primary answer is instead "this recreates infrastructure already provided by a host platform," prefer reuse or a thin binding.
