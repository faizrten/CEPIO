# ADR-0054 — Fixed offline relationship tenant partitions

Status: offline resource-isolation qualification for #329; no production routing.

## Decision

Compose the existing source-aware qualification boundary with a fixed host-owned mapping of one to sixteen tenant IDs to existing services, SQLite adapters and authority callbacks. Resolve the authenticated request-local identity once; select only its configured tenant; forward the same captured context to the existing boundary. Caller query fields cannot select a tenant. Unknown tenants fail generically without allocating partitions or consuming a configured tenant's admission window.

Every partition has its own boundary, admission counters/semaphore and reader/cursor cache. Require distinct SQLite connections and database files, checking SQLite's opened path and filesystem identity to reject alias/hardlink sharing. Reject existing foreign tenant bindings at composition. Each partition retains the existing four-active/30-per-actor/120-total-per-minute limits and the resource budgets in ADR-0053. At most sixteen partitions bounds configured state; this is not a dynamic tenant cache or provisioning service.

This uses existing repositories. It creates no graph database, service, source copy, replication worker, authority registry, production route or environment enablement switch. Source/tenant/property policy and current-rights checks remain inside every read.

## Qualification and limits

Synthetic tests verify that tenant A's exhausted quota, actor rotation, occupied admission slots and database lock do not exhaust/block tenant B's configured boundary. A mutation in A's separate file does not invalidate B's cursor; B's own mutations still conservatively invalidate it. Cross-tenant cursors, caller tenant selection, unknown tenant flooding, reused connections/files and foreign bindings fail closed.

Host composition and trusted importers must preserve dedicated repositories throughout their lifetime. Startup inspection is not a database-level tenant/RLS enforcement or continuous attestation; new foreign bindings or out-of-band writes after setup remain production-composition obligations. A mixed database cannot be made isolated merely by wrapping it twice. Existing multi-tenant shared-boundary mode remains unqualified for remote use.

This isolates the named application state and database lock/revision channels in the tested composition. CPU, scheduler, disk, process/native memory and transport queues remain shared. No hard scheduling, process-memory, distributed admission or timing noninterference guarantee follows. Hidden fanout and same-partition hidden mutations still affect timing/availability and cursor validity. Real identity/source authority, production adapter, dedicated import controls, distributed ingress and independent security review remain gates. #329 stays open; no release/scorecard change.

Production endpoints, deployment, live PI/SAP credentials and production writeback remain gated. No customer data, paid inference, new Azure resource or protected Labs intelligence is involved.
