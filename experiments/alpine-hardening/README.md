# Alpine hardening and integration qualification

Candidate-only follow-up to the supported-base comparison in ADR-0042. Production
Dockerfile, application code, release state, deployment workflows and permissions
are unchanged. The branch-only workflow uses contents:read and no cloud identity.

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

The unchanged production image-checking tools are also executed as read-only
compatibility probes. A Debian-specific tool or inventory failure is recorded
as a migration blocker; passing the isolated runtime checks does not bypass it.
If CEPIO's Fabric configuration is rejected, the integrations job fails after
retaining all other test and security results. Application fixes are outside
this base-image/hardening-only change.
