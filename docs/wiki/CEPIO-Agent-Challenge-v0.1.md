# CEPIO Agent Challenge v0.1

## Purpose

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
| --- | ---: |
| Answer correctness | >= 80% |
| Evidence coverage | 100% |
| Structurally unsupported claims | 0 |
| Identity resolution | >= 95% |
| Median CEPIO tool calls | <= 8 |
| Semantic abstraction leakage | 0 |

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

The agent ends with a `final` message whose answer contains human-readable text, canonical refs, scalar values, supported claims, and confidence. No evaluator fields are sent to the child process.

## CI behavior

`make agent-challenge` runs the deterministic reference harness as a regression gate. This validates infrastructure only. A live model should be run as a separate controlled benchmark job or provider environment with the required model credentials. The same questions, tools, evaluator and metrics are reused unchanged.

## Interpretation

A strong result is not merely high question accuracy. The target CEPIO behavior is that the model reaches correct operational conclusions, every industrial claim is grounded in CEPIO evidence, entity identity remains canonical, cross-modal evidence is discoverable, tool usage is efficient, and the model never needs the source-system schema.

That is the threshold at which CEPIO starts demonstrating value as an Industrial AI semantic operating layer rather than only an ontology runtime.
