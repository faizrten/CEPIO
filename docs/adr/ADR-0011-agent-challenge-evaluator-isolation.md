# ADR-0011 — Agent Challenge evaluator isolation

- **Status:** Accepted
- **Date:** 2026-10-18

## Context

CEPIO needs two different kinds of industrial-AI validation:

1. deterministic public conformance fixtures that prove CEPIO identity, graph, temporal, provenance, API and multimodal behavior; and
2. model qualification benchmarks that test whether an external AI agent can reason through the CEPIO tool surface without access to expected answers.

The first category benefits from complete reproducibility in the public repository. The second loses validity if its qualification answer key is published in the same repository as the questions and agent code.

A file named `hidden-evaluator.json` is not meaningfully hidden when it is committed to a public repository. Process-level isolation during one run is useful, but it does not protect benchmark integrity from repository readers, model training data, pre-run inspection or benchmark-specific tuning.

## Decision

CEPIO separates the **public conformance surface** from the **private qualification system**.

The public repository may contain:

- synthetic industrial datasets;
- deterministic public golden questions used to validate fixture plumbing;
- CEPIO tool schemas and gateway contracts;
- deterministic runtime/acceptance helpers;
- public API/SDK/MCP conformance tests;
- reporting schemas and benchmark-method summaries.

The public repository must not contain qualification answer keys, unseen benchmark corpora, benchmark-specific model transport/tuning code or scoring material used to claim live-agent performance.

Live Agent Challenge experimentation is maintained in the protected `faizrten/CEPIO-Labs` boundary. A qualification evaluator must be supplied at execution time from a controlled source outside the public repository and outside the answering process.

## v0.1 disclosure and migration

Agent Challenge v0.1 was committed publicly through CEPIO PR #123, including its evaluator and live-runner implementation. That disclosure cannot be reversed by later deletion from the current tree.

Therefore:

- v0.1 is **retired as a hidden qualification benchmark**;
- its historical experiment/provenance record is maintained in CEPIO Labs;
- public CEPIO removes the active v0.1 evaluator/live-agent implementation from the current product tree;
- any historical v0.1 result must be described as a disclosed experiment, not unseen model qualification;
- Agent Challenge v0.2 must use a fresh unseen corpus/evaluator that has never been committed to public CEPIO.

## Public reference evaluation versus qualification

A public reference evaluator may exist for deterministic harness self-tests, but its result is explicitly **not** a live-agent qualification result because any public answer key is inspectable and gameable.

```text
Public conformance evaluation
  -> deterministic
  -> reproducible
  -> suitable for CI plumbing and CEPIO runtime validation
  -> not evidence of model generalization

Private qualification evaluation
  -> answer key unavailable to the answering process and public repository
  -> unseen corpus/evaluator under controlled access
  -> suitable for controlled external-agent benchmark claims
```

## Agent isolation contract

For a qualification run, the answering process receives only:

- the natural-language question;
- approved CEPIO tool schemas;
- results returned by CEPIO tools it explicitly invokes;
- the final-answer schema.

It must not receive:

- expected references or scalar values;
- ground-truth scenario hints;
- evaluator state;
- filesystem or raw-dataset access;
- direct SQL/dataframe/source-system access;
- private benchmark artifacts.

The evaluator scores the answer only after the answering process completes.

## Workflow consequence

The public CEPIO repository does not host or automatically run live Agent Challenge qualification workflows. Model-specific benchmark execution belongs in CEPIO Labs or another governed private evaluation service.

## Publication consequence

Synthetic datasets and deterministic conformance assets can be intentionally published when they improve interoperability, adoption or runtime validation. Qualification answer keys, unseen benchmark corpora, scoring logic and differentiated benchmark-specific reasoning remain outside the public repository unless publication is explicitly chosen and the benchmark is no longer represented as hidden or qualification-grade.

## Consequences

### Positive

- public CEPIO remains reproducible without making benchmark-integrity claims it cannot support;
- live-agent results can be interpreted as actual qualification evidence rather than repository memorization;
- evaluation IP has a clear publication boundary;
- the same public CEPIO gateway can support both deterministic conformance and private qualification.

### Costs

- live qualification requires separate evaluator distribution and CI plumbing;
- public CI cannot independently reproduce a private qualification score without authorized evaluator access;
- benchmark versioning must track both public tool/fixture dependencies and private evaluator/corpus versions.

## Non-goals

This ADR does not define a specific private storage provider, model vendor, benchmark leaderboard or production credential mechanism. Those are deployment concerns constrained by this isolation boundary.
