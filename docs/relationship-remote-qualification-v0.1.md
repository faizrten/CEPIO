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
| Request pressure | Four concurrent calls and bounded per-actor/global process-local windows, saturation/reset tests | Distributed limits, byte-size/native-memory isolation and operational load qualification |
| Denied cardinality | SQL projection has no hidden counts or raw IDs; work-capped reads and uniform boundary errors | Timing/availability noninterference, including denied fanout and global revision activity, remains unqualified |
| Production repository | Unsupported backends fail closed | PostgreSQL/repository qualification #283 remains separate |

The issue stays open. The existing synthetic K-201 Studio section remains independent and gains no backend integration. See [ADR-0052](adr/ADR-0052-offline-relationship-host-protocol-qualification.md). Exact-head local and CI results belong in the governed PRs.

## Resource-budget increment

The offline boundary additionally bounds repository lock wait (50ms), SQLite busy wait (50ms), SQLite row/string/blob size (65,536 bytes), page VM work (200,000 instructions or a 100ms monotonic deadline) and its UTF-8 JSON page representation (262,144 bytes). Late results are discarded and temporary connection settings are restored. Ordinary host-local reads retain their existing contract. See [ADR-0053](adr/ADR-0053-offline-relationship-resource-budgets.md) for exact scope and limitations.

These are resource defenses, not constant-time behavior or native-memory/process isolation. Denied fanout can still distinguish success from budget exhaustion. Trusted callbacks and individual SQLite operations are not preemptible; wire framing and ingress body limits remain transport obligations. The synthetic denied-fanout sweep records residual timing/availability differences. Global revision churn, shared admission, distributed ingress and independent production qualification remain open.
