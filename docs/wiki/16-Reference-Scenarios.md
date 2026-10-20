# Reference Scenarios

Reference scenarios are product proofs, competency fixtures and integration testbeds. They must distinguish **synthetic/reference evidence** from **live environment qualification**.

The primary current product convergence scenario is the K-201 Reliability lighthouse for v0.5 CONNECT and v0.6 EXECUTE.

## 1. K-201 reliability — CONNECT lighthouse

The current target end-to-end chain is:

```text
PI / historian anomaly
 -> CEPIO ConditionObservation + state + provenance
 -> K-201 compressor identity/context
 -> Reliability Industry IQ / Skill
 -> failure/degradation reasoning
 -> production exposure + uncertainty
 -> Decision
 -> contextual policy / authority
 -> human approval where required
 -> durable workflow
 -> SAP work-order Action
 -> SAP acknowledgement/read-back
 -> verification / reconciliation
 -> WorkflowOutcome
 -> audit / assurance evidence
```

The release proof requires meaningful context from at least three authoritative source domains and one authenticated, idempotent, verified and reconciled external writeback.

Existing workflow, Fabric, Skill, external-action or synthetic compressor tests do not independently qualify this live CONNECT gate.

## 2. Reliability / Maintenance Command Center — EXECUTE lighthouse

The v0.6 EXECUTE application proof builds on the qualified CONNECT integration chain.

Primary personas:

- Reliability Engineer;
- Maintenance Planner;
- Operations Engineer;
- Maintenance Manager;
- Plant Manager.

Application loop:

```text
Detect degradation
 -> explain evidence/context
 -> assess likely failure / consequence / uncertainty
 -> inspect maintenance, materials and production constraints
 -> generate intervention options
 -> compare risk / cost / availability impact
 -> recommend
 -> authorize
 -> execute governed Action
 -> verify Outcome
 -> evaluate / learn
```

The application should consume reusable CEPIO Industry IQ, Skills, Functions, Performance Contracts, Decision definitions, policy and workflows rather than hiding industrial logic in UI code.

## 3. Microsoft Foundry Reliability Agent Lighthouse

For Microsoft-hosted agent execution:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

The Reliability Agent Lighthouse defines staged proof from Foundry-hosted agent reasoning through CEPIO MCP and Reliability Industry IQ toward human approval, governed SAP Action, evaluation and provider portability.

The current G1 path is intentionally Decision-focused and can restrict the host tool surface to governed reads, Functions and Skill evaluation while excluding Action execution.

A merged qualification runner/profile makes the proof executable; it does **not** constitute a real live Foundry PASS without environment evidence.

## 4. Refinery reliability and margin

The historical/reference reasoning chain connects equipment degradation to economic impact:

```text
Hydrocracker Margin KPI
 -> Hydrocracker Process Unit
 -> K-201 Recycle Gas Compressor
 -> event / historical state
 -> risk / production exposure
 -> maintenance / materials context
 -> Decision
 -> governed Action
 -> Outcome
 -> KPI / margin consequence
```

This demonstrates why CEPIO is broader than an asset hierarchy and how operational state can connect to Performance Contracts.

## 5. Molecule-to-margin

```text
Feedstock
 -> storage / transfer
 -> process unit
 -> equipment constraints
 -> production + quality
 -> energy consumption
 -> contract / product economics
 -> margin / EBITDA
```

CEPIO supplies cross-domain identity, semantics, evidence and performance relationships rather than recreating process simulation or ERP accounting engines.

## 6. Enterprise Performance Graph

Performance Contracts provide a structured chain from objectives to operating evidence and governed response:

```text
Objective
 -> Key Result / KPI / Guardrail
 -> contribution / driver relationships
 -> accountable role / persona
 -> current industrial evidence
 -> deviation / exposure
 -> recommendation / Decision
 -> governed workflow response
```

Reference Refinery and Drilling Contractor Performance Packs provide organization-neutral starting semantics. Customer formulas, targets, thresholds, scopes and accountability are explicit specialization.

## 7. Turnaround planning

```text
Turnaround objective / readiness
 -> asset scope
 -> work packages
 -> materials
 -> workforce / competency
 -> P6 schedule / dependencies
 -> permits / risk
 -> performance / readiness indicators
 -> Decision / approval
 -> governed Action
```

This scenario pressures CEPIO's ability to combine project, maintenance, supply, workforce, risk and performance intelligence.

P6 live qualification is not currently a product guarantee.

## 8. Upstream / OSDU opportunity evaluation

OSDU/ADME remains authoritative for subsurface technical truth.

```text
OSDU Well / Wellbore / interpretation / model scenario
 -> CEPIO evidence references
 -> assumptions / hypotheses
 -> uncertainty / confidence / information gain
 -> Opportunity
 -> Options
 -> recommendation
 -> Decision
 -> governed downstream work/action
```

CEPIO should not copy seismic, well-log, reservoir-grid or model payloads merely to reason about them.

The OSDU-first semantic/binding boundary is on main; real live upstream provider qualification is separate.

## 9. Drilling contractor Industry IQ

```text
Rig / well / campaign
 -> activity / subactivity
 -> equipment + crew readiness
 -> condition / maintenance
 -> NPT / invisible lost time / operational loss
 -> contract / dayrate / revenue consequence
 -> performance contract / guardrails
 -> Decision / workflow / Action
```

The drilling domain is a strategic generalization test because its operating model differs materially from refinery/process manufacturing while reusing common asset, work, reliability, HSE, workforce, supply and commercial semantics.

Current mainline evidence includes deterministic semantic/runtime qualification, provider-neutral drilling capability patterns and organization-neutral drilling performance reference semantics.

## 10. Drilling synthetic conformance testbed

The synthetic drilling fixture provides deterministic ground truth without customer data.

Historical fixture versions include structured/tabular records, telemetry, events, maintenance history, aliases and multimodal evidence such as documents, images, diagrams, geospatial context and waveforms.

Source-native artifacts are referenced rather than serialized into the ontology. CEPIO owns the identity, relationship, temporal, provenance and evidence binding required to use them consistently.

Synthetic/lab qualification is valuable assurance evidence but must not be described as live customer or production integration proof.

Protected adversarial/evaluator assets may remain in CEPIO Labs according to the public/private IP boundary.

## 11. EPCIC / commissioning

```text
Design object / tag
 -> package / system
 -> construction completion
 -> inspection / test
 -> punch item
 -> commissioning system
 -> startup readiness
 -> schedule / risk / production exposure
 -> Decision / governed response
```

This scenario is especially relevant to integrated refinery/petrochemical projects and tests federation with engineering/project standards rather than ontology duplication.

## 12. Platform portability scenario

A strategic GENERALIZE proof is that the same CEPIO competency / Skill / Decision behavior can operate over different authoritative provider bindings:

```text
Fabric context -----+
                    |
Cognite context ----+--> same CEPIO capability contract
                    |
OSDU context -------+
```

Provider transport changes; CEPIO industrial semantics, evidence requirements and authority should remain stable.

Early Binding Contract/Fabric parity evidence supports this direction. Real multi-provider enterprise qualification remains future proof.

## Competency and assurance fixtures

The Generalization/Competency work includes frozen drilling/refinery challenges, deterministic semantic-capability evaluation and representative operational-assurance gates.

Current known drilling evidence includes a v0.3 persona capability pack with 14/14 semantic PASS expectation plus separate operational assurance. These are different evaluation layers and must not be combined into a blanket production claim.

See [Competency & Assurance](20-Competency-Assurance.md).

## Reference application acceptance rule

A meaningful CEPIO operating application should increasingly demonstrate:

```text
Observe
 -> Understand
 -> Reason
 -> Decide
 -> Authorize
 -> Act
 -> Verify
 -> Learn
```

A static graph, plausible model answer, synthetic-only workflow or successful Action dispatch without source verification is not by itself sufficient proof of the CEPIO North Star.

See [Current State](../current-state.md) and [Roadmap](17-Roadmap.md) for current qualification boundaries.
