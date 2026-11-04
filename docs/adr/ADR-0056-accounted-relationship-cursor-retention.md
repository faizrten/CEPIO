# ADR-0056 — Accounted relationship cursor retention

Status: offline memory qualification for #329; no production admission. ADR-0055 belongs to the separate ACCC increment.

## Decision

The offline relationship qualification boundary now opts its existing reader into a fixed 256 KiB cursor-retention budget, in addition to the existing 1,024-entry ceiling and ten-minute TTL. Account the ordered mapping, token strings, record tuples and every retained primitive with Python `sys.getsizeof`; count shared references again conservatively. Reclaim expired records on the next read, then evict oldest records until both limits hold. Reject a page whose individual continuation cannot fit; never return an already-evicted token. Enabling the budget clears previous cursor state, and source-authority replacement continues to clear it.

Constructor signatures, tenant/policy/source fingerprints, revision invalidation and ordinary host-local readers remain compatible. New host-only methods configure this budget and inspect its accounted size; query responses expose neither memory figures nor hidden cardinality.

## Meaning and limits

This bounds accounted live Python cursor structures on the tested interpreter. It does not measure allocator arenas, resident/native memory, SQLite caches, policy/registry copies, transient materialization or the whole process. Expired state is reclaimed on subsequent reads; idle state is still bounded by the byte/count ceilings. Earlier memory can remain reserved by the allocator after eviction. A separate operating-system process qualification is required for total address space, CPU exhaustion and blocking trusted callbacks. No native RSS guarantee follows from `getsizeof` or `tracemalloc`.

Synthetic tests exercise long continuation IDs that defeat a count-only cache, ordinary sustained cursor creation, TTL reclamation with live continuations preserved, source reconfiguration, and a single over-budget continuation. Existing source, query, protocol, resource and partition suites remain required alongside full CI/quality/security/governance checks.

#329 remains open. No production route, deployment, live PI/SAP credentials, writeback, new Azure, paid inference, customer data, protected Labs logic or scorecard change.
