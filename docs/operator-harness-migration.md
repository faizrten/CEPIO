# Existing Operator migration to Microsoft Agent Framework Harness

Founder direction, 9 November 2026: Microsoft Harness remains the default and
existing CEPIO agent applications migrate to it. The first Labs broker migration
is merged separately; this change migrates the existing Core Operator orchestration.

## Installation and compatibility

Install `pip install 'cepio[agent-harness]'`. The extra pins the qualified
`agent-framework-core==1.24.0`. Core-only imports and deterministic services do not
require the Microsoft SDK. Calling the Operator without the qualified SDK raises
an actionable error before gateway discovery; no hidden legacy-runtime fallback.
The development extra installs the SDK so normal CI exercises the real integration.

`ConstrainedOperatorAgent` retains its constructor, synchronous `run`, planner,
gateway, trace, evidence IDs and `OperatorResult` contracts. Nemotron remains an
opt-in planner, with the same model/endpoint restrictions and authorization needs.
The API remains synchronous; do not call it directly inside an active event loop.

## Responsibility and authority

Microsoft Harness and its function-invocation layer own the generic tool loop.
The existing planner proposes typed steps; an internal dispatch function forwards
only the matching, single-use pending proposal to the existing CEPIO gateway.
Every run has a fresh session, trace and evidence collection. Tools, web search,
files, file memory, modes, todos, compaction and background agents are not added.

Internal dispatch does not require a second SDK approval: it preserves the
existing gateway's policy/approval boundary and creates no industrial approval.
The configured gateway must still enforce actor/tenant permissions, human
approval, idempotency and governed Actions on every call. A request is consumed
before gateway invocation, including failures. No approval flags, credentials,
raw repositories or source clients are passed to the planner by this adapter.
The ACCC adapter's separate always-require SDK approval policy is unchanged.

The existing tool-step ceiling remains enforced, with at most one final planner
turn afterward. A denied or unexposed request cannot become evidence. Answers
still pass CEPIO's citation finalizer; invented evidence IDs are rejected.

## Qualification

Focused offline tests use the actual SDK and synthetic transports. They exercise
MCP/REST evidence, stable IDs, forbidden sources, fabricated citations, revoked
gateway permission, tool exhaustion, final-turn completion, SDK mismatch and the
Nemotron planner's existing input/output restrictions. No live model calls,
deployment, new spend, scorecard credit or industrial judgment uplift is implied.
Full CI, dependency/security checks and application-specific live qualification
remain required before release/cutover. The earlier application version remains
the rollback artifact; no persisted records are rewritten.
