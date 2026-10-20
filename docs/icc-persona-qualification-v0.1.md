# ICC Persona Qualification v0.1

## Purpose

ICC Persona Qualification adds a persona-scoped qualification layer on top of CEPIO Domain Onboarding. The canonical domain benchmark remains frozen and source-system-neutral. A persona binding selects the competency questions and runtime evidence that the persona actually consumes.

This prevents CEPIO from creating persona-specific ontologies while still proving that an Industrial Capability Contract (ICC) can support a specific industrial role.

## Contract shape

A reference Domain Onboarding manifest may declare `persona_id` plus an explicit `persona_binding` artifact:

```yaml
id: drilling-contractor-reference-domain-onboarding-v0.1
version: "0.1"
domain: drilling-contractor
persona_id: rig-manager
persona_binding: generalization/persona-bindings/drilling-contractor-rig-manager-v0.1.yaml
artifacts:
  archetype: generalization/archetypes/drilling-contractor-v0.1.yaml
  personas: generalization/personas/drilling-contractor-v0.3.yaml
  standards: generalization/standards/drilling-references.yaml
  competency: generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml
  runtime_suite: generalization/runtime/drilling-contractor-runtime-coverage-v0.5.yaml
```

The binding itself is an auditable projection over the frozen competency pack:

```yaml
id: drilling-contractor-rig-manager-binding-v0.1
version: "0.1"
domain: drilling-contractor
persona_id: rig-manager
competency_pack_id: drilling-contractor-persona-capabilities-v0.3
minimum_question_count: 14
questions:
  - question_id: DC-PC-002
    mode: primary
    rationale: Rig Manager requires current drilling activity and deviation awareness.
  - question_id: DC-PC-001
    mode: oversight
    rationale: Rig Manager must understand offshore command boundaries without displacing OIM authority.
```

`primary`, `oversight` and `support` describe how the persona consumes an existing domain capability. They do not create new canonical semantics.

If no explicit binding is declared, the qualifier falls back to competency-pack `personas` annotations. The explicit binding is preferred for production qualification because direct persona annotations often describe the primary answering role rather than the full operating view required by a senior industrial persona.

Domain Onboarding itself remains domain-scoped and backward-compatible with manifests that do not declare a persona.

## Qualification flow

1. Run the governed Domain Onboarding workflow against the explicit manifest.
2. Resolve the requested persona from the manifest or CLI override.
3. Resolve and validate the explicit Persona Capability Binding when present.
4. Select the bound frozen competency questions without modifying the frozen competency pack.
5. Recalculate semantic pass rate for that persona scope.
6. Recalculate deterministic runtime evidence coverage for the same question set.
7. Fail closed if semantic, critical-failure or runtime thresholds are not met.
8. Emit an ICC delta report and qualification provenance.
9. Stop at human Generalization Review. Qualification never auto-releases a domain or persona binding.

## Why explicit persona binding matters

The first direct Rig Manager projection exposed an important distinction: the frozen Drilling Contractor competency pack directly tagged `rig-manager` on only two questions, even though the Rig Manager role requires integrated awareness across safe operations, current execution, well-control readiness, maintenance, workforce, rig move, commercial exposure and supply constraints.

A 100% score over two questions was technically valid but not sufficient evidence of role coverage. The explicit binding therefore adds a minimum coverage contract and maps the Rig Manager across all 14 frozen Drilling Contractor capability questions while preserving the original benchmark unchanged.

This separates two concerns cleanly:

- the frozen competency pack defines reusable domain capability questions; and
- the Persona Capability Binding defines which of those capabilities a role must consume and in what mode.

## ICC delta

The persona qualification report makes onboarding learning explicit:

- required questions;
- required capabilities;
- reused capabilities and matched semantic patterns;
- missing capabilities;
- new semantic candidates caused by current gaps;
- runtime gaps;
- semantic authority/accountability gaps; and
- customer-binding requirements still required before customer activation.

A zero-gap result is meaningful only when the persona coverage contract is itself adequate. `minimum_question_count` gives the binding a deterministic lower bound; the reviewed question list defines the actual role coverage.

## Customer boundary

Persona qualification does not infer customer-specific implementation details. The report deliberately leaves the following as customer-binding requirements:

- source mappings;
- customer KPI/OKR bindings;
- local policy and decision rights; and
- system adapters and governed writeback.

Customer data therefore binds a qualified capability to a customer environment; it does not redefine the canonical industry model.

## Provenance

Every report records hashes for the manifest, workflow, policy, archetype, persona pack, Persona Capability Binding, standards registry, frozen competency pack, runtime suite, ontology baseline and persona scope. It also records the execution timestamp and runtime suite identity when available.

This makes qualification reproducible and allows Industry IQ Studio to compare successive ICC qualification runs.

## Fail-closed behavior

The v0.1 qualifier blocks when:

- no persona is specified;
- the persona is absent from the scoped persona pack;
- an explicit Persona Capability Binding is invalid, mismatched, duplicated, under its minimum coverage, or references unknown questions;
- the persona has no questions in the frozen competency pack when fallback selection is used;
- parent Domain Onboarding is blocked;
- persona semantic pass rate falls below policy;
- persona critical failures exceed policy;
- semantic qualification contains errors; or
- persona runtime evidence coverage is incomplete or failed.

Regression tests deliberately inject semantic and runtime failures to prove that these gates reject unsupported persona qualification.

## GitHub Actions target selection

PR-triggered Domain Onboarding no longer falls back to an implicit Refinery manifest. The workflow requires exactly one changed `generalization/domain-packs/*.yaml` manifest and uses that manifest as the onboarding target. Manual runs require an explicit `manifest` input.

This avoids a green workflow for the wrong domain and makes the evidence target unambiguous.

## Current reference

The first persona-scoped reference is:

- domain: `drilling-contractor`
- persona: `rig-manager`
- Persona Capability Binding: `drilling-contractor-rig-manager-binding-v0.1`
- competency pack: `drilling-contractor-persona-capabilities-v0.3`
- runtime suite: `drilling-contractor-runtime-coverage-v0.5`
- binding coverage: all 14 frozen competency questions

The next recommended validation is a materially different persona in the same domain, such as `maintenance-planner` or `reliability-engineer`, to prove that multiple personas can project different capability subsets from the same canonical ICC.
