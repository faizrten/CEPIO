# Reference Scenarios

## 1. Refinery reliability and margin

The existing reference reasoning chain connects operational equipment to financial impact.

```text
Hydrocracker Margin KPI
        -> Hydrocracker Process Unit
        -> K-201 Recycle Gas Compressor
        -> Trip Event
        -> Historical State
        -> Risk / Production-Loss Function
        -> Decision
        -> Governed CreateWorkOrder
        -> Critical Spare
        -> Inventory
        -> Supplier
        -> Audit + Provenance
```

This demonstrates why CEPIO is broader than an asset hierarchy.

## 2. Molecule-to-margin

```text
Feedstock
 -> Storage / transfer
 -> Process unit
 -> Equipment constraints
 -> Production and quality
 -> Energy consumption
 -> Contract / product economics
 -> Margin / EBITDA
```

CEPIO provides the cross-domain semantics required to reason across these layers.

## 3. Asset reliability

```text
Observation / anomaly
 -> equipment state
 -> failure mode / risk
 -> production consequence
 -> maintenance strategy
 -> work order
 -> spare part
 -> supplier
 -> action
 -> outcome feedback
```

Targeted as a v0.6 reference application.

## 4. Turnaround planning

```text
Turnaround scope
 -> assets
 -> work packages
 -> materials
 -> workforce
 -> schedule
 -> dependencies
 -> risk
 -> approval / action
```

CEPIO can unify P6/project semantics with maintenance, supply and workforce context.

## 5. Upstream + OSDU

```text
OSDU well / wellbore / reservoir context
 -> CEPIO operational asset context
 -> production / integrity / maintenance
 -> work / materials / risk
 -> enterprise economics
```

OSDU remains the upstream data foundation while CEPIO provides enterprise operating relationships.

## 6. Drilling

```text
Rig
 -> equipment systems
 -> drilling activity
 -> NPT event
 -> maintenance/reliability consequence
 -> schedule / contract consequence
 -> decision/action
```

The drilling domain module allows rig/operator workflows to reuse shared asset, work, reliability, supply and commercial semantics.

## 7. EPCIC / commissioning

```text
Design object
 -> package / system
 -> construction completion
 -> inspection/test
 -> punch item
 -> commissioning system
 -> startup readiness
 -> production/economic exposure
```

This is particularly relevant to complex integrated refinery/petrochemical projects.

## Reference application acceptance test

A meaningful CEPIO application should demonstrate the full loop:

```text
Observe
 -> Understand
 -> Reason
 -> Decide
 -> Recommend
 -> Authorize
 -> Act
 -> Observe outcome
```

A static graph visualization alone is not sufficient proof of CEPIO value.
