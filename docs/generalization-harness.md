# CEPIO Generalization & Competency Harness

## Purpose

The CEPIO Generalization Lab tests whether CEPIO is converging toward a reusable Energy & Process Industry operating abstraction rather than growing through customer-specific vocabulary. Its executable component is the **Competency Harness**.

The first archetype is a generic drilling contractor because it stresses semantics that differ materially from the refinery reference scenario: mobile rigs, wells and campaigns, activity/NPT coding, crew competency, well-control assurance, rig moves, drilling equipment, service contracts and offshore safety.

## Architectural invariant

> Agents discover weaknesses; CEPIO evidence and deterministic validators decide whether the semantic contract passes.

The harness separates four trust zones:

1. **Challenge** — archetype, persona, standards and adversarial agents generate candidate questions.
2. **Execution** — an Operator agent may plan retrieval but is constrained to governed CEPIO tools.
3. **Evidence** — CEPIO objects, relationships, time, provenance, function/policy/action traces form the authoritative evidence bundle.
4. **Assurance** — semantic judging is combined with deterministic structural validation before a result can pass.

Harness v0.1 implements deterministic ontology readiness first. Live LLM execution is intentionally not a CI dependency.

## Frozen challenge flow

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
Accepted gap triage
CORE / DOMAIN / PROFILE / MAPPING / REJECT
```

Each run emits a stable hash over the frozen archetype, competency, persona and standards artifacts plus a separate ontology hash. Accepted current gap triage has its own hash. This keeps the challenge, ontology state and architecture response independently reproducible.

## Why semantic readiness comes first

An LLM can often infer a plausible answer even when the ontology lacks the required relationship. That behavior is useful for exploration but unsafe as an ontology test. The deterministic harness asks whether a non-LLM consumer can find the required canonical classes and edge contracts before any natural-language answer is judged.

The frozen competency pack is therefore not rewritten when CEPIO improves. Remediation must change the ontology/mapping architecture and then prove improvement against the same challenge.

## Drilling domain qualification v0.4

The frozen [drilling domain qualification](drilling-domain-qualification-v0.4.md) adds an additive v0.3 persona expansion and nine operating-language questions across enterprise, operational optimization, and agentic operations. Its accepted initial CORE gaps are preserved in a separate triage artifact, and focused tests pin the question-pack fingerprint and baseline semantic pressure. No ontology remediation is bundled with the benchmark.

Run the qualification with its accepted triage:

```bash
PYTHONPATH=src python scripts/run_generalization_harness.py \
  --competency generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml \
  --personas generalization/personas/drilling-contractor-persona-expansion-v0.3.yaml \
  --gaps generalization/gaps/drilling-contractor-domain-qualification-v0.4.yaml \
  --json-out /tmp/drilling-domain-qualification-v0.4-report.json
```

The domain qualification version is independent of CEPIO product release numbering. Runtime requirements attached to agentic questions remain `NOT_RUN` by this semantic harness and must be validated by runtime coverage.

## External standards are benchmarks, not canonical authority

The drilling campaign uses public/reference surfaces from:

- IADC DDR Plus — drilling activity, sub-activity, equipment and performance coding;
- IADC KSA — role-based rig personnel competency;
- IADC Drilling Manual — drilling-system/domain coverage taxonomy;
- IADC Model Contracts — daywork/day-rate and drilling-contract structures;
- IADC jack-up guidance — rig-move, preload and punch-through-risk framing;
- Energistics WITSML — drilling reports, activities, wells/wellbores and real-time information;
- PPDM — well identity/status and lifecycle vocabulary;
- OSDU — Well, Wellbore, Completion, Well Plan, Well Activity, Materials and Well Equipment domains;
- API RP 54 — drilling and servicing safety/risk context;
- API Standard 53 — well-control/BOP equipment assurance context;
- API RP 2JU — site-specific jack-up assessment context;
- SPE DSATS — drilling systems advancement, automation and nomenclature.

These references challenge and inform CEPIO. They do not automatically become canonical CEPIO semantics, and copyrighted standards content is not vendored into the repository.

## Agent contracts

`generalization/agents/drilling-v0.1.yaml` defines future live roles:

- **Test Director** — campaign and frozen-batch control;
- **Challenger** — persona/industry question generation;
- **Competency Curator** — normalization, clustering and prioritization;
- **CEPIO Operator** — CEPIO-only evidence retrieval;
- **Semantic Judge** — answer-to-question fit;
- **Evidence Auditor** — provenance/time/trace support;
- **Gap Classifier** — `CORE / DOMAIN / PROFILE / MAPPING / REJECT` proposal.

No harness agent may autonomously mutate canonical CEPIO semantics or merge an ontology change.

## Drilling v0.1 challenge

The frozen 16 questions mix expected strengths and hard gaps:

| Area | Why it matters |
|---|---|
| Rig → well → campaign | fundamental drilling identity/context |
| Rig → systems/equipment → work | asset + maintenance portability |
| Failure → downtime/NPT | reliability + drilling performance |
| Daily activity/sub-activity | operational-time vocabulary and federation |
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

## Baseline v0.1 result and accepted triage

The initial ontology baseline scored **9 PASS / 7 PARTIAL** and **84.7%** of deterministic semantic checks.

The original gaps were classified before remediation rather than copied literally into the ontology. Key decisions included:

- reject `NonProductiveTimeEvent`; derive NPT from activity/productivity classification and causal downtime/failure;
- add source-neutral drilling report/activity semantics but keep IADC/WITSML activity codes in federation/mapping;
- add reusable workforce competency requirements while rejecting certificate = competence equivalence;
- add BOP/well-control assurance as drilling-domain semantics;
- reject a new `drill:dayRate`; use common commercial rate semantics;
- reject stored `CampaignReadinessConstraint`; derive readiness through governed reasoning;
- add jack-up move/preload/punch-through semantics as source-neutral drilling-domain concepts.

The baseline decisions that have since been implemented are preserved in `generalization/gaps/drilling-contractor-v0.1-resolutions.yaml`. Only currently unresolved gaps remain in the executable triage file.

## Harness v0.2 semantic remediation

The first remediation cycle is documented in [Drilling Harness Semantic Remediation v0.2](drilling-semantic-remediation-v0.2.md).

It adds:

- drilling report and activity-interval semantics;
- a canonical classification hook plus IADC/WITSML federation contract;
- reusable workforce competency requirements and evidence/assessment links;
- well-control equipment/system/test semantics;
- jack-up rig-move, preload and punch-through-risk semantics;
- reusable commercial `ContractRate` / `RateBasis` semantics while retaining existing `comm:dayRate` compatibility.

The frozen v0.1 question pack remains unchanged. The regression contract is **11 PASS / 5 PARTIAL** and **94.6%** semantic checks. The remaining PARTIAL results are intentional `MAPPING` or `REJECT` decisions, not unowned semantic debt.

## Executable triage invariant

When a gap-triage artifact is supplied, the harness requires:

1. the artifact to be explicitly `accepted`;
2. every referenced question and standard to exist;
3. every current `PARTIAL` or `FAIL` missing semantic to have exactly one triage decision;
4. no duplicate triage coverage;
5. no stale triage entry for a semantic the current ontology now satisfies.

This means a remediation that resolves a gap must update the triage artifact in the same change. Silent semantic drift fails the harness.

## Result interpretation

A `PASS` means the ontology contains all declared semantic prerequisites. It does **not** prove that runtime data exists or that a natural-language answer is correct.

A `PARTIAL` can be the correct architectural result. For example, a frozen question may name an external codeset literally while CEPIO deliberately implements a canonical classification abstraction plus a federation mapping.

Questions with `runtime.temporal`, `runtime.provenance`, `runtime.policy` or `runtime.kinetic` requirements remain `NOT_RUN` in the ontology-readiness slice. This prevents semantic readiness from being confused with runtime assurance.

## Intended evolution

- **Harness v0.1** — frozen drilling-contractor semantic-readiness benchmark + accepted gap classification.
- **Harness v0.2** — minimal accepted semantic remediation, then deterministic scenario fixtures/evidence bundles.
- **Harness v0.3** — constrained Operator agent using CEPIO REST/MCP only.
- **Harness v0.4** — independent semantic judge + evidence auditor.
- **Harness v0.5** — adversarial/mutation campaigns across multiple industry archetypes.

The long-term convergence metric is not “100% literal benchmark vocabulary.” It is rising competency coverage across new archetypes with progressively fewer changes to CEPIO common semantics and fewer customer-specific exceptions.
