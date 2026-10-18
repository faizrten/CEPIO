# ADR-007: Isolated live challenge and deterministic retrieval experiments

Status: Proposed for review with PR #123

## Context

The drilling MVP branch adds synthetic multimodal conformance fixtures and a
live Copilot Agent Challenge workflow alongside existing deterministic CI. Its
workflow files are protected governance paths. External model access requires a
user-scoped Copilot token, and parallel custom tool invocations require reliable
protocol correlation. The first completed untuned run scored 9/10, but its median
13.5 tool calls exceeded the unchanged limit of eight.

## Decision

Keep deterministic conformance and live model evaluation separate. Existing CI
checks remain enforced. Live evaluation uses the repository's existing
COPILOT_GITHUB_TOKEN secret through the isolated child process; credentials are
not committed, included in tool results, or delivered to the model as context.
The empty Copilot session exposes only the existing custom CEPIO tools. The
challenge evaluates synthetic objects and introduces no production action.

Route concurrent requests through one protocol reader and unique request IDs;
preserve CEPIO evidence IDs in every returned result. Drain child stdout and
stderr independently and reap the child on final answer, timeout, or failure.
Retain the strict 120-second challenge deadline.

Improve retrieval through generic canonical-identifier constraints, normalized
identity matching, ambiguity rejection, and actionable invalid-type errors.
Helpers accept runtime objects and query arguments, never evaluator answers or
question-specific branches. Preserve tool schemas, model default, system prompt,
questions, expected answers, and scoring thresholds. Count all model tool calls.
Label new retrieval results as post-baseline experiments and preserve the
original untuned report without replacing or rescoring it.

## Validation and consequences

Transport tests cover parallel out-of-order results, evidence correlation,
protocol failures, buffered bursts, stderr pressure, and child shutdown.
Retrieval tests use independent plant, case, and job fixtures, including
ambiguous aliases, numeric padding, exact identifiers, and type validation.
Run the full existing CI and publish live traces, including failed gates.

The baseline CI at bfde23e passed 250 tests and all existing validation,
packaging, and container checks. The retrieval experiment at afda217 adds seven
independent tests. Windows timing-sensitive baseline failures were recorded
separately and are not grounds to weaken CI or benchmark thresholds.

The live benchmark is a small synthetic experiment. Structural citation checks
do not establish entailment or independent diagnostic causality. A later
benchmark version may address those limitations; this decision does not change
the frozen v0.1 evaluator or claim broad generalization from one model run.
