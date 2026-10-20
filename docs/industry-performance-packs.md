# Industry Performance Packs v0.1

Industry Performance Packs are CEPIO's reusable starting point for enterprise performance semantics.

They are **not** a new ontology, KPI engine or executable Industry IQ pack. Each pack is a complete `PerformanceContract` at the `industry_reference` layer. Organizations explicitly specialize it with the existing Performance Contract v0.2 overlay model.

## Design rule

> Standardize the structure of industrial performance intelligence, not the customer's formula or target.

The reference layer provides stable KPI/metric identities, driver relationships, guardrails and reference persona accountability. The customer layer owns formula, denominator, exclusions, aggregation, target, threshold, fiscal/reporting convention, data binding and governed response.

```text
Industry Performance Pack
  PerformanceContract(layer=industry_reference)
                ↓ explicit extends_contract_id
Organization Performance Contract
  PerformanceContractOverlayV2
                ↓
Role / Persona specialization
                ↓
Individual contribution/accountability
                ↓
Resolved effective Performance Contract
                ↓
Performance Runtime → Industry IQ → governed Decision
```

## Built-in packs

### Refinery / process manufacturing

Contract:

```text
cepio.performance.refinery.reference@0.1.0
```

Reference performance spine:

```text
Repeat equipment failures
          ↓
Unplanned downtime
          ↓
Operational availability
          ↓
Production loss ───────────────┐
                               │
Production throughput ─────────┤
Energy intensity ──────────────┤→ Operating margin → Enterprise objective
Product spec conformance ──────┘

Process-safety events ───────────────┐
Environmental limit exceedances ────┴→ constrain Enterprise objective
```

Reference personas include Plant Manager, Operations Manager, Reliability Engineer, Process Engineer, Energy Manager, Quality Manager, Process Safety Manager, Environmental Manager, Finance Controller and Production Assurance Engineer. These align with the checked-in refinery persona catalogue; the Performance Pack adds governed performance relationships rather than creating another persona taxonomy.

The pack intentionally leaves `formula_ref`, `target`, `thresholds` and `response_bindings` unset.

### Drilling contractor

Contract:

```text
cepio.performance.drilling-contractor.reference@0.1.0
```

Reference performance spine:

```text
Maintenance downtime → Operational uptime → Fleet utilization ─┐
                                                                │
NPT duration → NPT ratio → Operational uptime ──────────────────┤
Dayrate realization ─────────────────────────────────────────────┤→ Contract margin → Enterprise objective
Revenue leakage ─────────────────────────────────────────────────┘

Backlog coverage ── influences ───────────────────────────────────→ Enterprise objective
Invisible lost time ── influences ────────────────────────────────→ NPT ratio

Serious safety events ───────────────┐
Well-control barrier failures ───────┴→ constrain Enterprise objective
```

`Invisible Lost Time -> NPT ratio` is deliberately `influences`, not `contributes_to`: a contractor's activity taxonomy and commercial rules determine whether a time interval is formally classified as NPT.

Rig Readiness remains the existing deterministic categorical Industry IQ assessment. The Performance Pack does not invent a synthetic readiness percentage simply to fit a KPI model.

## Organization specialization example

A customer does not copy the reference availability node. It binds only what it owns:

```python
PerformanceContractOverlayV2(
    id="customer.performance",
    version="1.0.0",
    layer="organization",
    organization_id="customer",
    extends_contract_id="cepio.performance.refinery.reference",
    patches=(
        PerformanceElementPatch(
            element_type="node",
            element_key="cepio.reference.refinery.kpi.operational-availability",
            set_fields=(
                PerformanceFieldSet(
                    field="formula_ref",
                    value="logic://customer/operational-availability/v1",
                ),
                PerformanceFieldSet(
                    field="target",
                    value={"operator": "gte", "value": 0.96},
                ),
            ),
        ),
    ),
)
```

The organization may also rebind `scope_subject_id`, suppress a reference accountability, add local KPIs/KRs or attach a governed response binding. Every operation retains specialization provenance.

## What belongs in a reference pack

Good reference candidates are concepts that industrial practitioners recognize across many organizations while still allowing local calculation/governance:

- objectives and outcomes;
- stable KPI/metric identity;
- generic unit/category where useful;
- qualitative driver/constraint structure;
- reference role/persona accountability; and
- definitions that explicitly identify which semantics remain contextual.

Do **not** put a customer formula, target, threshold, fiscal calendar, rate table, customer-specific org chart, source-system identifier or workflow execution authority in the reference layer.

## Relationship to Industry IQ packs

Industry Performance Packs and executable Industry IQ packs are complementary:

```text
Performance Pack
  What does good performance mean?
  What KPIs/guardrails/drivers matter?
  Who commonly owns or contributes?

Industry IQ Pack
  What domain reasoning/function/decision capability can execute?
  What evidence does it require?
  What governed capability does it expose?
```

A drilling deployment may therefore use the drilling-contractor Performance Pack alongside `cepio.iq.drilling.npt`, Rig Readiness, Reliability reasoning and other executable Industry IQ packs. There is no second runtime pack registry for Performance Packs.

## Next packs

The recommended expansion order is:

```text
1. Petrochemical / chemicals
2. Upstream operator
3. Power generation / utilities
4. Mining
5. Midstream / terminals
6. EPC / EPCIC project delivery
```

Each new pack should be admitted only after the existing persona/competency artifacts demonstrate enough stable cross-organization performance structure to justify a reusable reference contract.
