# CEPIO Generalization Lab

The Generalization Lab is CEPIO's semantic proving ground. The **Competency Harness** challenges the ontology using reference enterprises, personas, industry standards and frozen competency questions.

## v0.1 — drilling contractor

v0.1 answers one narrow question:

> Does the current CEPIO ontology contain the semantic prerequisites needed to express important drilling-contractor questions?

It does **not** claim that CEPIO can already answer every question end-to-end. Temporal/provenance evidence execution, live LLM challengers/judges and customer-source mappings are later harness stages.

Run:

```bash
PYTHONPATH=src python scripts/run_generalization_harness.py
```

Write the evidence report:

```bash
PYTHONPATH=src python scripts/run_generalization_harness.py --json-out /tmp/cepio-drilling-harness.json
```

`--fail-on-critical-gap` is intentionally opt-in while v0.1 is being used to discover gaps.

## Artifact set

```text
archetypes/drilling-contractor-v0.1.yaml
personas/drilling-contractor-v0.1.yaml
agents/drilling-v0.1.yaml
competency/drilling-contractor-v0.1.yaml
standards/drilling-references.yaml
gaps/drilling-contractor-v0.1.yaml
```

The competency pack is the frozen challenge. The accepted gap-triage artifact is deliberately separate: it records the architectural response to the current result and has its own stable hash.

## Trust rule

LLMs may generate hypotheses, scenarios, questions and interpretations. An LLM-generated statement is never treated as CEPIO-supported enterprise evidence by itself. A future Operator agent must use governed CEPIO tools only and return `INSUFFICIENT_CEPIO_EVIDENCE` when CEPIO cannot support the answer.

## Frozen drilling pack

The initial pack contains 16 competencies spanning:

- rig / well / campaign identity;
- rig systems, drilling equipment and maintenance;
- NPT and downtime;
- IADC-style daily drilling activity semantics;
- crew certification and competency;
- permits, risk and corrective actions;
- BOP / well-control assurance;
- condition, work and critical spares;
- contract, dayrate and revenue exposure;
- fleet score / cross-domain exception context;
- bitemporal state and provenance;
- campaign-move readiness;
- jack-up move / preload / punch-through risk;
- HSE readiness;
- supplier-to-spare-to-work traceability.

The pack is frozen before evaluation. Its stable SHA-256 batch hash is emitted on every run together with an ontology hash, so results can be tied to an exact test contract and semantic baseline.

## External benchmark sources

`standards/drilling-references.yaml` records the public reference surfaces used to challenge CEPIO: IADC DDR Plus, IADC KSA, IADC Drilling Manual, IADC Model Contracts and jack-up guidance, Energistics WITSML, PPDM Well Status, OSDU data definitions, API RP 54 / Standard 53 / RP 2JU and SPE DSATS. The repository stores reference metadata and intended use, not copyrighted standards text.

## Result semantics

- `PASS` — all required ontology terms and edge contracts are present.
- `PARTIAL` — some semantic prerequisites are present, but at least one is absent or incompatible.
- `FAIL` — none of the required semantic prerequisites are present.
- `ERROR` — the competency contains no deterministic semantic checks.

Runtime requirements such as temporal evidence or property provenance are marked `NOT_RUN` in v0.1. They are visible so future harness versions can promote them into executable assurance checks without changing the question's identity.

## Gap-classification contract

A failed competency is evidence of a **gap**, not permission to add a class. Every current missing semantic must be assigned exactly one accepted disposition:

```text
CORE     reusable common CEPIO semantics
DOMAIN   drilling-domain canonical specialization
PROFILE  customer/fleet/deployment-specific extension
MAPPING  external taxonomy/source vocabulary to federate rather than copy
REJECT   exact proposed semantic is the wrong abstraction
```

A `REJECT` decision may name a `replacement_layer`. This is used when the competency exposes a real need but the literal missing term would model it badly, for example a drilling-only scalar where a reusable commercial rate object is the correct abstraction.

The runner validates that triage covers every current `PARTIAL/FAIL` missing semantic exactly once and contains no stale entries. An ontology change that resolves a gap must therefore update the triage artifact in the same change.

Harness agents may propose changes; they may not autonomously mutate canonical CEPIO Core.

See `docs/generalization-harness.md` for the accepted drilling decisions and architectural rationale.
