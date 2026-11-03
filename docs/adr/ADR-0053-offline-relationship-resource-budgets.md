# ADR-0053 — Offline relationship resource budgets

Status: bounded qualification increment for #329; no endpoint admission.

## Decision

The offline qualification boundary now enters a scoped SQLite resource budget. Wait at most 50ms for the repository lock, use a 50ms SQLite busy timeout, limit SQLite string/blob/row length to 65,536 bytes (or an already stricter limit), and stop page VM execution at the existing 200,000-instruction ceiling or a 100ms monotonic deadline. Check the deadline again before releasing a result. Bound the serialized UTF-8 page to 262,144 bytes using incremental JSON encoding. Keep public constructor signatures and the ordinary host-local reader behavior unchanged.

The repository lock owns temporary connection settings. Restore the prior length limit, busy timeout and deadline and release the lock on success or failure. Existing source, tenant, classification, property and cursor checks remain authoritative. Resource denial uses the existing generic unavailable response. No timing padding or randomized delay is presented as a confidentiality guarantee.

## Limits and security interpretation

These bounds constrain database result materialization and admitted work; they are NOT an operating-system memory ceiling or hard end-to-end deadline. SQLite checks length during execution, but may allocate native memory before rejecting a row. A progress callback cannot interrupt one long SQLite operation, trusted identity/rights/policy callbacks, Python projection, scheduler pauses or filesystem stalls. The end check discards late results rather than preempting those operations. Connection caches, registry/policy snapshots and cursors require additional accounting. The response byte budget counts this adapter's JSON representation, not HTTP/MCP framing or a differently escaping serializer.

Denied fanout can still change latency and success versus unavailable, despite uniform error text. A global repository revision still invalidates cursors on unrelated mutations. Shared process admission and shared database locks remain interference channels. Dedicated tenant resource partitions, native/process limits, distributed ingress isolation and independent transport/security review are required before remote admission. Synthetic tests do not qualify real source authority, deployed identity or PostgreSQL.

## Validation

Adversarial tests cover contention and recovery, oversized subject/neighbor values, UTF-8 aggregate response overflow, stricter preexisting limits, VM deadline interruption, late-result rejection and cleanup. A synthetic 0/600/2,000 source-denied-link sweep records VM instructions, elapsed time, outcome and traced Python memory. It intentionally preserves evidence of residual leakage rather than asserting constant time. Existing authenticated REST/MCP and source-aware paging tests remain required, followed by repository CI, compatibility, quality, security and governance gates.

No production endpoint, deployment, live PI/SAP credential use, writeback, new cloud resource, paid inference, customer data or Labs intellectual property is introduced. #329 stays open and release/scorecard claims do not change.
