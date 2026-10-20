# ADR-0030: Performance Contract Specialization v0.2

- Status: Proposed
- Date: 2026-10-20
- Owners: CEPIO Architecture
- Related: ADR-0021 Enterprise Performance Graph v0.1, ADR-0022 Performance Contract Specialization v0.1, ADR-0023 Performance Contract Registry v0.1

## Context

ADR-0022 established explicit specialization across:

```text
industry_reference -> organization -> role/persona -> individual
```

The v0.1 model deliberately chose whole-entry overrides. That made inheritance safe and unambiguous, but it is unnecessarily verbose for the most common organization-specific performance changes. A customer that only changes an Availability target from 95% to 97%, replaces a formula reference, or changes a response workflow currently has to restate the entire KPI node.

That creates three problems:

1. child contracts duplicate inherited semantics they do not own;
2. parent improvements are easier to accidentally shadow; and
3. provenance says which contract supplied the final node, but not which fields were intentionally specialized.

There is also no explicit way for an organization to say that an inherited response binding, accountability, KPI or relationship does not apply. Silent omission cannot mean deletion because omission is the core inheritance mechanism.

## Decision

CEPIO introduces Performance Contract Specialization v0.2 as an additive sparse-overlay capability.

v0.1 whole-entry overlays remain valid and unchanged. v0.2 adds two explicit operations:

- **patch** — refine allowlisted fields of an inherited element; and
- **suppress** — explicitly remove one inherited element from the effective child graph.

The complete `PerformanceContract` remains unchanged and remains the only directly evaluable performance truth. All v0.2 operations are resolved before evaluation.

### Field-level patching

Patch operations target a stable inherited identity and only modify allowlisted non-identity fields.

Examples:

```text
Industry KPI: Operational Availability
  target       >= 95%
  formula_ref  logic://industry/availability/v1

Organization patch:
  target       >= 97%
  formula_ref  logic://customer/availability/v7

Effective KPI:
  same KPI identity
  same KPI kind
  customer-specific target and formula
```

Patchable fields are deliberately bounded:

- subject: `name`, `parent_id`;
- performance node: descriptive fields, scope, unit, formula/reference, target, thresholds, freshness and validity fields;
- contribution: `weight`, `confidence`, `rationale`;
- response binding: statuses, workflow definition and rationale.

Identity-bearing fields such as node ID/kind, subject ID/kind and relationship endpoints/relation are not patchable. Changing those means creating a different semantic element, not refining an inherited one.

### Explicit clearing

Some inherited optional fields can be explicitly cleared. Clearing is distinct from omission:

- omitted field = inherit;
- cleared field = intentionally remove the inherited value.

For example an organization may clear a reference target while keeping the KPI definition, or clear a generic formula reference until its governed Business Logic binding is registered.

### Explicit suppression

Suppressions must name the inherited element and include a reason. Suppression is **non-cascading**.

If a child suppresses a KPI but leaves a contribution, accountability or response binding that still references it, final strict `PerformanceContract` validation fails closed. CEPIO never guesses which dependent semantics should disappear.

This is intentional governance behavior: removing enterprise meaning must be explicit.

### Operation conflicts

Within one overlay an element cannot simultaneously be:

- patched and suppressed; or
- supplied as a whole-entry definition and also patched/suppressed.

These conflicts are rejected before resolution.

### Provenance and audit

v0.2 retains final element lineage and adds a deterministic specialization-operation trail recording:

- operation type: add, override, patch or suppress;
- element type and stable key;
- source contract ID/version/layer;
- changed field names for patches; and
- declared reason when supplied.

This enables Industry IQ to explain not only **where the effective KPI came from**, but also **what an organization or persona intentionally changed**.

### Performance-management semantics

Inheritance remains contextual, not a KPI cascade.

An organization may patch a corporate KPI. A role/persona may add a Key Result that contributes to that KPI. An individual may add an accountability relationship to the Key Result. The individual does not therefore own the corporate KPI.

Example:

```text
Industry Reference
  Operational Availability KPI
        |
        v
Organization
  patch target/formula/definition
        |
        v
Reliability Engineer persona
  add KR: Reduce Repeat Failures
  add contribution: KR -> Availability
        |
        v
Individual Engineer
  add contributes_to accountability on the KR
```

### Safety and execution boundary

Specialization changes semantic composition only. It does not:

- execute Business Logic;
- infer causality;
- start workflows;
- authorize decisions; or
- perform external actions.

The existing Performance Runtime, Performance Service, Industry IQ reasoning, Workflow Policy and Kinetic execution boundaries remain authoritative.

## Compatibility

- Existing v0.1 overlay semantics remain supported.
- The complete `PerformanceContract` schema is unchanged.
- Existing KPI/OKR identities and organization boundaries remain unchanged.
- Final resolved graphs still pass the existing strict contract validator.

## Consequences

### Positive

- Organizations can specialize reference KPIs without copying entire nodes.
- Persona and individual contracts remain small and intention-revealing.
- Reference-model improvements are less likely to be accidentally shadowed.
- Non-applicable inherited semantics can be removed explicitly and audibly.
- Effective performance meaning becomes more explainable at field level.

### Trade-offs

- Patchable fields require an explicit allowlist and versioned governance.
- Suppression is intentionally verbose when dependent graph elements must also be removed.
- v0.2 does not attempt arbitrary JSON Patch semantics.
- Multi-parent or same-layer inheritance remains unsupported.

## Validation

Qualification covers:

- v0.1 compatibility;
- organization KPI target/formula/definition specialization;
- role/persona and individual accountability composition;
- runtime evaluation against the effective patched target;
- response-binding suppression/replacement;
- explicit clearing of optional inherited fields;
- contribution metadata refinement;
- missing patch/suppression targets;
- non-cascading suppression and strict graph validation;
- identity-field mutation protection; and
- same-overlay operation conflicts.

## Deferred

- automatic cascading deletion;
- multiple inheritance;
- cross-customer inheritance;
- quantitative causal inference;
- automatic workflow/action execution.
