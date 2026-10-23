# ADR-0041: Inspect identity evidence without granting diagnostic authority

Status: Proposed

## Evidence

Read-only workflow run 39988142665 verified image-default startup, the expected
configured immutable image and three stable anonymous 401/Bearer rounds. The
existing federated principal obtained a token and received REST objects 200,
Management health 403, and an opaque failed MCP initialization. An HTTP 200 on
REST does not prove a CEPIO application role. The exact MCP rejection, token
audience/role comparisons and directory assignment evidence remain to be collected.

## Decision

Keep the existing main-only workflow, azure-demo environment and federated
identity. Use a tested helper to compare the acquired API token's audience,
issuer, tenant and client with the configured values. Decoded claims are labeled
diagnostics, not signature/authorization proof; live API decisions remain
authoritative. Project only comparison booleans, counts and three public role
names. Respect configured group-to-role mappings without logging group IDs.

For HTTP failures record status and only an allowlisted CEPIO or standard JSON-RPC
error code. Never print tokens, raw claims, arbitrary server error text, response
bodies, client/tenant/principal identifiers, settings or Graph permission lists.
Write the sanitized result even when qualification fails. Invoke only initialize
and tools/list; skip listing if initialization fails.

Attempt read-only Microsoft Graph inspection of this principal's assignments to
the target API and its published role definitions using existing permissions.
Graph reads denied or incomplete are explicitly unavailable evidence. Do not add
Graph permissions merely to make inspection succeed.

## Proposed least-privilege correction (requires evidence and approval)

If audience/issuer/client comparisons pass but effective roles are empty and MCP
reports `mcp_role_required`, inspect the target API's existing application-role
assignment for the same approved federated service principal. For an intended
metadata-only reader, the narrow candidate is the existing enabled Application
role `cepio_management_reader` on that API alone. It satisfies Management and the
current MCP metadata binding without adding industrial policy authority in the
reference configuration. Do not substitute `cepio_admin`, broad AI/operator
roles, subscription RBAC, a new identity, a client secret or new federation.

The Entra/API owner must confirm that this deployment principal is intended to
have data-plane metadata access. If it is not, preserve that separation and use
the designated approved reader identity rather than broadening the deployer.
No assignment, permission, identity, infrastructure, runtime authorization or
deployment change is implemented by this PR. A role assignment remains a separate
reviewed decision after live diagnostics establish the mismatch.

## Validation and scope

All existing CI, quality, CodeQL, governance and environment controls remain
enforced. Tests verify safe rejection projection, identifier/unknown-role
redaction, audience/client mismatches, empty roles/group mapping and Graph GET-only
fallback. Hosted tests use a synthetic `cepio_management_reader` actor to
initialize/list tools; reference policy still denies industrial reads, risk
functions and decision proposals. No paid inference or tools are invoked.

These tests do not establish live Entra assignments or production readiness.
Merge the diagnostic change through normal required checks before dispatching
the main-only read-only workflow; do not relax branch/environment guards to run
unreviewed diagnostic code with the deployment identity.
