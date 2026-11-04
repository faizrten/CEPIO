# ADR-0057 — Linux process-memory and failure-containment qualification

Status: synthetic offline qualification for #329. No production worker, endpoint or deployment is installed.

## Decision

Exercise the existing source-aware `RelationshipQualificationBoundary` in separate Linux child interpreters using a fixed, test-only fixture and supervisor. Reuse the existing SQLite repository, policy, source-rights, pagination and property projection contracts. Do not introduce a generic execution service or rebuild the query engine.

The child installs hard and soft limits before importing/building CEPIO: 1 GiB virtual address space (`RLIMIT_AS`), five cumulative CPU seconds (`RLIMIT_CPU`), 64 descriptors and zero core-dump bytes. Limits include the fixture's policy/registry construction and query native allocations after installation. Setup failure never admits a worker. Python/interpreter/site startup precedes these limits; production enforcement before exec needs external OS/container controls. Address-space limits are not RSS quotas, CPU fairness or disk/I/O isolation. See Python's [resource semantics](https://docs.python.org/3/library/resource.html).

A fixed absolute Python executable and test fixture run without a shell, with isolated Python import mode and a minimal environment. No parent credential environment is inherited. Dedicated synthetic tenant databases are created only in pytest temporary directories. Linux is required; unsupported hosts skip qualification explicitly and never substitute an unbounded worker.

The test supervisor bounds request frames to 4,096 bytes and response frames to 262,144 bytes, discards stderr rather than buffering it, and enforces read deadlines. It terminates the owned process group and reaps the direct child on timeouts, malformed/oversized responses, crashes or unavailable results. A failed worker instance remains disabled; caller retries cannot silently create a replacement or reset its admission state. Successful workers persist across pagination. This is not a distributed queue, production restart policy or process-tree sandbox.

## Required evidence

Linux tests must prove successful source-aware pagination under the installed limits; denial of oversized Python, libc and SQLite allocations; CPU exhaustion causing OS termination (EOF, not the supervisor timeout); forced termination of a sleeping resolver; crash/oversized-output cleanup; bounded input and discarded stderr; source-revocation/caller-tenant rejection; and continued reads by a separate tenant worker after another worker fails. Record installed limits and observed peak RSS without treating one fixture's RSS as a production capacity guarantee. The SQLite native-allocation probe further lowers its address-space ceiling to current virtual size plus 64 MiB (never above 1 GiB), then requests a 128 MiB blob. This remains below SQLite's compiled value-size limit, so a size-validation failure cannot masquerade as OS memory containment.

The native tests are in normal repository pytest CI on Linux. Local Windows syntax/lint/skip results are not Linux memory evidence. Existing required CI, quality, security, compatibility, coverage and governance gates still apply. No workflow exception or gate weakening is needed.

## Remaining production gaps

- Qualify the real production launcher and hosting environment, including limits before interpreter startup, whole-process-tree/cgroup memory and PID controls, CPU fairness and disk/I/O quotas. A trusted fixture under `rlimit` is not confinement of malicious code, filesystem or network access.
- Admission across replicas, bounded transport parsing/framing, queued requests, parent-process memory, global capacity and restart/backoff budgets remain deployment-composition obligations. The test supervisor is not imported into CEPIO runtime.
- Policy/registry and native allocations are contained in the tested child envelope, but production fixture size, adapter/cache behavior and useful capacity under that envelope still require evidence. Shared-resource latency and same-tenant hidden-fanout/revision noninterference remain open.
- Dedicated imports, authentic source/derivative lineage and revocation authority, deployed identity, production adapter and independent transport/security review remain required.

#329 remains open. Production endpoints, deployment, live PI/SAP credentials and production writeback remain gated. No new Azure, paid inference, customer data, protected Labs logic or release/scorecard advancement.
