# Drilling Contractor Domain Qualification — v0.4

## Purpose

The drilling-contractor competency program has moved from semantic coverage to domain qualification. The v0.3 persona-capability pack and v0.5 runtime suite proved that CEPIO can answer the current 14-question operating capability contract deterministically. This v0.4 challenge deliberately widens the scope again before any ontology remediation.

The benchmark asks whether CEPIO can support a drilling contractor as an enterprise operating abstraction across executive economics, operational optimization and governed agentic work.

## Qualification principles

1. Freeze the challenge before remediation.
2. Ask operating questions, not ontology questions.
3. Prefer capability contracts over one literal ontology path.
4. Preserve operator, drilling-contractor and service-company accountability boundaries.
5. Treat model output as inference unless enterprise evidence supports it.
6. Represent authority, responsibility, time, provenance and action governance explicitly.
7. Do not add vocabulary merely to obtain a passing score.
8. Classify every exposed gap as `CORE`, `DOMAIN`, `PROFILE`, `MAPPING` or `REJECT` before implementation.

## Persona expansion

Persona pack `drilling-contractor-v0.3` is additive to v0.2 and introduces seven qualification personas:

- Chief Executive Officer / President
- Chief Operating Officer
- Chief Financial Officer
- VP / Director Drilling Operations
- Drilling Performance / Optimization Engineer
- Contract Manager
- Digital / Data / AI Leader

The previous 24 personas remain unchanged in scope.

## Three challenge bands

### Band A — Enterprise competency

Questions `DC-DQ-001` through `DC-DQ-005` test whether CEPIO can support enterprise decisions rather than only rig-level operations:

- risk-adjusted fleet and customer economics;
- recurring fleet loss and enterprise intervention;
- downtime-to-cash and margin scenarios;
- contract renewal / repricing / renegotiation decisions;
- capital allocation across reliability, utilization and contract value.

### Band B — Operational optimization competency

Questions `DC-DQ-006` through `DC-DQ-010` test whether CEPIO can move from descriptive visibility to optimization:

- invisible lost time;
- drilling-parameter / dysfunction association;
- lessons learned and recurrence prevention;
- predictive NPT risk and preventive action;
- normalized cross-rig and cross-crew benchmarking.

Qualification must avoid false comparability: wells, sections, rigs, crews and campaigns must be compared only under explicit operating context.

### Band C — Agentic operating competency

Questions `DC-DQ-011` through `DC-DQ-015` test whether CEPIO can act as the governed semantic substrate for agents:

- evidence-grounded BOP readiness recommendation;
- critical-spare / procurement intervention;
- contract and claims evidence chain;
- governed operating-plan deviation;
- measurable value realization without violating safety, authority or audit constraints.

The agentic band does not require autonomous execution. It requires CEPIO to distinguish recommendation, authorization, execution and evidence, and to fail closed where authority or evidence is absent.

## Qualification stages

### Stage 1 — Semantic qualification

Run the frozen v0.4 pack against the current ontology. A PARTIAL or FAIL result is expected and is evidence of useful pressure, not a reason to mutate the benchmark.

Deliverables:

- deterministic PASS / PARTIAL / FAIL result;
- semantic check coverage;
- capability-level matched and missing patterns;
- gap ledger classified by architecture disposition.

### Stage 2 — Semantic remediation

Implement only accepted `CORE` and `DOMAIN` semantics. Use `PROFILE` for customer-specific structure, `MAPPING` for external standards/codes and `REJECT` where a requested literal would weaken the ontology.

The frozen v0.4 pack must not change during remediation.

### Stage 3 — Runtime qualification

For each qualified capability, create deterministic runtime evidence that proves CEPIO can materialize and retrieve the required context. Runtime evidence must include temporal state and provenance where relevant.

### Stage 4 — Operational assurance

Prove fail-closed behavior for:

- unsupported enterprise facts;
- expired or missing authority;
- actions requiring human approval;
- stale operating context;
- missing provenance;
- safety or policy constraints.

### Stage 5 — Customer qualification

Validate with real customer-shaped data and workflows while keeping customer vocabulary outside the canonical ontology unless cross-customer evidence justifies promotion.

Recommended reference validation set:

- ARO Drilling — primary Saudi drilling-contractor profile;
- Nabors — automation and drilling-performance stress case;
- ADNOC Drilling — integrated drilling-services / fleet economics stress case;
- Valaris or Shelf Drilling — offshore fleet and contract-portfolio stress case.

Customer qualification is not complete until at least two materially different contractors can answer the same canonical competency questions with customer-specific mappings only.

## Exit criteria for Drilling Contractor Qualified v1

CEPIO should not claim a qualified drilling-contractor domain solely because the ontology contains drilling nouns. Qualification requires:

1. all frozen competency questions classified and architecture-reviewed;
2. accepted semantic capabilities passing deterministically;
3. runtime evidence for all qualified capabilities;
4. temporal and provenance evidence for material operational and financial claims;
5. authority and responsibility resolution for governed actions;
6. agentic workflows fail closed when evidence or permission is missing;
7. cross-customer validation demonstrates canonical reuse without profile leakage;
8. regression tests preserve the benchmark and prior capability contracts.

## Immediate next step

Run the frozen v0.4 pack against current `main`, capture the baseline score, and produce `drilling-contractor-domain-qualification-v0.4` gap triage before proposing ontology changes.
