# Drilling Operator Industry IQ v0.1

## Purpose

This increment makes the **upstream operator-company side** of CEPIO Drilling Industry IQ executable. It is deliberately distinct from the existing `Operator v0.6` agent boundary, which governs how an AI planner uses CEPIO tools.

The operator IQ north star is:

> CEPIO should understand how an upstream operator plans, governs, executes, assures and optimizes well delivery across drilling-contractor and service-company interfaces while preserving source authority and decision rights.

## Accountability boundary

Operator and contractor IQ share the same canonical industrial objects. They do not receive separate copies of `Well`, `ActivityInterval`, `Risk`, `OperationalPlan`, `Decision` or other shared concepts.

The distinction is operating accountability:

- the **operator** owns the well objective/value case, approved plan, operator change control, risk acceptance, service/contractor acceptance and well-delivery economics;
- the **drilling contractor** owns the rig, contractor crews, equipment readiness, maintenance, execution capability and contractor performance obligations;
- both meet at the governed well/activity/event/report/service evidence boundary.

This means contractor Rig Readiness IQ or NPT IQ can provide evidence to an operator scenario without transferring the operator's plan or decision rights.

## First executable scenario — Well Delivery Assurance IQ

The first operator question is:

> Given the approved operator plan and current well execution, are we still on plan; which deviations or risks materially threaten delivery; and is a governed plan revision required?

Runtime pack:

`cepio.iq.drilling.operator-well-delivery@0.1.0`

Function:

`assessOperatorWellDelivery`

Decision:

`operator-well-delivery-intervention-recommendation`

Governed action:

`InitiateWellPlanRevision`

## Deterministic result

The assessment returns one of:

- `ON_PLAN`
- `AT_RISK`
- `INTERVENTION_REQUIRED`

It does not generate a synthetic score. The result is derived from governed evidence:

1. an approved/current `OperationalPlan` scoped to the assessed `Well`;
2. `ActivityInterval` execution evidence linked by `activityForWell`;
3. generic `PlanDeviation` evidence linked to the canonical plan by `deviationFromPlan` and to the affected well/activity by `impacts`;
4. canonical `Risk` evidence linked to the well or supplied activity through `hasRisk`.

Closed/resolved deviations and mitigated risks remain evidence but do not trigger intervention. Active advisory evidence yields `AT_RISK`. Blocked execution, material/critical deviations or high/critical active risks yield `INTERVENTION_REQUIRED`.

Missing, malformed, unsupported or incorrectly scoped evidence fails closed.

## Governed plan revision

`InitiateWellPlanRevision` does not change rig controls, drilling parameters or any physical process. It creates a canonical `PlanRevision` in `DRAFT` state and links it to the approved `OperationalPlan` using `revisesPlan`.

The action is restricted to explicit operator human roles:

- `operator_drilling_engineer`
- `operator_drilling_superintendent`
- `operator_wellsite_leader`

The recommender role cannot execute the action. Decision-to-Action causality and the normal CEPIO action audit path remain intact.

## Scenario portfolio

`generalization/industry-iq/drilling-operator-scenarios-v0.1.yaml` freezes 16 operator-side scenarios spanning well delivery, performance, NPT, risk/barriers, well control, contractor/rig performance, services, economics, change control, logistics, lessons learned, campaign allocation, subsurface integration, completion/production readiness, claims and portfolio capital allocation.

Only Well Delivery Assurance is newly executable in v0.1. The existing drilling NPT pack is identified for reuse rather than reimplemented.

## North-star rules

- no operator-specific ontology fork;
- no contractor-specific ontology fork;
- no canonical vocabulary added merely to pass a scenario;
- source systems remain authoritative;
- evidence bindings stay replaceable;
- AI assessments/recommendations are not enterprise facts;
- operator decision rights remain with the operator;
- customer data is not used to train CEPIO;
- safety-critical physical autonomy is prohibited.

## Next qualification

After v0.1, the strongest next operator scenario is **Drilling Performance and Invisible Lost Time IQ**, because it can reuse the same well/activity context plus NPT evidence and test whether CEPIO can separate contractor execution evidence from operator value/recovery decisions without semantic duplication.
