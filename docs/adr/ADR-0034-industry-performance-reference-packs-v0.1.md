# ADR-0034: Industry Performance Reference Packs v0.1

- Status: Accepted
- Date: 2026-10-20
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0030 Performance Contract Specialization v0.2

## Context

CEPIO now has a governed Enterprise Performance Graph and deterministic specialization from industry reference through organization, role/persona and individual. The missing product layer is reusable industrial performance knowledge: the objectives, KPI identities, driver relationships, guardrails and role-accountability patterns that are common enough to accelerate a new deployment without pretending every organization calculates or governs them identically.

The repository already makes two important architectural commitments:

1. KPI identities such as availability and energy intensity reuse generic KPI semantics rather than creating one ontology class per KPI.
2. Formula, convention, denominator, normalization, target and organization policy remain external/contextual and must preserve provenance.

The existing Industry IQ Pack Registry solves a different problem: executable domain intelligence and its runtime dependencies. A performance reference library must not become a second executable pack system.

## Decision

### 1. Treat an Industry Performance Pack as a complete industry-reference Performance Contract

CEPIO does not introduce a new contract primitive for performance packs.

A built-in Industry Performance Pack is a normal:

```text
PerformanceContract(layer="industry_reference")
```

with a stable contract ID and semantic version. It is directly valid, organization-neutral reference intelligence and is registered/resolved using the existing Performance Contract machinery.

v0.1 seeds two packs:

```text
cepio.performance.refinery.reference@0.1.0
cepio.performance.drilling-contractor.reference@0.1.0
```

### 2. Standardize performance grammar, not customer policy

Reference packs may contain:

- objectives;
- KPI/metric/guardrail identities;
- generic units where useful;
- explanatory definitions;
- structural driver/contribution relationships;
- reference personas/roles; and
- reference accountability patterns.

Reference packs MUST NOT assert organization-specific:

- formula references;
- numeric targets;
- thresholds;
- customer-specific fiscal or reporting conventions;
- workflow response bindings; or
- customer identities.

This keeps reference intelligence reusable while preserving the rule that an organization owns the meaning and policy of its business.

### 3. Organization adoption is explicit specialization

An organization opts into a reference pack through `PerformanceContractOverlayV2`.

The organization can then:

- patch a KPI formula, target, threshold, definition or scope;
- bind the KPI to local subjects/roles;
- suppress reference accountabilities that do not fit the local operating model;
- add organization-specific KPIs, KRs and guardrails; and
- add governed response bindings only where the organization chooses.

The effective contract remains the deterministic merge of reference semantics plus explicit organization specialization. There is no name-based or inferred customer mapping.

### 4. Reference accountability is a starting hypothesis, not personnel truth

Reference persona accountability captures common operating-model patterns so Industry IQ can reason about likely ownership and contribution structure before a customer-specific operating model is bound.

It does not create individual accountability, personnel scoring or HR performance policy. Organizations are expected to suppress/rebind reference accountabilities where their governance differs.

### 5. Preserve causality discipline

Reference contribution edges distinguish structural contribution from contextual influence.

For example, drilling `Invisible Lost Time -> NPT ratio` is modeled as `influences`, not `contributes_to`, because an organization's activity taxonomy determines whether time is formally classified as NPT. This prevents the reference graph from asserting a stronger causal/accounting claim than the organization has established.

### 6. Keep execution authority outside the packs

Reference packs have no workflow response bindings and no Action capability.

After organization specialization, any response binding still flows through the existing Performance Service, Industry IQ reasoning, governed Decision and Workflow Policy/Kinetic boundaries.

## Initial refinery pack

The refinery/process-manufacturing pack spans:

- safe/resilient/profitable operations objective;
- operating margin;
- operational availability;
- production throughput and production loss;
- energy intensity;
- product specification conformance;
- unplanned downtime and repeat equipment failures;
- process-safety and environmental guardrails; and
- reference accountability across plant, operations, reliability, process, energy, quality, safety, environmental, finance and production-assurance personas.

The pack reuses the repository's established availability and energy-intensity design: KPI identity is canonical; calculation convention remains external.

## Initial drilling-contractor pack

The drilling-contractor pack spans:

- safe/resilient/value-delivery objective;
- contract margin;
- fleet utilization;
- operational uptime;
- NPT ratio and duration;
- dayrate realization;
- backlog coverage;
- maintenance downtime;
- invisible lost time;
- revenue leakage;
- serious-safety and well-control guardrails; and
- reference accountability across CEO, COO, CFO, drilling operations, rig management, drilling supervision, reliability, performance, commercial, HSE and well-control personas.

Rig Readiness is intentionally not represented as a synthetic percentage KPI. The existing Drilling Rig Readiness Industry IQ capability remains the authoritative deterministic categorical assessment.

## Consequences

### Positive

- New organizations can start from industrial performance knowledge instead of a blank graph.
- Customer KPI formulas/targets remain tenant-owned rather than leaking into global reference semantics.
- Industry reference, organization, persona and individual layers now form one coherent performance inheritance model.
- Industry IQ can traverse from business outcomes into operational drivers with explicit provenance.
- Refinery and drilling prove the pattern across continuous-process and service/fleet operating models.
- No duplicate pack registry or ontology vocabulary is introduced.

### Trade-offs

- Reference accountabilities require customer review rather than blind adoption.
- Some metrics cannot be normalized across companies without additional organization-specific semantic equivalence rules.
- Reference driver edges are qualitative structure, not quantitative causal-effect models.
- v0.1 is deliberately selective rather than an exhaustive industry KPI catalogue.

## Deferred

- petrochemical, upstream, midstream, mining, power and EPC/EPCIC performance packs;
- automated extraction of customer KPI definitions from BI/ERP/historian assets;
- KPI comparability/normalization contracts across organizations;
- quantitative causal weights and learned driver models;
- Studio authoring UX for selecting and specializing reference packs;
- automatic mapping from persona catalog entries into organization directory identities.

## Validation

Focused tests require:

- both built-in packs to remain organization-neutral industry-reference contracts;
- no universal formula/target/threshold or response binding in reference nodes;
- expected KPI, metric, guardrail and persona coverage;
- refinery organization specialization of availability without copying the graph;
- explicit suppression/rebinding of reference accountability;
- drilling organization specialization of NPT policy without graph duplication; and
- stable pack lookup by Performance Contract identity.
