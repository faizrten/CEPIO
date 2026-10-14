# CEPIO Capability Benchmark — v0.2

Scale: **0 absent, 1 concept, 2 prototype, 3 usable reference implementation, 4 production-grade, 5 platform-grade.**

This is a capability benchmark, not a claim of parity with Palantir. Palantir has years of production hardening, tooling and operating experience that CEPIO v0.2 does not yet possess.

| Capability | v0.1 | v0.2 | Target | Next engineering move |
|---|---:|---:|---:|---|
| Typed objects | 2 | 3 | 5 | generated domain models/interfaces |
| First-class relationships | 2 | 3 | 5 | cardinality, temporal indexes, graph backend |
| Interfaces/capabilities | 1 | 2 | 5 | formal interface ontology + inheritance |
| Events/state/time | 2 | 3 | 5 | temporal state projection/event streams |
| Functions | 2 | 3 | 5 | execution lineage, packaging, distributed runtime |
| Actions | 2 | 3 | 5 | transactional adapters, compensation execution |
| Decisions | 1 | 3 | 5 | outcome feedback + causal learning |
| Authorization | 1 | 3 | 5 | Entra/OPA/Cedar integration, policy administration |
| Property-level filtering | 0 | 3 | 5 | field lineage + dynamic ABAC |
| Audit | 0 | 3 | 5 | tamper-evident/WORM storage, retention controls |
| Optimistic concurrency | 0 | 3 | 5 | distributed transaction semantics |
| Idempotency | 0 | 3 | 5 | distributed idempotency service |
| Provenance/lineage | 0 | 1 | 5 | source/transformation lineage model |
| Ontology versioning | 1 | 2 | 5 | migrations + compatibility gates |
| API | 2 | 3 | 5 | richer query/filter/action contracts |
| Typed SDK | 1 | 2 | 5 | generated Python/.NET/TypeScript SDKs |
| MCP/agent tools | 0 | 2 | 5 | production MCP transport + tool governance |
| Graph traversal | 2 | 3 | 5 | indexed graph query/planner |
| Search | 0 | 0 | 5 | lexical + semantic + vector hybrid |
| Writeback | 1 | 2 | 5 | live adapters + reconciliation |
| Application framework | 0 | 1 | 4 | reliability, margin, turnaround apps |
| Standards mappings | 1 | 1 | 4 | OSDU/15926/CFIHOS/ISA-95/FIBO packs |
| CI/CD ontology-as-code | 2 | 3 | 5 | breaking-change detection + migrations |
| Observability | 0 | 1 | 5 | runtime metrics, traces, action/policy telemetry |
| Multi-tenancy | 0 | 0 | 4 | namespace, tenant, policy boundaries |
| Scale/performance | 0 | 1 | 5 | load model, distributed backend, SLOs |

## v0.2 acceptance test

The release is successful when one executable scenario can:

1. resolve a refinery KPI;
2. traverse to the hydrocracker and affected compressor;
3. inspect operational events;
4. calculate risk and production-margin impact;
5. persist a decision recommendation;
6. create a governed work order exactly once under idempotent retry;
7. traverse from that work order to a critical spare and supplier;
8. reject an AI recommender attempting the same execution;
9. preserve an immutable audit record of every action attempt;
10. persist state across SQLite restart.

v0.2 meets this reference acceptance test. Platform parity still requires the production hardening in the roadmap.
