# ADR-0040: Verify the hosted protocol composition through rollout

Status: Proposed

## Evidence and uncertainty

Azure demo deployment run 39850881945 installed an immutable image successfully,
then passed REST health and anonymous REST/Management denial but observed HTTP 404
on its one MCP request immediately after restart. A later independent check of
the same hostname observed the required HTTP 401 on MCP with unchanged repository
mainline. This does not establish which worker/image answered either request.
Rollout timing is plausible but not a proven root cause. The live App Service
startup override still requires authenticated control-plane inspection.

## Decision

Keep the Dockerfile's combined `cepio.host_api:app` entrypoint and existing
environment-scoped federated OIDC identities. Do not change routes or overwrite
startup configuration based on an unconfirmed diagnosis.

Before image deployment, inspect the startup override without logging arbitrary
command contents. Allow the image default or the documented explicit combined
host command; reject other overrides for private inspection.

After restart, require three complete consecutive successful protocol-boundary
rounds within a 180-second retry window. Each round requires REST health and
anonymous HTTP 401/Bearer challenges for REST objects, Management health and MCP.
A transient 404 resets the counter; a persistent 404 fails. Anonymous protected
2xx responses stop immediately. Redirects never count as successful denial.

Test the packaged container's MCP route and protocol initialization in CI, beyond
the existing health-only smoke. The manual main-only read-only access check also
inspects the configured digest and uses its existing identity for authenticated
REST/Management reads, MCP initialize and tools/list. It never invokes a tool.

## Governance and validation

All existing required CI, quality, CodeQL and governance gates remain enforced.
The immutable image check, approved environment, identity, repository/branch
guards and strict denial expectations remain intact. No inference, role grant,
infrastructure provision, automatic merge or deployment is introduced by this PR.

Deterministic tests cover transient and persistent 404s, stable-round counting,
unsafe anonymous success, redirect/challenge handling and startup overrides.
Local hosted tests use synthetic validated actors for metadata protocol checks;
they are not real Entra evidence. Live anonymous tests pass independently.
Real authenticated proof requires the merged read-only workflow to run with the
existing environment identity. A failed token/role check remains a blocker.

## Limits

Configured image digest and public HTTP success do not prove per-worker image
identity, full role/tenant isolation or production security readiness. Retain the
source SHA, configured digest, workflow run and scoped probe results separately.
No CEPIO release status or canonical maturity score changes here.
