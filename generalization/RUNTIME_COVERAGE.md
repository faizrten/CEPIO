# CEPIO Runtime Coverage v0.5

Runtime coverage is the bridge between semantic capability and operational assurance.

- **Semantic capability** asks whether the frozen competency question can be represented by an approved CEPIO semantic composition.
- **Runtime coverage** asks whether a CEPIO runtime can materialize and retrieve the evidence pattern for every frozen question.
- **Operational assurance** separately proves temporal reconstruction, provenance, scoped authority, policy, governed action and Operator evidence discipline.

These gates are intentionally independent. A semantic pass does not imply that a runtime can retrieve evidence, and runtime retrieval does not imply production data quality or production readiness.

## RuntimeCapabilityRequirement contract

Each `RuntimeQuestionCase` declares:

1. the frozen competency-question ID;
2. the semantic capabilities being exercised;
3. a synthetic, source-neutral evidence graph;
4. deterministic relationship/property probes CEPIO must resolve;
5. an evidence bundle generated from runtime results.

No expected prose answer is used to determine pass/fail. A question passes only when every runtime probe resolves exactly as specified and the Operator evidence gate rejects citations outside the current evidence bundle.

## Drilling v0.5 gate

`generalization/runtime/drilling-contractor-runtime-coverage-v0.5.yaml` covers every question in the frozen `drilling-contractor-persona-capabilities-v0.3.yaml` pack.

Required release condition:

- 14/14 frozen questions present;
- 14/14 runtime cases PASS;
- every question emits runtime evidence;
- every supported Operator answer cites only current-bundle evidence;
- a fabricated evidence citation is rejected;
- existing v0.4 operational-assurance gates remain 5/5 PASS;
- no ontology or competency-pack change is permitted merely to satisfy the runtime gate.

## What this does not prove

A 100% score means the reference CEPIO runtime can execute the declared evidence retrieval contracts for the frozen suite. It does **not** prove customer data completeness, live integration quality, latency/SLA, source-system correctness, model accuracy, or autonomous-action readiness.

The next step after v0.5 is to bind the same runtime contract to a constrained live Operator Agent and then reuse the contract against a second materially different E&PI archetype.
