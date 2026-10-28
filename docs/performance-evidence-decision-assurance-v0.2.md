# Enterprise Evidence and Decision Assurance v0.2 — development contract

This additive Core contract composes the existing host-bound Performance Evidence
service and the experimental Executive Performance service. It **does not**
create an alternative Industry IQ engine, approve Decisions, invoke Actions,
or change the public /api/v1 or MCP protocol.

## Evidence handle

A trusted host configures an AssurancePolicy with exact organization,
evidence plan, subject, focus node, actor roles and source ID/version locks.
An authenticated actor may request only the host plan, evaluation time and
current versus historical-replay mode. The service resolves the actual evidence
through the existing host-bound source service, checks the pinned versions,
and retains an immutable in-memory snapshot behind a cryptographically random
short-lived opaque handle.

An agent cannot submit performance values, source versions, tenant identity,
or a claimed attestation status in the handle request. Handle retrieval is
constrained to the original authenticated actor and tenant. Capacity and
expiry are bounded. Historical replay never claims current freshness;
current mode independently checks a trusted host clock window.

**Important:** a handle proves that a value passed this CEPIO host binding,
not that a real industrial source cryptographically signed it. The status
remains `host_bound_not_source_attested`. The backing handle store is
in-memory and lost on restart. It is not a production distributed token store.

## Decision assurance receipt

The existing Industry IQ / Executive preview runs on server-recovered
observations, not caller-submitted values. The resulting deterministic receipt
includes actor, tenant, source record/version keys, contract revision hashes,
policy ID/version, evaluation time, evidence snapshot digest and Decision
package digest. `verify_assurance_receipt` detects changes to the local receipt.

SHA-256 hashes are **integrity checks, not issuer signatures**. The companion `verify_assured_result` checks both the receipt and the exact executive payload fingerprint; verifying only the receipt does not validate an accompanying payload. A malicious
party who controls both the receipt and its hash can forge a new receipt.
An external-source signature, independently secured issuer identity, durable
append-only receipt store, and verified source-side formula execution are
deferred to later explicit acceptance gates.

The receipt always reports `development_conformance_only`,
`recommend_only`, `policy_required=true`, and false Decision persistence,
workflow start and action execution. The referenced assurance policy is a
host permission/consistency contract; this is **not** a Kinetic approval
decision, nor a substitute for the existing Workflow Policy runtime.

## No trust promotion

The experimental ExecutivePerformancePackage still uses the preexisting
`caller_supplied_unverified` label. The outer assurance receipt records a
host-bound snapshot separately; it deliberately **does not rewrite** the
Executive package's trust field to `source_attested`.

## Negative tests

The v0.2 tests cover cross-tenant and cross-actor handle access,
unauthorized roles, expired and unknown handles, bounded state, source version
changes, unpinned sources, missing commercial/HSE observations, replay/current
clock confusion, client-injected KPI/attestation fields and receipt editing.

The tests use the existing synthetic Rig 07 fixture. No new infrastructure,
paid inference, customer data, or protected industry casebook is introduced.

## Follow-on qualification

1. Private Labs adversarial cross-repository tests on an exact merged Core SHA.
2. Independently reconciled Business Logic inputs/formulas and time windows,
   including commercial calculation checks.
3. Authenticated issuer/source attestation, replay-resistant persistence and
   durable audit/Decision lifecycle.
4. Role-scoped REST/MCP/Teams acceptance and multi-tenant isolation under a
   hosted identity, without promoting synthetic evidence to operational truth.
