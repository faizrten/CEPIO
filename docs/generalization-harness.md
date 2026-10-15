# CEPIO Generalization & Competency Harness

## Purpose

The CEPIO Generalization Lab tests whether CEPIO is converging toward a reusable Energy & Process Industry operating abstraction rather than growing through customer-specific vocabulary. Its executable component is the **Competency Harness**.

v0.1 uses a drilling-contractor archetype because it stresses materially different semantics from the refinery reference scenario: mobile fleet assets, wells and campaigns, activity/NPT coding, crew competency, well-control assurance, rig moves, drilling equipment, service contracts and offshore safety.

## Architectural invariant

> Agents discover weaknesses; CEPIO evidence and deterministic validators decide whether the semantic contract passes.

The harness therefore separates four trust zones:

1. **Challenge** — archetype, persona, standards and adversarial agents generate candidate questions.
2. **Execution** — an Operator agent may plan retrieval but is constrained to governed CEPIO tools.
3. **Evidence** — CEPIO objects, relationships, time, provenance, function/policy/action traces form the authoritative evidence bundle.
4. **Assurance** — semantic judging is combined with deterministic structural validation before a result can pass.

v0.1 implements the deterministic ontology-readiness slice first. Live LLM execution is intentionally not a CI dependency.

## v0.1 flow

```text
Drilling-contractor archetype
        +
Personas + external benchmark registry
        |
        v
Frozen competency pack (16 CQs)
        |
        v
OntologyIndex over ontologies/*.ttl
        |
        +-- class/property existence
        +-- subclass compatibility
        +-- object-property domain/range compatibility
        |
        v
PASS / PARTIAL / FAIL + missing semantics
        |
        v
Gap triage: CORE / DOMAIN / PROFILE / MAPPING / REJECT
```

Each run emits a stable hash over the frozen archetype, competency, persona and standards artifacts plus a separate hash of the CEPIO ontology modules. This makes the semantic-readiness result reproducible.

## Why semantic readiness comes first

An LLM can often infer a plausible answer even when the ontology lacks the required relationship. That behavior is useful for exploration but unsafe as an ontology test. v0.1 therefore asks whether a non-LLM consumer could find the required canonical classes and edge contracts before any natural-language answer is judged.

For example, CEPIO can already express an `OperatingRig` working on a `Well`, and a `DrillingCampaign` using that rig. The same baseline currently lacks first-class concepts needed for some deliberate challenge cases such as BOP assurance, IADC-style activity coding and jack-up move readiness. The harness must surface those differences rather than allow a model to fill them in.

## External standards are benchmarks, not canonical authority

The drilling pack uses public reference surfaces from:

- IADC DDR Plus — activity/data acquisition and performance coding;
- IADC KSA — role-based rig personnel competency;
- IADC Drilling Manual — drilling-system/domain coverage taxonomy;
- Energistics WITSML — interoperable well/wellbore and real-time drilling data;
- PPDM — well identity/status and lifecycle vocabulary;
- OSDU — Well, Wellbore, Completion, Well Plan, Well Activity, Materials and Well Equipment domains;
- API RP 54 — drilling and servicing safety/risk context;
- API Standard 53 — well-control/BOP equipment assurance context;
- SPE DSATS — drilling systems advancement, automation and nomenclature.

These references challenge and inform CEPIO. They do not automatically become CEPIO canonical semantics, and copyrighted standards text is not vendored into this repository.

## Agent contracts

`generalization/agents/drilling-v0.1.yaml` defines the future live roles:

- **Test Director** — campaign and frozen-batch control;
- **Challenger** — persona/industry question generation;
- **Competency Curator** — normalization, clustering and prioritization;
- **CEPIO Operator** — CEPIO-only evidence retrieval;
- **Semantic Judge** — answer-to-question fit;
- **Evidence Auditor** — provenance/time/trace support;
- **Gap Classifier** — `CORE / DOMAIN / PROFILE / MAPPING / REJECT` proposal.

No harness agent may autonomously mutate CEPIO Core or merge an ontology change.

## Drilling v0.1 challenge design

The frozen questions intentionally mix expected strengths and hard gaps:

| Area | Why it matters |
|---|---|
| Rig → well → campaign | fundamental drilling identity/context |
| Rig → systems/equipment → work | asset + maintenance portability |
| Failure → downtime/NPT | reliability + drilling performance |
| Daily activity/sub-activity | IADC operational-time vocabulary |
| Crew → certification → competency | workforce readiness |
| Permit → safety case → risk → action | HSE assurance |
| BOP/test/drill evidence | well-control assurance |
| Condition → work → critical spare | reliability/supply chain |
| Downtime → obligation/dayrate/revenue | commercial consequence |
| Rig score with cross-domain context | enterprise graph value |
| Valid time vs transaction time | bitemporal correctness |
| KPI provenance | evidence traceability |
| Campaign move consequence | multi-domain reasoning |
| Jack-up move/preload/punch-through | drilling-contractor specificity |
| Incident → corrective action → readiness | safety-to-operation linkage |
| Supplier → spare → equipment/work | supply-chain traceability |

## Result interpretation

A `PASS` in v0.1 means the ontology contains all declared semantic prerequisites. It does **not** prove that runtime data exists or that a natural-language answer would be correct.

`PARTIAL` is often the most useful result: it shows that CEPIO's common abstractions work but a drilling-domain specialization or relationship is still missing.

Questions with `runtime.temporal`, `runtime.provenance`, `runtime.policy` or `runtime.kinetic` requirements are reported as `NOT_RUN` in v0.1. This prevents ontology readiness from being confused with runtime assurance.

## Intended evolution

- **v0.1** — deterministic ontology semantic readiness, drilling contractor.
- **v0.2** — scenario fixtures and CEPIO runtime evidence bundles.
- **v0.3** — constrained Operator agent using CEPIO REST/MCP only.
- **v0.4** — independent semantic judge + evidence auditor.
- **v0.5** — adversarial/mutation agents and regression campaigns across multiple industry archetypes.

The eventual release gate should measure convergence: new archetypes should require progressively fewer changes to CEPIO Core while competency coverage rises.
