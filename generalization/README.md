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

## v0.2 — broader drilling personas

The v0.2 persona pack expands the challenge from management-level drilling semantics to frontline execution, operator/customer interfaces, service companies, crewing, finance, marine and procurement roles. It remains a **literal prerequisite benchmark**: every term and relationship named by the frozen pack is checked exactly.

That behavior is useful for discovery, but an exact-path benchmark can continue to report a gap after CEPIO deliberately chooses a stronger abstraction. For example, CEPIO rejects direct `CrewMember -> WorkOrder` responsibility in favor of a time-scoped `ResponsibilityAssignment`.

The accepted gap-triage and resolution ledgers preserve those decisions rather than weakening the frozen v0.2 questions.

## v0.3 — capability-based semantic composition

v0.3 adds a second deterministic evaluation contract. A competency may declare business capabilities, and each capability may define one or more **approved semantic patterns**. The capability passes when at least one complete pattern is supported by the CEPIO ontology.

```text
Business question
      ↓
Capability requirement
      ↓
Approved semantic alternatives
      ↓
Ontology term / edge validation
      ↓
PASS when any complete alternative is valid
```

This allows CEPIO to receive coverage credit for stronger composed semantics without adding weak convenience predicates solely to satisfy a test. Examples include:

- `CrewMember -> CrewAssignment -> Activity` instead of direct person-to-activity assignment;
- `ResponsibilityAssignment -> WorkItem` instead of direct person-to-work responsibility;
- `Activity -> measuredBy -> DrillingFluidObservation` instead of a drilling-only inverse observation edge;
- `JackUpMove -> dependsOn -> MarineSupportAsset` instead of a special-purpose marine support predicate;
- common `ServiceExecution / ServiceDeliveryEvidence / ServiceAcceptance` semantics instead of drilling-specific service-delivery classes;
- common `PlanDeviation` plus authority and impact semantics instead of `drill:ProgramDeviation`.

Legacy v0.1/v0.2 packs remain backward compatible and continue to execute as literal prerequisite contracts.

Run the capability contract:

```bash
PYTHONPATH=src python scripts/run_generalization_harness.py \
  --competency generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml \
  --personas generalization/personas/drilling-contractor-v0.2.yaml \
  --skip-gap-triage \
  --fail-on-critical-gap
```

### Coverage semantics

A v0.3 semantic capability score answers:

> Does CEPIO provide at least one architecturally accepted semantic composition for each tested business capability?

It does **not** mean the capability has been proven against live enterprise data. Semantic capability coverage must remain separate from later assurance gates:

```text
Semantic capability coverage
        +
Runtime answerability
        +
Temporal correctness
        +
Provenance completeness
        +
Policy / authority evidence
        =
Operational coverage
```

Therefore, even a 100% score on a frozen semantic capability pack is not a production-readiness claim. Generative/adversarial questions and runtime evidence tests must continue to challenge the model.

## Artifact set

```text
archetypes/drilling-contractor-v0.1.yaml
personas/drilling-contractor-v0.1.yaml
personas/drilling-contractor-v0.2.yaml
agents/drilling-v0.1.yaml
competency/drilling-contractor-v0.1.yaml
competency/drilling-contractor-persona-expansion-v0.2.yaml
competency/drilling-contractor-persona-capabilities-v0.3.yaml
standards/drilling-references.yaml
gaps/drilling-contractor-v0.1.yaml
gaps/drilling-contractor-persona-v0.2.yaml
```

The competency pack is the frozen challenge. Accepted gap-triage artifacts are deliberately separate: they record architectural responses to literal benchmark results and have their own stable hashes.

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

- `PASS` — all required literal checks or all declared capability requirements pass.
- `PARTIAL` — some required checks/capabilities pass, but at least one does not.
- `FAIL` — none of the required checks/capabilities pass.
- `ERROR` — the competency contains no deterministic semantic checks.

Runtime requirements such as temporal evidence or property provenance remain separate from semantic readiness and are promoted into executable assurance checks without changing the question's identity.

## Gap-classification contract

A failed competency is evidence of a **gap**, not permission to add a class. Every current missing semantic in a literal pack must be assigned exactly one accepted disposition:

```text
CORE     reusable common CEPIO semantics
DOMAIN   drilling-domain canonical specialization
PROFILE  customer/fleet/deployment-specific extension
MAPPING  external taxonomy/source vocabulary to federate rather than copy
REJECT   exact proposed semantic is the wrong abstraction
```

A `REJECT` decision may name a `replacement_layer`. This is used when the competency exposes a real need but the literal missing term would model it badly.

The runner validates that triage covers every current `PARTIAL/FAIL` missing semantic exactly once and contains no stale entries. An ontology change that resolves a gap must therefore update the triage artifact in the same change.

Harness agents may propose changes; they may not autonomously mutate canonical CEPIO Core.

See `docs/generalization-harness.md` for the accepted drilling decisions and architectural rationale.
