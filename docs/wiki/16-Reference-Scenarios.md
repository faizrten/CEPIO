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
 -> activity/productivity classification + causal downtime
 -> maintenance/reliability consequence
 -> schedule / contract consequence
 -> decision/action
```

The drilling domain module allows rig/operator workflows to reuse shared asset, work, reliability, supply and commercial semantics.

### Drilling MVP conformance testbed

The synthetic drilling fixture provides deterministic ground truth for exercising that chain without customer data.

**v0.1** establishes structured/tabular records, low-frequency telemetry, events, maintenance history, source aliases and twenty golden semantic questions across four engineered scenarios.

**v0.2** preserves the same scenarios and adds documents, inspection images, engineering diagrams, geospatial context and high-frequency waveforms. These source-native artifacts are referenced rather than serialized into the ontology. CEPIO owns the canonical identity, relationship, temporal and provenance binding that makes the evidence usable consistently by REST, SDK and MCP consumers.

The v0.2 deterministic acceptance gate contains thirty golden questions: the original twenty plus ten multimodal questions covering evidence corroboration, diagram grounding, geospatial relationships, waveform evidence, cross-modal fusion and artifact provenance.

A separate public Agent Challenge question set exercises higher-order tool use, but the qualification answer key is intentionally not distributed in the public repository. See [CEPIO Agent Challenge v0.1](CEPIO-Agent-Challenge-v0.1.md) and ADR-0011.

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

## Competency and assurance fixtures

The Generalization Lab contains frozen drilling and refinery challenges linked to persona catalogs. The drilling capability pack v0.3 has a checked-in 14/14 semantic PASS expectation. A separate operational-assurance fixture exercises temporal state, provenance, scoped authority, policy/action audit and evidence citation discipline across five gates. It references four questions and does not establish full runtime coverage of the semantic pack.

See [Competency & Assurance](20-Competency-Assurance.md) for evaluation contracts and limits, and [Target Users / Personas](19-Target-Users-Personas.md) for the roles behind those questions.

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
