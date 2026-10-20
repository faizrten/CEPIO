# ADR-0036: Persona-Scoped ICC Qualification and Fail-Closed Onboarding Targets v0.1

- Status: Accepted
- Date: 2026-10-20
- Classification: PUBLIC architecture/governance contract

## Context

The first governed Domain Onboarding run for the Drilling Contractor domain exposed two control-plane weaknesses.

First, a pull-request-triggered Domain Onboarding workflow could silently fall back to the Refinery reference manifest because `workflow_dispatch` inputs are not populated for `pull_request` events. A green workflow could therefore qualify the wrong domain. This is unacceptable for qualification evidence because the evidence target must be explicit and reproducible.

Second, selecting a persona directly from the frozen competency pack's `personas` annotations produced a technically correct but incomplete Rig Manager projection: only two of fourteen frozen questions were directly tagged to `rig-manager`. Those annotations identify primary answering roles; they do not necessarily define the full operating view a senior industrial persona must consume. Treating direct tags as complete persona coverage would create false confidence.

The canonical Drilling Contractor benchmark must remain frozen and source-neutral. Persona-specific coverage must not be solved by creating persona-specific ontology concepts or by mutating the benchmark after qualification.

## Decision

### 1. Require an explicit onboarding target

Domain Onboarding must never select an implicit default domain in CI.

- Manual workflow dispatch requires an explicit repository-relative domain manifest.
- Pull-request-triggered onboarding resolves exactly one changed `generalization/domain-packs/*.yaml` manifest.
- Zero or multiple changed domain-pack manifests fail closed.
- The developer CLI requires `--manifest` explicitly.

This makes the qualification target auditable and prevents green evidence for the wrong domain.

### 2. Introduce Persona Capability Binding as a governed projection

A Persona Capability Binding is a separate contract over an existing frozen domain competency pack. It defines which frozen questions a persona must consume and in what mode:

- `primary`: directly accountable operating capability;
- `oversight`: capability requiring management visibility/accountability without displacing another role's authority;
- `support`: contextual capability needed for integrated decisions.

The binding validates domain, persona, frozen competency-pack identity, duplicate/unknown question references, and a minimum role-coverage threshold.

The first reference binding is `drilling-contractor-rig-manager-binding-v0.1`, covering all 14 frozen Drilling Contractor persona-capability questions while preserving the frozen benchmark unchanged.

### 3. Qualify persona semantics and runtime evidence separately from the canonical domain

Persona-scoped ICC qualification runs on top of the existing governed Domain Onboarding result. It recalculates semantic and deterministic runtime coverage only for the questions selected by the Persona Capability Binding.

Qualification fails closed on missing/invalid persona bindings, missing persona coverage, parent-domain failure, semantic threshold failure, semantic errors, critical failures, or incomplete runtime evidence.

Successful automation still terminates at `GENERALIZATION_REVIEW`. No persona, domain, capability, or release approval is inferred from CI.

### 4. Emit ICC delta and provenance as first-class evidence

Every persona qualification report records:

- required questions and capabilities;
- reused capability patterns;
- missing capabilities;
- new semantic candidates;
- runtime gaps;
- semantic policy/authority gaps;
- customer-binding requirements; and
- hashes for the manifest, workflow, policy, archetype, persona pack, persona binding, standards, frozen competency pack, runtime suite, ontology baseline, and persona scope.

This makes a zero-gap result meaningful only when the persona coverage contract itself is adequate and reproducible.

### 5. Preserve the customer boundary

Persona qualification does not infer customer-specific source mappings, KPI/OKR definitions, local decision rights, adapters, or writeback behavior. These remain explicit customer-binding requirements.

Customer data may bind a qualified capability to a customer environment; it must not redefine the canonical industry model or become implicit training/generalization evidence.

## Consequences

### Positive

- PR qualification cannot silently target the wrong domain.
- Persona coverage is explicit, reviewable, versioned, and testable.
- Frozen domain benchmarks remain stable while persona views can evolve independently.
- Senior roles can consume capabilities across functional boundaries without creating role-specific canonical ontologies.
- ICC qualification produces auditable delta and provenance evidence suitable for Industry IQ Studio.
- Negative tests prove the qualification contract fails closed.

### Costs / constraints

- Persona bindings become an additional governed artifact to maintain.
- Protected workflow changes require high-risk governance review and ADR evidence.
- A persona's binding must be reviewed for role adequacy; 100% qualification is not meaningful if the binding is too narrow.
- Customer activation still requires source mappings, KPI/OKR bindings, local policy/authority, and system integration evidence.

## Validation

The Rig Manager reference binding is qualified against the frozen Drilling Contractor v0.3 persona-capability benchmark and v0.5 deterministic runtime-evidence suite.

Observed evidence before this ADR was finalized:

- 14/14 frozen competency questions in the explicit Rig Manager binding;
- 32/32 required capability instances reused;
- 100% persona semantic qualification;
- 100% persona runtime evidence coverage;
- zero missing capabilities;
- zero new semantic candidates;
- zero runtime gaps;
- zero semantic policy/authority gaps.

Negative tests cover malformed bindings, domain/persona/pack mismatch, duplicate and unknown questions, insufficient role coverage, missing persona, fallback selection, known persona with zero benchmark questions, parent-domain blocking, semantic gaps/errors, and runtime failures.

The CEPIO quality policy must remain unchanged. The implementation is required to meet the repository's changed-line coverage and no-new-coverage-debt gates rather than weakening them.

## Alternatives considered

### Mutate the frozen competency pack to tag Rig Manager on every relevant question

Rejected. This conflates reusable domain capability ownership with persona consumption and would modify the benchmark merely to satisfy a presentation/role concern.

### Create a Rig Manager ontology/profile

Rejected. The role should project existing industrial capabilities; it should not introduce persona-specific canonical semantics.

### Continue using direct competency `personas` tags only

Rejected for production qualification. The first run proved that direct tags can be too narrow for senior-role operating coverage. They remain an explicit fallback for backward compatibility and exploratory use.

### Keep a default Refinery manifest in GitHub Actions

Rejected. Qualification evidence must be target-explicit and fail closed when ambiguous.
