# ADR 0043 Full generated OpenAPI compatibility gate

Status: Proposed

Date: 2026-10-24

## Context

The accepted public route YAML and conservative generated-schema checks do not
fully classify newly required inputs, bounds and response guarantees. Updating a
head baseline must not conceal a breaking change from the immutable PR base.
Management also needs a separate complete declared HTTP contract comparison.

## Decision

Extend the existing quality-compatibility lane with checksum-pinned oasdiff
1.34.0, comparing complete generated application and Management contracts from
isolated base/head processes. Base source comes from the exact Git commit, and
both processes use in-memory test configuration without starting a service.
Commit reviewed complete application and Management snapshots, require head
generation to match, and compare against the immutable base snapshot thereafter.
This detects dependency-driven schema drift that regeneration of both sources
with today's dependency graph alone could hide. Initial introduction uses an
explicitly labelled base-source bootstrap because no historical full snapshot
exists; it is not a recreation of an old released dependency graph.
Block ERR/WARN findings and any changed authentication requirement/scheme,
Authorization header or stable operation ID. Prohibit remote schema references.
Run positive/negative comparator controls first and retain full local reports.
Tool outages, invalid/missing output and base export failures are failures.

Existing route, SDK, ontology, security, migration and governance checks remain
enforced. The new semantic gate has no automatic waiver via a rewritten YAML or
generic interface-migration declaration. A necessary breaking API change needs
an explicit versioned contract and separately reviewed transition.

## Consequences and validation

Declared schemas gain semantic compatibility coverage without a paid comparison
service or uploading specifications to a third party. Three deterministic unit
tests cover security/header/operation identity preservation; every CI run also
executes comparator controls for compatible optional inputs and incompatible
required inputs, bounds, response guarantees and authentication removal.
Runtime authorization, untyped responses, undocumented errors, MCP semantics and
deployed artifact qualification remain separate obligations. Production stays
on HOLD; no deployment, identity/permission change or infrastructure is added.

Upstream references: [oasdiff 1.34.0](https://github.com/oasdiff/oasdiff/releases/tag/v1.34.0)
and [breaking-change policy](https://github.com/oasdiff/oasdiff/blob/v1.34.0/docs/BREAKING-CHANGES.md).
