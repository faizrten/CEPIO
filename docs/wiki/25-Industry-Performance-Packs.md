# Industry Performance Packs

Industry Performance Packs turn CEPIO's Enterprise Performance Graph into reusable industry knowledge.

A pack is not a new contract type. It is a complete organization-neutral `PerformanceContract` at the `industry_reference` layer. Customer organizations explicitly specialize it using Performance Contract v0.2.

## Why this exists

The Enterprise Performance Graph defines the grammar for objectives, KPIs, metrics, guardrails, accountability and driver relationships. Industry Performance Packs supply reusable domain content for that grammar.

```text
Enterprise Performance Graph
        ↓ grammar
Industry Performance Pack
        ↓ reusable domain reference
Organization specialization
        ↓ customer formula / target / accountability
Role / Persona / Individual
        ↓
Effective Performance Contract
```

This means CEPIO can know that operational availability, energy intensity or NPT are important industrial performance concepts without pretending that every company calculates or governs them the same way.

## Current built-in reference packs

### Refinery / process manufacturing

`cepio.performance.refinery.reference@0.1.0`

Covers operating margin, operational availability, throughput, production loss, energy intensity, product conformance, unplanned downtime, repeat equipment failures, process-safety guardrails and environmental exceedances.

Reference personas connect this graph to the existing refinery persona catalogue, including Plant Manager, Operations Manager, Reliability Engineer, Process Engineer, Energy Manager, Quality Manager, Process Safety Manager, Environmental Manager, Finance Controller and Production Assurance Engineer.

### Drilling contractor

`cepio.performance.drilling-contractor.reference@0.1.0`

Covers contract margin, fleet utilization, operational uptime, NPT ratio/duration, dayrate realization, backlog coverage, maintenance downtime, invisible lost time, revenue leakage, serious-safety guardrails and well-control barrier failures.

Reference personas align to the drilling-contractor catalogue, including CEO, COO, CFO, VP Drilling Operations, Rig Manager, Drilling Superintendent, Reliability Engineer, Drilling Performance Engineer, Commercial Manager, HSE Manager and Subsea/Well Control Engineer.

## What stays customer-owned

The reference packs intentionally leave these unset:

- formula references;
- targets;
- thresholds; and
- workflow response bindings.

The customer overlay supplies those semantics, along with local organizational subjects, KPI scope and any accountability rebinding.

That preserves the governing principle:

> CEPIO owns the grammar and reusable industry reference intelligence; the organization owns its operating meaning and policy.

## Performance Packs versus Industry IQ packs

Performance Packs describe what performance means and how industrial outcomes relate.

Industry IQ packs provide executable domain capability such as calculations, decisions or governed actions.

They complement each other rather than sharing a registry or execution model.

For example, a drilling deployment can use the drilling-contractor Performance Pack to define NPT, utilization and contract-margin relationships while separately installing the executable NPT, Rig Readiness and Reliability Industry IQ capabilities.

## Causality discipline

A reference graph must not overstate causal truth.

Structural relationships may use `contributes_to`, `depends_on` or `constrains` where the industrial relationship is sufficiently stable. Contextual relationships use `influences` when customer classification or policy determines the actual causal/accounting interpretation.

For example, Invisible Lost Time influences NPT but is not automatically classified as NPT in the reference pack.

## Related documentation

- [Enterprise Performance Graph](22-Enterprise-Performance-Graph.md)
- [Industry Performance Packs technical guide](../industry-performance-packs.md)
- [ADR-0034](../adr/ADR-0034-industry-performance-reference-packs-v0.1.md)
- [Target Users / Personas](19-Target-Users-Personas.md)
