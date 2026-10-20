# ICC Persona Qualification v0.1

## Purpose

ICC Persona Qualification adds a persona-scoped qualification layer on top of CEPIO Domain Onboarding. The canonical domain benchmark remains frozen and source-system-neutral. A persona binding selects the competency questions and runtime evidence that the persona actually consumes.

This prevents CEPIO from creating persona-specific ontologies while still proving that an Industrial Capability Contract (ICC) can support a specific industrial role.

## Contract shape

A reference Domain Onboarding manifest may declare an optional `persona_id`:

```yaml
id: drilling-contractor-reference-domain-onboarding-v0.1
version: "0.1"
domain: drilling-contractor
persona_id: rig-manager
artifacts:
  archetype: generalization/archetypes/drilling-contractor-v0.1.yaml
  personas: generalization/personas/drilling-contractor-v0.3.yaml
  standards: generalization/standards/drilling-references.yaml
  competency: generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml
  runtime_suite: generalization/runtime/drilling-contractor-runtime-coverage-v0.5.yaml
```

`persona_id` is consumed by the ICC qualification layer. Domain Onboarding itself remains domain-scoped and backward-compatible with manifests that do not declare a persona.

## Qualification flow

1. Run the governed Domain Onboarding workflow against the explicit manifest.
2. Resolve the requested persona from the manifest or CLI override.
3. Select only frozen competency questions whose `personas` include that persona.
4. Recalculate semantic pass rate for that persona scope.
5. Recalculate deterministic runtime evidence coverage for the same question set.
6. Fail closed if semantic, critical-failure or runtime thresholds are not met.
7. Emit an ICC delta report and qualification provenance.
8. Stop at human Generalization Review. Qualification never auto-releases a domain or persona binding.

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

A zero-gap result is meaningful: it demonstrates reuse of the canonical ICC without adding persona-specific canonical semantics.

## Customer boundary

Persona qualification does not infer customer-specific implementation details. The report deliberately leaves the following as customer-binding requirements:

- source mappings;
- customer KPI/OKR bindings;
- local policy and decision rights; and
- system adapters and governed writeback.

Customer data therefore binds a qualified capability to a customer environment; it does not redefine the canonical industry model.

## Provenance

Every report records hashes for the manifest, workflow, policy, archetype, persona pack, standards registry, frozen competency pack, runtime suite, ontology baseline and persona scope. It also records the execution timestamp and runtime suite identity when available.

This makes qualification reproducible and allows Industry IQ Studio to compare successive ICC qualification runs.

## Fail-closed behavior

The v0.1 qualifier blocks when:

- no persona is specified;
- the persona is absent from the scoped persona pack;
- the persona has no questions in the frozen competency pack;
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
- competency pack: `drilling-contractor-persona-capabilities-v0.3`
- runtime suite: `drilling-contractor-runtime-coverage-v0.5`

The next recommended validation is a materially different persona in the same domain, such as `maintenance-planner` or `reliability-engineer`, to prove that multiple personas can project different capability subsets from the same canonical ICC.
