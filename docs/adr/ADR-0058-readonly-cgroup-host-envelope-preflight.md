# ADR-0058 — Read-only cgroup host resource-envelope preflight

**Status:** proposed offline qualification adjunct for [#329](https://github.com/faizrten/CEPIO/issues/329). No production service, deployment or new permissions.

## Decision

Add a minimal provider-neutral, **host-owned** cgroup-v2 snapshot inspector
(`relationship_host_preflight.py`). It reads `cgroup.type`, `memory.max`,
`memory.current`, `pids.max`, `pids.current` and `cpu.max` from an
explicit local cgroup directory supplied by the trusted operator. It compares
the reported kernel ceilings to a separately host-owned upper-bound policy for
memory bytes, PID count and CPU cores.

The inspector is **not called by REST/MCP/SDK**. It never creates a worker,
sets rlimits, configures cgroups, grants source/tenant access, deploys anything,
approves an Action, or modifies repository/registry state. It is a prerequisite
evidence collector for future deployment verification, not a production
admission authority. Every output retains `production_qualified=false`.

A candidate requires readable cgroup-v2 type, finite positive configured
memory, PID and CPU quotas within host-owned ceilings, and current usage below
memory/PID limits. Values `max`, missing/invalid fields, exhausted limits,
incomplete CPU quota and excessive ceilings fail closed. Local reads are limited
to 256 bytes per file. The tests use only temporary synthetic files and
cannot prove a real host actually enforces the reported limits.

## Why

ADR-0057 proved Linux offline process failure containment using test-supervisor
resource limits, but not production limits installed before interpreter
startup, container/cgroup quotas or process-tree controls. A validated,
repeatable **read-only** check is useful before authorizing a real host
integration. Reuse CEPIO's existing relationship query boundary. Do not
create a second worker engine or cloud service just for a preflight.

## What passing does not prove

A cgroup snapshot is point-in-time and host-local. It does not prove that
CEPIO workers are members of that cgroup, that the path is authorized,
unmodified or complete, that ancestors have correct limits, that processes
can't escape confinement, that memory is isolated by tenant, or that the
launcher sets limits *before* importing Python and handling any request.

It also does not qualify real host CPU fairness, disk/I/O bandwidth,
parent/queue memory, PID namespaces, container security, distributed ingress,
restart/backoff, user identity, authentic source rights, privacy of denied
fanout, real PI/SAP connectors or PostgreSQL production adapters. None of
these are waived when the snapshot is within local bounds.

## Verification and governance

`tests/test_relationship_host_preflight_v01.py` exercises valid synthetic
limits, missing/unbounded/excessive ceilings, invalid values, exhausted
usage, bounded reads, and immutable non-authoritative responses. GitHub CI,
quality/coverage, architecture, compatibility, security, CodeQL, governance
and publication checks remain required before merge.

The full production gate in #329 remains open. A later, separately approved
host/launcher integration must bind the cgroup check to actual process
membership, source authentication, per-tenant isolation and workload
observability. No Azure resources, paid inference, customer data, release
claims or permissions are changed in this ADR.
