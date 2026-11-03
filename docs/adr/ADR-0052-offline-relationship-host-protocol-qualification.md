# ADR-0052 — Offline relationship host/protocol qualification

Status: offline qualification increment for #329, not production endpoint admission.

## Decision

Use the existing authenticated REST principal, MCP request-local actor provider and bearer validator in an in-process synthetic qualification harness. Both test transports call one `RelationshipQualificationBoundary` over the source-aware bounded reader. The boundary requires current source authorization, captures one request-local identity, revalidates query payloads and normalizes denial/resolver/repository errors without graph, source or cursor internals.

Apply fixed per-process admission ceilings: four concurrent reads, thirty attempts per actor/tenant per sixty-second window and 120 attempts in total per window. Admitted authenticated attempts consume budget even when query validation or source policy later denies the read. Invalid/missing principal contexts are rejected before admission. Counter state is bounded by the total attempts; new principals cannot bypass an exhausted global window. This is not a distributed rate limiter and no distributed denial-of-service guarantee follows.

No production REST route or MCP tool is installed. No environment toggle mounts this adapter. The REST path and MCP registration used for qualification live exclusively in tests. Existing supported REST/MCP contracts and default tool lists remain unchanged.

## Evidence and remaining gates

The harness uses ephemeral RSA keys, synthetic signed JWTs, the production token validator, existing MCP authentication middleware and actual Streamable HTTP JSON-RPC. Only key discovery is replaced by local synthetic keys. It tests valid cross-protocol pagination, invalid signature/audience/issuer/tenant/expiry, forged dev headers, role/identity isolation, caller-authored scope rejection, cross-actor cursors, current source revocation, concurrency saturation and bounded admission state. It proves offline conformance, not a successful real Entra tenant deployment or source attestation.

Before any endpoint is admitted, separately qualify: production adapter and source-binding completeness/ancestry/revocation authority; denied-fanout timing/availability (including global revision invalidation); byte-size and distributed resource isolation; production identity configuration and transport/security review. Synthetic qualification cannot waive these controls. Deployment, PI/SAP credentials, external writeback and CONNECT/scorecard advancement remain separate authorization/evidence gates.
