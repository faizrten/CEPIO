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

CEPIO separates the **public challenge surface** from the **private qualification evaluator**.

The public repository may contain:

- synthetic industrial datasets;
- public challenge questions;
- CEPIO tool schemas and gateway contracts;
- deterministic retrieval/runtime helpers;
- reference conformance and acceptance tests;
- public deterministic golden questions used to validate fixture plumbing;
- reporting schemas and benchmark protocol documentation.

The public repository must not contain the qualification answer key used to claim live-agent benchmark performance.

A live Agent Challenge evaluator must be supplied at execution time from a controlled source outside the public repository, for example a protected CI secret-backed artifact, a private benchmark repository or another governed evaluation service.

## Public reference evaluation versus qualification

A public reference evaluator may exist for harness self-tests, but its result is explicitly **not** a live-agent qualification result because any public answer key is inspectable and gameable.

The terminology is:

```text
Public conformance evaluation
  -> deterministic
  -> reproducible
  -> suitable for CI plumbing and CEPIO runtime validation
  -> not evidence of model generalization

Private qualification evaluation
  -> answer key unavailable to the answering process and public repository
  -> suitable for controlled external-agent benchmark claims
```

## Agent isolation contract

For a qualification run, the answering process receives only:

- the natural-language question;
- approved CEPIO tool schemas;
- results returned by CEPIO tools it explicitly invokes;
- the final-answer schema.

It must not receive:

- benchmark question identifiers when those reveal evaluator structure;
- expected references or scalar values;
- ground-truth scenario hints;
- evaluator state;
- filesystem or raw-dataset access;
- direct SQL/dataframe/source-system access;
- private benchmark artifacts.

The evaluator scores the answer only after the answering process completes.

## Workflow consequence

The public CEPIO repository does not enable a live Agent Challenge workflow merely by adding the synthetic testbed. A live workflow may be introduced only when it retrieves the qualification evaluator from an approved private source and demonstrates that the answering process cannot access it.

Feature-branch-specific workflow triggers must not be promoted to `main` as permanent benchmark infrastructure.

## Publication consequence

Synthetic datasets and public questions can be intentionally published when they improve interoperability, adoption or deterministic validation. Qualification answer keys, protected benchmark corpora and differentiated industrial reasoning remain outside the public repository unless publication is explicitly chosen and the benchmark is no longer represented as hidden or qualification-grade.

## Consequences

### Positive

- public CEPIO remains reproducible without making benchmark-integrity claims it cannot support;
- live-agent results can be interpreted as actual qualification evidence rather than repository memorization;
- evaluation IP has a clear publication boundary;
- the same public CEPIO gateway can support both deterministic conformance and private qualification.

### Costs

- live qualification requires separate evaluator distribution and CI plumbing;
- public CI cannot independently reproduce a private qualification score without authorized evaluator access;
- benchmark versioning must track both public challenge-surface version and private evaluator version.

## Non-goals

This ADR does not define a specific private storage provider, model vendor, benchmark leaderboard or production credential mechanism. Those are deployment concerns constrained by this isolation boundary.
