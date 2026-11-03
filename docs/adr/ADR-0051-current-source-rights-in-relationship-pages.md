# ADR-0051 — Current source rights in relationship pages

Status: implementation increment for #329; remote exposure remains blocked.

## Decision

Extend the existing host-local reader with an optional, trusted current-source-access resolver. Its result is bound to the authenticated actor, roles, tenant, fixed `operational_inspection` purpose, rights revision and expiry. It is an adapter result, not a consent registry or a replacement for the pending #299 sovereignty contracts. A future host may implement the resolver using those contracts after their own review and integration.

Trusted importers bind all contributing source references to each endpoint version and exact relationship payload. In source-aware mode, missing bindings fail closed; every source on the subject, relationship and neighbor must be authorized. SQL applies these restrictions before materialization. Mutations revoke bindings, and rights/binding drift invalidates continuations. Current UTC time is checked at admission and before release; historical query time cannot resurrect expired rights.

## Limits

Source completeness, derivative ancestry, permission authenticity and revocation are the resolver/importer's responsibility. A string label or successful synthetic test does not attest these facts. Local legacy callers retain their existing behavior without the resolver; that mode is ineligible for remote composition. No production route, source credential, source registry, industrial IQ, external write or deployment is introduced.

SQLite work remains capped, but denied-fanout timing/availability and conservative global revision invalidation remain remote blockers. PostgreSQL and deployment qualification stay separate. Source permissions must never be supplied through an agent/tool query.

## Verification

`tests/test_relationship_source_access_v01.py` tests source permission propagation, additional-source denial, fixed purpose, actor/tenant/role binding, expiry at admission/release, revocation/version drift, source metadata projection, missing legacy bindings, bounded input and mutation revocation. Existing adversarial paging/load tests remain applicable. Exact executed results belong in the PR.
