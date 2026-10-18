# CEPIO Agent Challenge v0.1

## Purpose

<<<<<<< HEAD
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
=======
The Agent Challenge tests whether a general-purpose AI agent can answer industrial operational questions by using **only the CEPIO semantic tool surface**. It is deliberately separate from the deterministic Golden Question oracle and from the question-text-only blind baseline.

The experiment asks one product question:

> Can an intelligent model understand and reason over an industrial enterprise through CEPIO without learning the underlying source-system implementation?

## Isolation contract

The answering process receives only the natural-language question, the CEPIO tool schemas, and results returned by CEPIO tools it explicitly invokes. It does **not** receive the benchmark question ID, expected refs or values, ground-truth scenario hints, evaluator state, filesystem access, SQL access, dataframe access, or raw source-system connectors.

The evaluator owns the expected answers and scores the final answer only after the agent has finished. The evaluator files live in the repository for reproducibility; "hidden" means hidden from the answering process, not cryptographically secret from repository readers.

## Bounded CEPIO tool surface

Agent Challenge v0.1 exposes eight semantic tools: `search_objects`, `get_object`, `get_relationships`, `get_events`, `resolve_identity`, `get_evidence`, `query_measurements`, and `get_provenance`.

Large/raw multimodal payloads remain source-native. The agent receives CEPIO semantic bindings, summaries, provenance and source references rather than direct file/database access.

The strict runner adds token-aware search normalization so industrial identifiers such as `Mud Pump 2`, `mud-pump-02`, and numeric rig identifiers are ranked by semantic tokens rather than substring coincidences.

## Challenge pack

The initial challenge contains 10 compositional questions across L2-L5 difficulty. They combine canonical identity resolution, relationship traversal, NPT/failure causality, maintenance state, post-maintenance condition evidence, well-control events, geospatial context, proactive maintenance and multimodal evidence retrieval.

The 10 questions are additional to the 30 Golden Questions and are not used to train or tune the answering process during a run.

## Scoring

| Metric | External-agent gate |
>>>>>>> origin/main
| --- | ---: |
| Answer correctness | >= 80% |
| Evidence coverage | 100% |
| Structurally unsupported claims | 0 |
| Identity resolution | >= 95% |
| Median CEPIO tool calls | <= 8 |
| Semantic abstraction leakage | 0 |

<<<<<<< HEAD
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
=======
Latency is recorded but is not a hard v0.1 gate because the provider/runtime environment can dominate wall-clock time.

"Unsupported claims" in v0.1 is a structural check: each claim must cite valid CEPIO tool-call IDs. A later evaluator version can add model-based entailment checking between claims and retrieved evidence.

"Semantic abstraction leakage" counts attempts to call tools outside the approved CEPIO gateway. The challenge process has no direct-source tool, so SQL/filesystem/source-system access cannot be used legitimately.

## Reference harness versus real AI result

`--agent reference` validates the benchmark plumbing and must not be reported as AI performance. It is a deterministic tool-using reference agent that proves the challenge data is answerable through CEPIO, the tool schemas are sufficient, hidden-answer isolation works, scoring works, and the execution trace is complete.

A real AI result uses `--agent external` with an external process implementing the JSONL protocol.

Run the canonical strict harness with:

```bash
PYTHONPATH=src python scripts/run_agent_challenge_strict.py \
  --agent external \
  --agent-command "YOUR_AGENT_PROCESS"
```

For each question, CEPIO sends one JSON line containing the question, tool schemas and final-answer schema. The agent may emit a tool request such as:

```json
{"type":"tool_call","id":"agent-1","name":"search_objects","arguments":{"query":"Rig-07"}}
```

CEPIO responds with a semantic tool result and a CEPIO `tool_call_id`:

```json
{"type":"tool_result","request_id":"agent-1","tool_call_id":"tc-01","result":[]}
```

Concurrent Copilot handlers share one stdin reader/dispatcher. Each request has a unique ID;
results are routed by `request_id`, including out-of-order responses, and preserve the
CEPIO `tool_call_id` as `cepio_tool_call_id` in model-visible evidence. EOF or invalid
correlation fails pending calls explicitly. Reader shutdown never waits for an open
parent stdin. The harness drains stdout through one line reader (including buffered
bursts) and stderr separately, then reaps the child and closes its pipes on every exit.
The strict challenge deadline remains 120 seconds; model, prompt, questions, evaluator,
and approved tool schemas are unchanged.

The agent ends with a `final` message whose answer contains human-readable text, canonical refs, scalar values, supported claims, and confidence. No evaluator fields are sent to the child process.

## CI behavior

`make agent-challenge` runs the deterministic reference harness as a regression gate. This validates infrastructure only. A live model should be run as a separate controlled benchmark job or provider environment with the required model credentials. The same questions, tools, evaluator and metrics are reused unchanged.

## Interpretation

A strong result is not merely high question accuracy. The target CEPIO behavior is that the model reaches correct operational conclusions, every industrial claim is grounded in CEPIO evidence, entity identity remains canonical, cross-modal evidence is discoverable, tool usage is efficient, and the model never needs the source-system schema.

That is the threshold at which CEPIO starts demonstrating value as an Industrial AI semantic operating layer rather than only an ontology runtime.


## Post-baseline retrieval efficiency experiment

The first untuned live run at `bfde23e` scored 9/10 with median 13.5 tool calls;
its report remains unchanged. Subsequent retrieval changes are benchmark-informed
experiments and must not be described as untuned results.

The existing tools now share deterministic retrieval helpers in
`cepio.agent_retrieval`. Canonical identifiers mentioned in search text constrain
results to matching objects and references, instead of matching separate numeric
tokens across unrelated fields. Identity resolution accepts delimiter and numeric
padding variations in canonical IDs and display names, preserves exact alias
precedence, and rejects ambiguous matches. Invalid object-type filters return an
explicit error listing runtime object types, avoiding unexplained empty results.
Helpers receive runtime objects and query arguments only; they do not read questions,
expected answers, or model output. Independent fixtures test different plant, job,
and case identifiers from the frozen dataset.

These changes preserve tool names, descriptions, parameter schemas, and result
shapes for successful calls. Retrieval behavior has changed, so later model runs
are comparisons against the preserved baseline, not repetitions of an identical
retrieval system. Questions, expected answers, scoring thresholds, system prompt,
model default, and the 120-second challenge timeout remain frozen. Every model
call still counts; no caching or deduplication discounts the efficiency metric.
>>>>>>> origin/main
