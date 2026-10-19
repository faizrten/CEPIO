# ADR-0017 — Petrophysics v1 Mainline Promotion

- Status: Accepted
- Date: 2026-10-18
- Scope: Subsurface ontology, Petrophysics runtime, role policy, qualification fixtures

## Context

CEPIO Petrophysics v1 was developed as a depth-first persona milestone across PET-01 through PET-08. The qualified implementation originally accumulated on a historical stacked branch chain. Since the Core epistemic primitives, Kinetic opportunity semantics and OSDU/ADME Subsurface boundary have subsequently been promoted to `main`, carrying the historical stack forward would reintroduce obsolete ancestry and risk overwriting newer governance/runtime work.

The clean promotion changes protected paths:

- `ontologies/subsurface.ttl`
- `ontology-modules.yaml`
- `policies/policies.yaml`

Governance therefore requires an explicit architectural decision and validation record.

## Decision

Promote Petrophysics v1 as a clean, additive mainline delta on current `main`.

1. Add the experimental `subsurface` ontology module at version `0.2.0`.
2. Keep Core as the owner of Evidence, Claim, Hypothesis, Assumption, Assessment, Uncertainty, Confidence, InformationGain and Dependency semantics.
3. Keep Kinetic as the owner of Opportunity, Option, OptionRecommendation and Decision semantics.
4. Add only thin Petrophysics/Subsurface assurance concepts needed to express governed formation-evaluation and cross-discipline reasoning; do not replicate OSDU technical payloads.
5. Add a `petrophysicist` policy role with read/reason/recommend scope only. It receives no action, function or decision authority.
6. Preserve all newer current-main policy capabilities, contextual-policy behavior, workflow governance and package exports when promoting the Petrophysics runtime.
7. Keep public benchmarks synthetic and explicitly non-empirical; customer/operator data is not included.

## Architectural invariants

The promotion must preserve:

- **OSDU-first / extension-not-replication**: WellLog, RAFS and reservoir-model payloads remain in their governed technical systems.
- **Source identity**: external record IDs and versions remain provenance-bearing references.
- **Authority separation**: AI/runtime may analyze and recommend but may not declare an interpretation authoritative, approve reserves, overwrite external records or approve investment decisions.
- **Core stability**: no Petrophysics concept is promoted into Core solely because one persona uses it.
- **Policy continuity**: existing gates and current-main roles/capabilities remain effective.
- **No customer-data training dependency**: qualification uses CEPIO-authored synthetic fixtures and deterministic runtime tests.

## Consequences

Positive:

- Petrophysics becomes a first-class but bounded Subsurface domain capability on current mainline.
- The eight Petrophysics journeys share one semantic/runtime spine rather than separate workflow silos.
- The clean promotion avoids inheriting obsolete commits from the historical branch stack.
- The result is ready for provider-neutral evidence binding without coupling the ontology to Fabric, OSDU or another source implementation.

Trade-offs:

- `subsurface` remains experimental while more persona and provider evidence accumulates.
- Live source integration is deliberately outside this promotion and must satisfy the same semantic/authority contracts.

## Validation

The promotion is accepted only when:

- the full CEPIO pytest suite passes;
- ontology compatibility checks pass;
- public API and client contract checks pass;
- drilling and refinery regression/qualification harnesses remain green;
- package and container smoke tests pass;
- Petrophysics PET-01 through PET-08 qualification remains answered with no blocked journey in the synthetic reference portfolio;
- governance metadata and protected-path checks pass.

The clean promotion branch was created directly from the current `main` baseline rather than by merging the historical Petrophysics stack.
