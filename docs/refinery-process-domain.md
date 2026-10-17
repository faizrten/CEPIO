# Refinery / Process-Industry Domain Semantics

## Purpose

This note documents the first CEPIO process-industry domain remediation derived from the frozen refinery/process-manufacturing Generalization Lab challenge.

The implementation does **not** introduce a separate refinery ontology or duplicate the canonical industrial model. It extends the existing `process_industry` domain module only where the accepted refinery gap triage demonstrated missing source-neutral process-operation semantics.

## Architectural boundary

CEPIO continues to use the shared canonical industrial identity model:

```text
CEPIO Core / Kinetic
        |
Industrial Common
        |
Process Industry
        |
Refinery / process-manufacturing competency compositions
        |
Customer profiles
```

`industrial:ProcessUnit` remains the canonical process-unit identity. The process-industry module does not define `process:ProcessUnit`.

The implementation follows the Generalization Lab rule:

> Reuse common CEPIO abstractions first; add a process-domain specialization only when the business meaning cannot be expressed faithfully with the existing vocabulary.

## Added process-operation semantics

### Process constraint

`process:ProcessConstraint` specializes `kinetic:Constraint` and is scoped to `industrial:ProcessUnit` by `process:constraintOnUnit`.

Economic exposure and material/utility dependency are not duplicated as process-specific predicates. They continue to compose through `cepio:impacts` and `cepio:dependsOn`.

### Operating envelope and operating limit

`process:OperatingEnvelope` represents the approved operating context for a process unit. `process:OperatingLimit` specializes the common `kinetic:Constraint` abstraction. `process:envelopeForUnit` scopes an envelope to the canonical process unit.

Limits can be composed into an envelope through the existing generic `cepio:partOf` relationship rather than introducing a second containment vocabulary.

### Process deviation

`process:ProcessDeviation` is modeled as `cepio:State` because an out-of-envelope condition is a time-varying operational state, not a work-plan deviation. `process:deviationAgainstEnvelope` links the observed deviation to its governing operating envelope.

### Startup / restart

`process:StartupOrRestart` specializes `cepio:Activity`.

Restart readiness remains a composition over existing CEPIO semantics:

```text
StartupOrRestart
  dependsOn -> ProcessUnit
  dependsOn -> WorkPermit
  dependsOn -> EnergyIsolation
  dependsOn -> WorkItem
  dependsOn -> SafetyBarrier
  requiresApproval -> Approval
```

No restart-specific permit, isolation, barrier or approval predicates are introduced.

## Generalization Lab status

The historical refinery baseline remains immutable. The raw v0.1 result and normalized v0.1.1 result are retained as evidence of the ontology state before remediation.

The accepted refinery triage classified 11 architectural decisions as:

- 3 `CORE` — implemented in reusable HSE/performance modules;
- 4 `DOMAIN` — implemented in `process_industry` by this slice;
- 1 `MAPPING` — energy-intensity KPI identity/formula remains a semantic-metric mapping concern;
- 3 `REJECT` — proposed convenience semantics are intentionally not canonicalized.

The frozen refinery competency pack is not edited by remediation.

## Standards role

The refinery challenge currently uses public metadata from ISA-95 / IEC 62264, ISO 14224, IEC 61511, API RP 754 and ISO 50001. These references are benchmarks and evidence sources, not copied canonical vocabularies.

The next refinery competency expansion should add new independent challenge questions grounded in additional process-industry references such as procedure automation, alarm management, production assurance, risk-based inspection, engineering-data exchange and field-device information models. Those references should first enter the standards registry and a new frozen competency pack; they should not cause ontology additions until the harness demonstrates a genuine `CORE`, `DOMAIN`, `PROFILE`, `MAPPING` or `REJECT` decision.

## Module evolution

`process_industry` evolves additively from `0.1.0` to `0.1.1` and now depends on the existing `kinetic` foundation module because process constraints and operating limits reuse `kinetic:Constraint`.
