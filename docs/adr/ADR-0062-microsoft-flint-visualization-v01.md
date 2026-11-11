# ADR-0062 — CEPIO-owned visualization contract; replaceable Flint compiler

- **Status:** Proposed; M0–M2 development qualification only
- **Date:** 2026-11-11
- **Risk:** HIGH (protected OSS register plus new GitHub evaluation workflow)
- **Publication:** PUBLIC — generic contracts and explicitly synthetic evidence only

## Context and decision

Microsoft Flint can compile meaningful charts, but CEPIO must own its evidence, authorization, method and decision records. [ADR-0061](ADR-0061-open-source-dependency-resilience.md) forbids turning third-party UX libraries into the canonical system of record.

1. Register Microsoft Flint as `evaluation`, version `flint-chart@1.0.1`, under preliminary MIT license check and security/lock restrictions. Do not mark as approved.
2. Build host-only `cepio.visualization/0.1` with case, tenant, actor, evidence version and SHA hashes retained by CEPIO, and bounded Flint-only inline datasets and chart intent. Fail closed on missing or revoked authorization; do not expose a new public entry point or customer connector.
3. Demonstrate three separate unit-correct synthetic K-201 line charts via actual optional Flint compile and validate calls in an isolated Node evaluation job; retain native Vega-Lite specs and interaction intents.
4. Provide a CEPIO-owned portable Vega-Lite fallback specification, keeping decision/evidence history independent of Flint. Do not claim that chart export equals a customer-ready renderer.
5. No Azure mutation, paid model call, user authentication change, production deployment, or LLM-mediated data access.

## Trade-offs and remaining qualification

Prefer small, replaceable visualization infrastructure over a full Data Formulator fork, hosted MCP server or a permanent Flint requirement in CEPIO Core. Exact direct package pin is present, but the transitive npm lock, notices, security review, browser sandbox, CSP, authentic enterprise provenance and replay/abstention qualifications remain production blockers. Synthetic hashes do not prove external measurement authenticity.

## Verification and rollback

Run the Python negative tests and isolated Node Flint compilation job. Existing CI, governance, security and CodeQL must also pass before merge. The change is reversible by a normal PR revert and has no runtime deployment or storage migration. No scorecard or release gate change is claimed.
