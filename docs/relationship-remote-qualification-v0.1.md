# Relationship remote qualification — offline v0.1

This increment closes testable host/protocol gaps under [#329](https://github.com/faizrten/CEPIO/issues/329). It **does not enable or admit a production endpoint**.

`RelationshipQualificationBoundary` requires the existing source-aware reader, a trusted request-local identity provider and current source-access resolver. It captures authenticated identity once per invocation, rejects caller identity/tenant/source declarations, revalidates copied query models, uses the existing property policy, and returns a uniform unavailable error for denied subjects, stale cursors, source revocation and internal resolver failures. Its fixed limits bound active calls and per-process admission state. Resolver exceptions and cause text are not returned to clients.

The REST/MCP harness exists only in `tests/test_relationship_protocol_qualification_v01.py`. Its REST dependency uses `get_actor_context`; MCP uses `MCPActorBindingMiddleware` and `ContextVarActorProvider`. Ephemeral RSA-signed tokens are verified through the existing Entra validator, with local key discovery replacing network access. It exercises real MCP initialize/tools-list/tools-call JSON-RPC and shared REST-to-MCP cursor continuation. No real credential, customer data, paid inference, connector or new Azure resource is involved.

Four active calls and thirty attempts per actor/tenant per minute are allowed, subject to a global 120-attempt per-process window. Saturation fails closed; no principal eviction can reset an exhausted window. These admission limits supplement the SQLite VM cap. They do not make query latency independent of denied graph size, prove bounded SQLite/native memory for arbitrarily large payloads, or replace ingress/distributed resource isolation.

## Qualification register

| Gap | Evidence in this series | Remaining production gate |
| --- | --- | --- |
| Source-use propagation | Mandatory current rights for all bound subject/link/neighbor sources; current expiry and cursor invalidation | Verify complete source/derivative bindings and authentic rights/revocation authority |
| Host identity and tenancy | Signed-token tests verify signature, audience, issuer, tenant, expiry; spoofed headers/payloads denied; concurrent principals isolated | Qualify actual deployment identity configuration without live PI/SAP access |
| REST/MCP conformance | Real in-process REST and MCP Streamable HTTP query/pagination/error tests, shared cursor semantics | Independent production transport/security review and separately admitted endpoint |
| Request pressure | Bounded lock/busy wait, SQLite row/VM and response budgets; fixed tenant partitions separate admission/cursor state, with saturation and contention tests | Native/process memory and CPU/disk isolation, distributed ingress and operational load qualification |
| Denied cardinality | SQL projection omits hidden counts/IDs; resource-capped reads; fanout sweep records residual leakage; dedicated files isolate cross-tenant revision churn | Same-partition hidden fanout/revision timing and availability noninterference remain unqualified; dedicated import discipline must be verified |
| Production repository | Unsupported backends fail closed | PostgreSQL/repository qualification #283 remains separate |

The issue stays open. The existing synthetic K-201 Studio section remains independent and gains no backend integration. See [ADR-0052](adr/ADR-0052-offline-relationship-host-protocol-qualification.md). Exact-head local and CI results belong in the governed PRs.

## Resource-budget increment

The offline boundary additionally bounds repository lock wait (50ms), SQLite busy wait (50ms), SQLite row/string/blob size (65,536 bytes), page VM work (200,000 instructions or a 100ms monotonic deadline) and its UTF-8 JSON page representation (262,144 bytes). Late results are discarded and temporary connection settings are restored. Ordinary host-local reads retain their existing contract. See [ADR-0053](adr/ADR-0053-offline-relationship-resource-budgets.md) for exact scope and limitations.

These are resource defenses, not constant-time behavior or native-memory/process isolation. Denied fanout can still distinguish success from budget exhaustion. Trusted callbacks and individual SQLite operations are not preemptible; wire framing and ingress body limits remain transport obligations. The synthetic denied-fanout sweep records residual timing/availability differences. Global revision churn, shared admission, distributed ingress and independent production qualification remain open.

## Fixed tenant-partition qualification

`RelationshipQualificationPartitions` accepts a fixed trusted host mapping of at most sixteen tenants to existing dedicated SQLite repositories and authority callbacks. It captures identity once, rejects unknown tenants without dynamic allocation, and gives each configured tenant separate admission and cursor state. Shared connections/files and existing foreign bindings are rejected. Synthetic tests establish separation of quota exhaustion, lock contention and cross-file revision invalidation. See [ADR-0054](adr/ADR-0054-fixed-offline-relationship-tenant-partitions.md).

This closes those application-state interference cases only in the dedicated-repository composition. The host must maintain tenant-exclusive imports; startup checks do not enforce future writes. Shared CPU/disk/native memory, distributed ingress, same-tenant hidden fanout/revision leakage and real production composition remain unqualified. No production router or endpoint is installed.

## Accounted cursor retention

The offline boundary also opts into a 256 KiB accounted Python cursor budget, alongside the existing 1,024-entry and ten-minute limits. Expired entries are reclaimed on the next read; oldest continuations are evicted under pressure. A continuation too large to retain fails closed. Host-only size diagnostics never enter query responses. [ADR-0056](adr/ADR-0056-accounted-relationship-cursor-retention.md) distinguishes live-structure accounting from allocator, policy/registry, SQLite and native/process memory; those still require process-level qualification.

## Linux process envelope qualification

A test-only Linux supervisor/worker fixture runs the existing source-aware boundary under hard 1 GiB address-space, five-second cumulative CPU, 64-descriptor and zero-core-dump limits installed before CEPIO construction. It tests Python/libc/SQLite allocation failure, OS CPU termination, blocked callbacks, crashes, bounded IPC, disabled failed workers and continued service in a separate tenant process. [ADR-0057](adr/ADR-0057-linux-relationship-process-qualification.md) defines the evidence and limits; Windows skips are not Linux qualification.

This establishes only the tested Linux process envelope. It adds no runtime worker service or production routing. Limits before interpreter startup, process-tree/cgroup controls, parent/queue memory, distributed admission, production restart budgets, CPU fairness and disk/I/O isolation still need deployment-specific qualification. Address space is not RSS, and process separation does not prove timing confidentiality.
