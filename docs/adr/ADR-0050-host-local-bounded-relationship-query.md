# ADR-0050 — Host-local bounded relationship paging

Status: proposed implementation increment for issue #329; remote exposure remains blocked.

## Context

M1 fetches relationship sets before applying a scan budget. That host-local reference cannot establish bounded database reads, relationship classification or tenant-safe remote access. Pending sovereignty changes (#305/#307/#308) are not dependencies of this increment.

## Decision

Reuse existing Core application identity, policy projection, objects, relationships and SQLite persistence. Add a host-composed query reader with a strict identity-free payload and an additive SQLite adapter. Trusted importers bind explicit tenant/classification/source-use metadata to current versions/payloads; mutations revoke bindings. No canonical ontology concept, proprietary Industry IQ, graph database, customer mapping or new hosted surface is introduced.

Use indexed, ordered keyset queries with SQL authorization predicates before bounded materialization. Fail closed for unsupported repositories/policy engines. Keep continuations opaque, expiring and server-local, with actor/grant/policy/revision binding. Bound SQLite VM work as well as returned rows. Continue using the existing property projection policy.

## Consequences and qualification limits

Legacy objects/relationships require explicit trusted security binding before this reader can expose them. Mutations require rebinding. The reference supports SQLite only and intentionally rejects arbitrary policy engines. A hard work-budget failure and timing are not proofs of cardinality noninterference. Authenticated host wiring, remote protocols, denial-of-service/side-channel qualification, source authority and PostgreSQL remain separate gates. This ADR does not authorize deployment, PI/SAP access, writeback, release promotion or a new score.

Validation: adversarial paging and 3,000-link load tests are defined in `tests/test_relationship_query_v01.py`; exact executed evidence and CI results must be recorded in the PR. See [the implementation contract](../bounded-relationship-query-v0.1.md).
