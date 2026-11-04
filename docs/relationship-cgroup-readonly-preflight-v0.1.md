# Relationship host resource ceiling preflight — local read-only v0.1

**Purpose:** make the hosting-resource portion of [issue #329](https://github.com/faizrten/CEPIO/issues/329) measurable before authorizing a remote CEPIO Operational Object Workbench.

Call `inspect_relationship_cgroup(directory, policy)` only from a trusted local
operator or validated deployment preflight. `directory` is a **host-selected
cgroup-v2 path**, never an agent, request body or source-supplied filename.
`RelationshipHostCeilingPolicy` defines maximum memory bytes, PID count and
CPU cores allowed for that isolated workload.

The returned immutable evidence includes observed numeric limits and usage,
stable failure codes, `bounded_candidate` and the mandatory
`production_qualified=false`. A true candidate means **only** that the
synthetic or local cgroup snapshot matched this limited resource policy at one
instant. It never grants remote query access or validates the host itself.

## Negative cases

Missing `cgroup.type`, `memory.max`, `memory.current`, `pids.max`,
`pids.current` or `cpu.max`; unlimited `max` values; invalid, excessive
or exhausted limits; failed/non-ASCII/oversized reads; and unbounded policy
inputs must all fail closed. Reads are limited to 256 bytes per file.

## Still required for real deployment

1. Verify cgroup-v2 mount, process membership and ancestor ceilings from the
   trusted launcher before accepting any request.
2. Prove actual per-tenant worker isolation, parent/queue and entire
   process-tree resource limits, native RSS and CPU/disk/I/O fairness under
   representative workloads.
3. Bind capacity/admission, safe shutdown/restart and ingress framing to the
   existing hosted identity, source-rights and property-policy contracts.
4. Qualify real Azure hosting/Entra access, source lineage, production
   PostgreSQL adapter if selected, and independent transport/security review.

These require a separate authorized implementation and field evidence. The
preflight introduces **no production endpoint or deployment**. See ADR-0058
and the existing Linux process test qualification ADR-0057. It does not
alter v0.5 CONNECT or canonical v1 maturity claims.
