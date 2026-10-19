# Reliability IQ v0.5 — Bad Actor & Fleet Reliability IQ

## Purpose

REL-IQ-005 identifies persistent reliability bad-actor candidates without confusing raw event volume with poor reliability.

The executable question is:

> Which equipment items show persistently elevated reliability burden after normalizing failure and downtime against comparable service exposure across repeated operating periods, and where should human reliability engineering focus?

The capability is cross-industrial. Drilling equipment is a proving context, not the owner of the semantics.

## Why normalization is mandatory

A heavily used asset can accumulate more failures than a lightly used asset while still performing better per unit of service. REL-IQ-005 therefore refuses to rank assets from raw failure count alone.

For every equipment-period pair it requires explicit governed service-exposure evidence and derives:

```text
normalized failure rate
  = failure count / exposure × configured exposure scale

normalized downtime rate
  = downtime hours / exposure × configured exposure scale
```

The normalization scale is explicit configuration (for example per 1,000 operating hours). CEPIO does not hard-code a universal industrial denominator.

## Reused semantics

No canonical ontology or public API change is introduced. The pack reuses:

- `Equipment`
- `FailureEvent`
- `failureOfEquipment`
- `KPI`
- `KPIObservation`
- `observationForEntity`
- `observationOfKPI`
- `startTime`
- `downtimeHours`
- `value`
- `unitSymbol`
- `validFrom`
- `validTo`

Service exposure is represented as generic KPI evidence. The KPI identity, calculation convention and source lineage remain external/governed rather than becoming a dedicated `OperatingHours` ontology class.

## Peer-population contract

A bad actor is a comparative conclusion, not an intrinsic asset state.

Each assessment therefore has one explicit `comparison_context`, such as a same-duty pump cohort or equivalent rig-system cohort. The context is configuration/profile metadata, not a new ontology branch.

REL-IQ-005 requires:

- at least three peer equipment items;
- at least two non-overlapping analysis periods;
- the same qualified peer population in every period;
- one unique exposure observation for every equipment-period pair;
- one common exposure KPI identity and engineering unit across the population.

Changing duty/context normally means running a separate peer assessment rather than mixing incomparable equipment.

## Exposure qualification

Every exposure observation must:

1. be a governed `KPIObservation`;
2. resolve through `observationForEntity` to exactly the assessed Equipment;
3. resolve through `observationOfKPI` to exactly the configured exposure KPI;
4. carry positive numeric `value`;
5. carry the configured `unitSymbol`;
6. carry timezone-aware `validFrom` and `validTo` that cover the complete analysis period.

Reusing the same exposure observation across periods fails closed so repeated assessment windows cannot manufacture persistence from one source record.

## Failure-burden qualification

Every supplied failure event must:

1. be a governed `FailureEvent`;
2. resolve through `failureOfEquipment` to exactly one assessed Equipment;
3. carry timezone-aware `startTime` inside the supplied period;
4. carry non-negative numeric `downtimeHours`.

Duplicate event IDs inside or across periods fail closed.

## Peer comparison

For each period CEPIO calculates the peer median normalized failure rate and peer median normalized downtime rate.

An equipment-period can be:

- `WITHIN_PEER_RANGE`
- `ELEVATED_FAILURE_RATE`
- `ELEVATED_DOWNTIME_RATE`
- `ELEVATED_MULTI_DIMENSION`

Elevation requires both:

1. an explicit minimum evidence-support threshold (for example minimum failure events or downtime hours), and
2. a normalized rate greater than the peer median multiplied by an explicit governed multiplier.

The support floor prevents a zero-median peer population from turning one isolated event into a bad-actor conclusion.

## Persistence

Cross-period equipment state is:

- `WITHIN_EXPECTATION` — no elevated periods;
- `WATCHLIST` — elevated in at least one period but below the persistence threshold;
- `PERSISTENT_BAD_ACTOR` — elevated in at least the configured minimum number of periods.

A single period can never prove persistence.

The review disposition is:

- `MONITOR`
- `RELIABILITY_REVIEW`
- `BAD_ACTOR_ENGINEERING_REVIEW`

These remain advisory. REL-IQ-005 does not automatically alter maintenance strategy, approve capital, reschedule maintenance, redesign equipment, or control physical assets.

## Relationship to earlier Reliability IQ

```text
REL-IQ-003
Condition Monitoring
"What is deteriorating now?"
        ↓
REL-IQ-004
RUL + Maintenance Window
"How much life remains and does the plan fit?"
        ↓
REL-IQ-001
Asset Intervention
"What intervention should be considered?"

REL-IQ-002
Failure Pattern & Recurrence
"Which failure modes recur?"
        ↓
REL-IQ-005
Bad Actor & Fleet Reliability
"Which assets stay abnormal after exposure normalization?"
```

REL-IQ-002 detects repeated failure patterns. REL-IQ-005 answers the different fleet question of whether an asset is persistently worse than comparable peers after service exposure is normalized.

## North-star alignment

```text
Authoritative failure history + service exposure KPI
                    ↓
replaceable bindings
                    ↓
Equipment / FailureEvent / KPIObservation
                    ↓
REL-IQ-005
exposure normalization + peer median + persistence
                    ↓
watchlist / bad-actor engineering review
                    ↓
human reliability strategy process
```

The result remains an evidence-backed assessment, not enterprise fact. Source systems remain authoritative, customer data is not used to train CEPIO, and customer-specific peer definitions and thresholds remain configuration rather than ontology forks.
