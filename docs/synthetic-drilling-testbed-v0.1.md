# Synthetic Drilling Testbed v0.1

## Purpose

The CEPIO Synthetic Industrial Dataset — Drilling v0.1 is a reference conformance fixture for the CEPIO MVP. It is not a sample customer dataset. Its purpose is to provide deterministic ground truth for testing identity resolution, ontology mapping, graph traversal, temporal reasoning, provenance, API behavior and agent-facing semantic queries.

## Design principles

1. **Existing ontology first.** The fixture aligns to current CEPIO drilling, industrial and reliability semantics rather than defining duplicate domain concepts.
2. **Ground truth is explicit.** Failure causes, leading signals, NPT impact and maintenance actions are known before the query is executed.
3. **Messiness is intentional.** Cross-system aliases model the naming inconsistency normally seen between historians, maintenance systems, equipment masters and drilling reports.
4. **Generation is deterministic.** A fixed seed makes telemetry and reference records reproducible in CI.
5. **Scale is configurable.** Small CI runs and larger performance runs use the same generator and scenario contract.

## Test boundary

The v0.1 fixture proves the data-to-semantics boundary. It does not yet claim production fidelity for WITSML, IADC DDR, SAP PM or historian adapters. Those systems should be introduced later as adapter substitutions while keeping the CEPIO-facing semantic contract stable.

## Golden-question gate

The twenty golden questions in `mvp/datasets/drilling-v0.1/tests/golden-questions.json` form the initial semantic acceptance gate. MVP progression should require at least 90% correct answers, with 100% provenance for returned facts and zero need for the consumer to know the originating source-system schema.

## Next step

After this fixture is wired into CEPIO runtime ingestion/query paths, create an equivalent refinery fixture and measure the percentage of CEPIO Core, API and test machinery reused unchanged. That is the first quantitative Generalization Lab test of the platform abstraction.
