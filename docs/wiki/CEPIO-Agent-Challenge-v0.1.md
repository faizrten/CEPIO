# CEPIO Agent Challenge v0.1

## Purpose

The CEPIO Agent Challenge tests whether a general-purpose AI agent can answer industrial operational questions by using only the governed CEPIO semantic tool surface rather than learning source-system implementation details.

The experiment asks one product question:

> Can an intelligent model understand and reason over an industrial enterprise through CEPIO without direct access to the underlying source systems?

## Two evaluation modes

CEPIO deliberately separates deterministic public conformance from live-agent qualification.

### Public conformance

The public repository contains synthetic drilling datasets, public challenge questions, deterministic fixture generation and runtime acceptance tests. These assets are reproducible and suitable for CI, SDK/API/MCP validation and benchmark-protocol development.

Public fixture answers are not evidence of model generalization because repository readers can inspect them.

### Private qualification

A live Agent Challenge is qualification-grade only when its expected answers remain outside the public repository and outside the answering process. The evaluator must be supplied at execution time from an approved private source.

The public repository therefore does **not** contain a qualification answer key for the public challenge questions and this release does not enable a live qualification workflow or live-agent runner.

See `docs/adr/ADR-0011-agent-challenge-evaluator-isolation.md`.

## Agent isolation contract

For a controlled qualification run, the answering process receives only:

- the natural-language question;
- approved CEPIO tool schemas;
- results returned by CEPIO tools it explicitly invokes;
- the final-answer schema.

It does not receive expected references or values, evaluator state, ground-truth scenario hints, private benchmark artifacts, filesystem access, direct SQL/dataframe access or raw source-system connectors.

The evaluator scores the final answer only after the agent has completed its tool-use trace.

## Public challenge surface

The initial public challenge surface contains ten compositional questions across higher-order industrial reasoning tasks, including canonical identity resolution, relationship traversal, failure/NPT causality, maintenance state, post-maintenance evidence, well-control events, geospatial context, proactive maintenance and multimodal evidence retrieval.

The questions are additional to the deterministic thirty-question drilling v0.2 conformance pack.

## CEPIO tool boundary

A future live challenge should expose semantic operations such as object search, object retrieval, relationship traversal, event retrieval, identity resolution, evidence retrieval, measurement queries and provenance retrieval through the normal governed CEPIO interfaces.

Large/raw multimodal payloads remain source-native. The agent should receive CEPIO semantic bindings, summaries, provenance and source references rather than direct file/database access.

The live-agent retrieval/transport implementation is intentionally **not** part of this public promotion. It should be introduced together with the private-evaluator execution boundary so the benchmark protocol and its isolation guarantees evolve as one governed capability.

## Qualification metrics

A future private-evaluator run can retain the v0.1 target metrics:

| Metric | Qualification target |
| --- | ---: |
| Answer correctness | >= 80% |
| Evidence coverage | 100% |
| Structurally unsupported claims | 0 |
| Identity resolution | >= 95% |
| Median CEPIO tool calls | <= 8 |
| Semantic abstraction leakage | 0 |

Latency should be recorded but need not be a hard gate because provider/runtime conditions can dominate wall-clock time.

## What can be claimed from the public repository

The checked-in assets can prove that:

- the synthetic industrial evidence is deterministic;
- CEPIO can bind structured and multimodal source-native artifacts to canonical industrial context;
- the runtime can answer deterministic fixture questions with provenance;
- the public challenge surface and evaluation boundary are inspectable;
- no qualification answer key is required for the deterministic fixture tests.

They cannot, by themselves, prove live-model benchmark performance because the qualification evaluator and live-agent runner are intentionally absent.

## Next implementation gate

A live Agent Challenge workflow may be added only after it can retrieve a versioned evaluator from a protected source and demonstrate that the answering process cannot access that evaluator. At that point the public challenge-surface version and private evaluator version should both be recorded in the benchmark report.
