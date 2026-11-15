# CEPIO Current State

## Documentation snapshot — 12 November 2026

Reviewed Core main: `e12a5ee5f6b332b3601642f4e6906ebe146b131d`. This is a repository/documentation review, not a fresh production qualification or scorecard assessment.

| Question | Evidence-backed answer | Authority |
| --- | --- | --- |
| What is the published product? | v0.4 FOUNDATION Developer Preview; its support boundary is unchanged | [Release manifest](../RELEASE.md) |
| What is the next release gate? | v0.5 CONNECT remains open: real three-source context and verified, reconciled writeback | [CONNECT #51](https://github.com/faizrten/CEPIO/issues/51) |
| What is the maturity score? | 69/100 at the governed 20 October baseline; no recalculation in this review | [Scorecard](../config/v1-scorecard.yaml) |
| What has advanced on main? | Bounded inspection/alignment, relationship paging, ACCC host admission, optional Nemotron planning, semantic reconciliation/review lifecycle and OSS dependency admission | Focused references below |
| What is live today? | Not reverified by this documentation change. A merged implementation or passing CI does not identify a deployed image or enabled feature | Exact environment, image/commit, configuration and authenticated acceptance evidence are required |

### Recent capability map

| Capability | Repository evidence | Qualification boundary |
| --- | --- | --- |
| Operational object inspection and alignment | [Inspection](operational-state-inspection-v0.1.md), [alignment](operational-state-alignment-v0.1.md) | Reference/synthetic evidence; no CONNECT closure |
| Bounded relationship access | [Remote qualification](relationship-remote-qualification-v0.1.md) | Offline conformance does not establish production exposure |
| Microsoft-default agent host / ACCC | [Host composition](architecture/accc-harness-readonly-spike.md) | Offline SDK mechanics and admission; no blanket live-model or deployment claim |
| Optional model planner | [Nemotron planner](nemotron-planner.md) | Opt-in binding; live model qualification separate |
| Ontology reinforcement | [Auto-Ontology](integrations/auto-ontology-reinforcement.md) | Retrieval, reconciliation and review-use primitives; live reinforcement and two-arm judgment uplift remain unqualified |
| External dependency resilience | [OSS admission policy](governance/open-source-dependency-resilience.md) | Policy/register/checker are present on this main revision; candidate registration is not production approval |

Public Core remains the source-neutral contract layer. Protected implementations and deployment receipts must be assessed within their own authorized repositories; this page does not publish or infer their readiness.

### How to use this snapshot

Start with the [documentation guide](README.md). Developers can follow the [Developer Preview](developer-preview.md); operators should use [deployment profiles](deployment-profiles.md) and [REST security](rest-security.md). The Wiki explains concepts; focused contracts and accepted ADRs define bounded behavior.

**Open documentation/adoption proof:** independently complete the developer extension journey tracked in [#60](https://github.com/faizrten/CEPIO/issues/60) and the clean-room deployment exercise in [#63](https://github.com/faizrten/CEPIO/issues/63). Navigation reconciliation does not close those gates.

## Historical capability baseline — 20 October 2026

The remainder preserves the earlier baseline and its subsequent dated addenda. Statements about persistence, hosted surfaces and future adapters below describe that historical scope; they must not be used as a fresh deployment inventory. Use the dated snapshot above and the focused evidence for later changes.

**Development increment (11 November 2026):** [Auto-Ontology reinforcement](integrations/auto-ontology-reinforcement.md) adds a host-only semantic-term evidence binding and a two-arm qualification contract. Offline transport checks do not establish live integration, ontology reinforcement or judgement uplift. No release, default runtime, deployment or scorecard change.

**Bounded implementation increment (7 November 2026):** [Nemotron read-only planner](nemotron-planner.md) binds an opt-in model endpoint to the existing Operator protocol. Offline transport/contract validation is separate from live model qualification. No default-model, deployment, release or scorecard change.

**Bounded implementation increment (3 November 2026):** [Host-local relationship paging v0.1](bounded-relationship-query-v0.1.md) adds explicit security bindings, SQL authorization pushdown and bounded SQLite reads. It does not qualify a remote Operational Object endpoint or complete #329; the dated baseline and release/scorecard claims below remain unchanged.

**Strategy reference (26 October 2026):** [CEPIO Product North Star & Strategic Doctrine](strategy/industry-iq-product-north-star.md) establishes the professional companion mission, Industrial Competence Network and sovereignty doctrine. The dated implementation baseline and maturity scores **below retain their own dates**; strategic approval must not be confused with new live qualification or product-release advancement.

**Snapshot date:** 2026-10-20  
**Capability snapshot baseline (pre-reconciliation `main`):** `85d9b6ead10038a74c141799b682b845d49ce24b`

This page is the narrative current-state snapshot for CEPIO. The pinned SHA identifies the implementation/capability baseline reviewed for this documentation pass; merging documentation-only reconciliation commits does not make that capability snapshot stale. It distinguishes three things that must not be conflated:

1. **published product release** — the qualified external product boundary;
2. **repository mainline capability** — merged implementation that may be ahead of the published release;
3. **v1 maturity scorecard** — an independently governed evidence-backed completion model.

## North Star

> **CEPIO is the portable Industrial Operating Intelligence layer for Energy & Process Industries: thin in infrastructure, thick in Industry IQ.**

The product objective is to make reusable industrial operating competence available to humans, applications and AI agents without rebuilding systems of record, data platforms, generic agent runtimes or frontier-model infrastructure.

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

Palantir Ontology remains a useful capability benchmark. It is not CEPIO's product identity.

For the Microsoft reference ecosystem, the operating boundary is:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

Microsoft Foundry, Copilot, Fabric, Entra and Azure supply generic platform capabilities. CEPIO supplies industrial meaning, evidence, competence, Decisions, authority, governed Actions and outcome semantics.

## Product architecture

```text
Authoritative enterprise context
SAP · PI · OSDU · Fabric · Cognite · P6 · MES · engineering systems
                         |
                         v
               Replaceable bindings
                         |
                         v
              Thin CEPIO operating core
 semantics · identity · state · time · evidence · provenance
 uncertainty · policy · authority · Functions · Decisions · Actions
                         |
                         v
                 Thick Industry IQ
 capabilities · Skills · competencies · performance contracts
 failure/risk/decision patterns · constraints · KPI/economic logic
 workflows · assurance/evaluation contracts
                         |
                         v
       Governed intelligence runtime and context plane
 Capability Registry · Memory · Retrieval · Compiled Industry IQ
                         |
                         v
                  Protocol surfaces
 REST /api/v1 · Management /management/v1 · MCP /mcp
                         |
                         v
        Apps · Studio · copilots · agents · workflows
```

The governing architecture rule is:

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

## Product release status

### v0.4 FOUNDATION — Developer Preview

**Qualified.**

The published product release remains CEPIO `0.4.0` Developer Preview. It qualifies the coherent developer/runtime foundation: canonical semantics, temporal state and provenance, Functions, Decisions, governed Actions, `/api/v1`, Entra-aware security boundaries, Microsoft bindings, reference deployment profiles and observability.

The v0.4 release guarantee is intentionally narrower than current `main`.

### v0.5 CONNECT — current release gate

**Open / partial.** GitHub epic #51 remains the authoritative release-gate tracker.

The release question is:

> Can CEPIO operate over real industrial systems while keeping those systems authoritative and complete one governed, verified and reconciled external action?

The release gate still requires one industrial asset using context from at least three source-system domains, explainable provenance for material state, and one authorized/idempotent/verified/reconciled writeback.

The major remaining product proof is live industrial integration, especially SAP + PI and the end-to-end K-201 reliability scenario. Mainline foundations do not qualify the product release by themselves.

## Mainline capabilities ahead of the published v0.4 release

The following capabilities are merged on `main` but must be interpreted according to their own qualification boundaries.

### Industrial operating and execution foundation

- durable workflow definitions/instances, approvals, retries/timeouts/cancellation and supported compensation;
- external Action lifecycle, verification/reconciliation and immutable `WorkflowOutcome`;
- contextual policy, exact policy-version pinning and trusted evaluation lineage;
- Skill Registry, runtime binding, READY preflight and READY-only host dispatch;
- Application Contract / protocol convergence across REST, SDK and MCP;
- governed uncertainty, confidence, information-gain and Opportunity/Option semantics.

### Binding and platform portability

- provider-neutral Binding Contract v0.1;
- Fabric/Fabric IQ bindings and a Fabric live-proof transport path;
- source-neutral evidence and governed-action boundaries;
- OSDU-first subsurface extension boundary;
- retired Azure AI Search integration (ADR-0039); PostgreSQL is preferred for next memory/retrieval adapter; SQLite remains the current mainline repository.

Live SAP/PI and the full three-source CONNECT release gate remain unqualified.

### Industry IQ control plane

- Industry IQ Pack Registry;
- Capability Registry and governed Compounding Industrial Intelligence;
- trusted catalogue and pack provenance;
- supply-chain attestation/SBOM/security policy for external packs;
- domain onboarding and reusable capability-promotion controls;
- protected/customer-specific knowledge boundaries that prevent tenant knowledge from silently becoming global Industry IQ.

### Memory, retrieval and acceleration

- durable Semantic / Procedural / Episodic / Profile memory contracts;
- bounded per-task Context Assembly;
- capability-routed Retrieval & Indexing;
- structured and lexical reference backends plus replaceable vector/graph slots;
- PostgreSQL-backed memory/retrieval adapter remains a future milestone behind the same source-neutral contracts;
- deterministic Compiled Industry IQ bundles and bounded hot-cache acceleration;
- hard exclusion of PROFILE/customer context from the shared compiled cache.

Core invariant:

> **Industry IQ may compound continuously; working model context remains bounded, governed and tenant-safe.**

### Enterprise performance intelligence

- Performance Contract and Performance Runtime;
- specialization through organization, role/persona and individual layers;
- sparse patches/suppressions with fail-closed dependency validation;
- objectives, KRs, KPIs, guardrails, accountability and contribution relationships;
- recommend-only bridge from performance deviation to governed workflows;
- reusable Refinery and Drilling Contractor Industry Performance Reference Packs.

Reference packs contain organization-neutral operating hypotheses. Customer formulas, targets, thresholds, organization structures and source bindings remain customer specialization.

### Management and protocol productization

The hosted CEPIO runtime now has three deliberately separated surfaces:

```text
/api/v1/*          Application Contract / REST
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

The Management surface remains observation-only. It does not create remote mutation/administration authority.

The hosted MCP gateway exposes the governed CEPIO MCP contract behind authenticated actor mapping and does not allow callers or models to self-assert CEPIO roles.

### Microsoft-native industrial agency

The current architecture decision is:

> **Microsoft owns agent execution. CEPIO owns industrial agency.**

The Reliability Agent Lighthouse defines a G0-G7 proof sequence spanning Foundry-hosted agent execution, CEPIO MCP, protected Industry IQ, Fabric/event triggering, human approval, governed SAP action, scenario/eval qualification and provider portability.

A Foundry Reliability G1 qualification path is implemented, including a least-privilege tool profile. Repository implementation does **not** by itself claim a successful live G1 environment run.

## Current interfaces

The hosted target composition is:

| Surface | Purpose | Authority model |
| --- | --- | --- |
| `/api/v1/*` | application/runtime contract | authenticated CEPIO application policy |
| `/management/v1/*` | runtime capability/health projection | authenticated read-only management role |
| `/mcp` | AI/agent protocol projection | authenticated host-injected actor + normal CEPIO policy |

Protocol surfaces project shared CEPIO contracts; they must not invent independent industrial semantics.

## Target users

The initial center of gravity remains:

- industrial engineers, planners and operational leaders making cross-system decisions;
- digital/data/AI teams building applications and agents for them;
- platform/integration teams binding authoritative systems;
- governance/technical-authority users defining evidence and execution boundaries;
- AI agents as first-class software consumers operating under authenticated policy and authority.

CEPIO is headless at its core:

> **Same industrial reality. Different experience for every decision-maker.**

## Competency and assurance

Competency is a product-quality measure, not an ontology-size metric.

```text
Persona
 -> Responsibility
 -> Decision
 -> Competency question
 -> Required capability/evidence
 -> Skill / Function / Decision / Action
 -> Assurance result
```

The maturity model spans semantic, runtime, procedural/Skill, agent and operational competency. Generalization asks whether capability remains reusable; assurance asks whether a claim/action is justified.

## v1.0 maturity scorecard

The canonical scorecard currently remains **69/100 (69%)**, pinned to the governed evidence snapshot documented in `docs/v1-completion-scorecard.md` and `config/v1-scorecard.yaml`.

That score is **not automatically recalculated when new PRs merge**. Mainline work after the scorecard snapshot may create evidence drift. A governed scorecard update must validate whether new evidence earns points before the canonical score changes.

The scorecard and product roadmap are deliberately separate:

- **roadmap:** what release proof must be completed next;
- **scorecard:** how much total v1 maturity is already evidenced.

## Roadmap taxonomy

Canonical product capability labels:

| Release | Capability label | Proof |
| --- | --- | --- |
| v0.4 | **FOUNDATION** | developers can build against a coherent CEPIO contract |
| v0.5 | **CONNECT** | CEPIO can operate over authoritative industrial truth |
| v0.6 | **EXECUTE** | CEPIO can produce governed, verified industrial outcomes |
| v0.7 | **EXTEND** | independent teams can add Industry IQ safely |
| v0.8 | **OPERATE** | an enterprise can depend on CEPIO operationally |
| v0.9 | **GENERALIZE** | CEPIO is portable across enterprises/platform contexts |
| v1.0 | **GUARANTEE** | stable production contracts and explicit guarantees |

These labels are product-release taxonomy, not component-version names.

## Known open proofs

The main outstanding product proofs include:

- live SAP S/4HANA integration qualification;
- live AVEVA PI/historian qualification;
- three-source K-201 CONNECT lighthouse;
- verified live external writeback/read-back/reconciliation;
- real hosted Foundry G1 evidence for the intended Reliability Skill;
- production distributed persistence/worker/queue qualification;
- HA, SLO, DR and penetration/security qualification;
- second real enterprise portability/adoption proof;
- v1 compatibility/deprecation/support guarantees.

## Documentation authority

Use these layers together:

1. implementation contracts, code, ontologies, mappings, tests and accepted ADRs are authoritative for behavior;
2. this page is the current narrative snapshot;
3. `docs/roadmap.md` is authoritative for product-release gates;
4. `config/v1-scorecard.yaml` is authoritative for the numeric v1 maturity score;
5. `docs/wiki/` is the reader-oriented narrative/navigation layer;
6. `RELEASE.md` is authoritative for the published v0.4 release boundary.

Historical benchmark documents remain historical evidence and should not be rewritten merely to match the current product vocabulary.

### OSDU read foundation (development only)

An optional exact-version OSDU Storage reader now provides a tested transport
prerequisite for Wellbore/RAFS evidence. It is not registered with the hosted
runtime. DDMS bulk-data hydration, actor-aware host composition and authorized
live qualification remain open. See [scope and acceptance](osdu-read-foundation.md).
