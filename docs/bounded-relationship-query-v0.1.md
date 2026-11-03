# Bounded relationship queries v0.1 — host-local reference

This is the first bounded implementation increment for [#329](https://github.com/faizrten/CEPIO/issues/329), not completion of its remote qualification. It adds no REST, SDK, MCP or Studio endpoint. The existing M1 helper remains host-local and retains its documented limitations. No release gate or maturity score changes.

## Contract and authority

`HostRelationshipReader` composes the existing `CEPIOApplicationService`, `ExecutionContext`, `RolePolicyEngine` and SQLite object/relationship tables. A host installs authenticated identity and relationship-visibility callbacks; the query payload permits only `asset_id`, `direction`, `limit` (1–50), and an opaque continuation token. Extra actor, tenant, role and grant declarations are rejected. A Python object constructed by trusted host code is not authentication: never build these callbacks or security bindings from agent/tool input.

The additive `SQLiteRelationshipPageAdapter` supplies an indexed keyset page read. Host-only importer methods bind current object versions to a tenant and exact relationship payloads to tenant, classification and source-use labels. These are security bindings, not new canonical ontology properties. Legacy/unbound rows are invisible. Object and relationship updates/deletes revoke bindings; reinserting the same ID does not inherit authority. Labels, policies and real-source mapping authority remain the host/profile's responsibility; possession of a label is not independent source attestation.

Both endpoints must match current identity/type, tenant and version. SQL applies type, sharing-scope, relationship type, classification and source-use predicates before fetching at most `limit + 1` rows. Properties use the same `RolePolicyEngine.filter_properties` contract as actor-scoped application reads. Relationship IDs, raw properties, security bindings, denied identities and hidden counts are never returned. An unsupported backend or policy implementation fails closed rather than falling back to `get_relationships` or listing the graph. Only the exact reference RolePolicyEngine is translated; custom policy engines need a separately qualified pushdown adapter.

## Continuation and bounded work

Ordering is deterministic by persisted relationship ID within a direction. Continuations are random server-local tokens (maximum 1,024 states, ten-minute lifetime), bound to actor, roles, tenant, asset, direction, page size, current grants, policy contents, expanded type rules and database revision. Mutation triggers cover objects, relationships and security bindings; SQLite data-version checks also conservatively invalidate on another connection's commits. A changed/stale/unknown token is rejected. A host restart or eviction invalidates tokens. No caller-supplied offset, snapshot declaration or last-seen ID is trusted.

The query is limited to 200,000 SQLite VM instructions (100-instruction progress intervals) and at most 51 materialized rows. This is a hard work ceiling, not an unqualified latency SLA. A pathological denied fanout can exhaust the budget and return a generic unavailable result. The response has no denied count, but availability and timing may still correlate with graph size. **Constant-time/noninterference, denial-of-service resilience, real authenticated host identity, source-use propagation and protocol qualification remain remote-exposure blockers under #329.** Do not expose this reference as a hosted workbench solely because its synthetic tests pass.

The adapter shares the existing SQLite connection and lock, and uses one read transaction per page. Host importers and adapters must honor that lock. It installs no new database service, source credentials, inference, customer data or external write path. PostgreSQL qualification remains separate (#283).

## Verification

`tests/test_relationship_query_v01.py` covers projected outgoing/incoming pages, opaque keyset continuation, forbidden query declarations, cross-tenant links/endpoints, hidden scopes, forbidden relation/classification/source use, missing bindings, mismatched endpoint types, retyping, source/tenant/policy drift, stale/tampered cursors, unsupported backends/policies, work-budget interruption and a 3,000-link load fixture with 600 hidden links before the first visible page. Load output records actual SQLite VM steps, elapsed time and traced peak Python memory. It forbids unbounded repository relationship/object-list reads and checks at most six materialized rows for a five-link page. These are synthetic runtime safety tests, not industrial reasoning or live-source qualification.

See [ADR-0050](adr/ADR-0050-host-local-bounded-relationship-query.md) for the architectural boundary. Exact test and CI evidence belongs in the governed PR.
