# Alpine hardening and integration qualification

The current migration workflow runs `nonfabric` against the root Dockerfile.
Fabric is not provisioned; live qualification is deferred. Prior default,
optional-extra and Trixie-control results remain historical evidence. The
non-Fabric run adds persistence across separate containers on a named volume and
requires the optional SQL driver to be absent. See
`docs/operations/alpine-migration-rollback.md` for scope and rollback instructions.

Candidate-only follow-up to the supported-base comparison in ADR-0042. Production
Release state, deployment workflows and permissions are unchanged; the root
Dockerfile now proposes the Alpine migration for review.
The authorized follow-up fixes Fabric's driver timeout argument and makes the
candidate checker portable to Alpine. The branch-only workflow uses contents:read
and no cloud identity.

Two final images are built and scanned independently: default `mcp`, and
`mcp,otel,fabric-sql`. Both use the pinned Python/Alpine base and prior runtime
constraints. The optional image installs runtime libraries libltdl, krb5-libs and
libstdc++; it does not need the earlier exploratory krb5 development package.

After all installation, the image replaces BusyBox's shell with Alpine main's
dash package and removes the BusyBox executable, copies and every resolved
shortcut, including administrative commands. Package inventory is retained and
hashed, not rewritten to suppress vulnerabilities. No setuid/setgid files or
file capabilities are allowed. The Python probe verifies absence, shell startup
expansion, SQLite reopen, and positive/negative TLS trust and hostname behavior.

The installed wheel receives native and hosted REST/MCP checks. The complete
source suite runs under the same Alpine/Python base. Existing Fabric, hosted MCP,
authorization and management tests also run against the installed wheel inside
the final hardened image, with test tools mounted externally and no networking.
Those Fabric tests use synthetic connectors, not a real Fabric database.

The optional driver is loaded and exercised against a loopback-only TDS listener
using its supported timeout API; a prelogin packet must arrive and the incomplete
connection must fail closed. Separately, the driver's parser validates CEPIO's
actual connection configuration without requesting a cloud token. A Trixie
control distinguishes existing configuration defects from Alpine regressions.
This verifies native execution and error handling, not authentication or SELECT
execution. OpenTelemetry context propagation is
tested without an exporter. A separate public Microsoft OpenID metadata GET
checks external DNS and default CA trust without credentials or token requests.

The scanner examines both exact final image archives with full SBOM and no
severity/unfixed filters. Workflow failures fail the check; they are not silently
converted to candidate eligibility. Evidence logs, JUnit XML, scanner JSON,
SBOM, image identities and hashes are retained for 30 days.

Unproven by this credential-free workflow: live Fabric/SQL authentication and
read-only queries, Azure managed identity, private endpoint networking, ARM64,
production performance and deployment provenance. A clean result cannot imply
production qualification for those paths. No deployment, merge, permission
expansion, model invocation or vulnerability waiver is part of this experiment.

The production candidate checker is executed directly, including its independent
archive-bound scan. Python replaces the dependency on find/id, retaining non-root
and privilege-bit inspection and adding file-capability rejection. Alpine's
preserved inventory, removed commands, shell and BusyBox-copy absence are verified
without weakening Debian checks or scanner thresholds. Full checker evidence is
retained alongside the isolated checks.
If CEPIO's Fabric configuration is rejected, the integrations job fails after
retaining all other test and security results. The configured timeout is passed
through the driver's supported keyword API; encryption and certificate validation
remain required. Existing injected connection factories retain their interface.
