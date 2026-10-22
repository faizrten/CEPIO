# ADR-0037: Read-only authenticated hosted API preflight

Status: Proposed

## Context
Anonymous-denial checks and health checks do not establish that an authenticated client can use the hosted application contract. Drilling reliability qualification must first prove access through that contract.

## Decision
Add a manual-only workflow on main using the existing protected azure-demo environment and its OIDC identity. Pin the existing Core hostname. Read only the configured audience from App Service settings, obtain a short-lived resource token inside the runner, and perform bounded GET requests to objects and Management health. Refuse redirects. Never print or upload tokens or response bodies. Do not introduce new grants, infrastructure mutations, model calls or Actions.

The existing deployment identity is diagnostic-only here, not a decision to use it as a permanent scenario identity. A denied token or request must lead to explicit configuration/least-privilege review, never automatic grants. GUID audiences assume the conventional api:// App ID URI; nonstandard resource configuration remains an explicit unresolved condition on failure.

## Governance and consequences
Existing branch, review, CI, environment and deployment gates remain enforced. The workflow cannot run on PR refs and does not auto-run on merge. It does not alter existing deployment triggers. Repository policy classifies workflow changes as high risk even though the probe itself is read-only. No release, production qualification or scorecard claim changes.

## Validation
Embedded Python parsed with ast.parse. Repository CI and governance checks must pass before merge. Live authenticated execution is pending manual dispatch and any existing environment approval. HTTP 200 on a filtered object list is access evidence only, not proof of drilling data visibility, end-to-end scenario execution or governed writeback. Management health is reported independently from the application-access result.
