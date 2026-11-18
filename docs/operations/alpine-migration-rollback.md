# Alpine migration: non-Fabric runtime and rollback

Status: proposed in draft PR #301; no deployment is authorized by this document.
Scope: Linux amd64, Python 3.11, default `mcp` runtime. Fabric is not provisioned
and its live qualification is deferred. It is not a prerequisite for this default
runtime; enabling Fabric later requires separate identity, networking and query
qualification. Optional extras are not qualified by the non-Fabric run.

Verified candidate: source `3afa74ef37ac2a91795d74061f534261d42de5fa`,
[qualification run 40113997169](https://github.com/faizrten/CEPIO/actions/runs/40113997169).
Zero detected vulnerabilities at every severity; 1,183 source tests passed (one
Node-dependent skip covered by host CI), 96 installed-wheel tests passed, named
volume persistence across containers passed, and the actual candidate checker
passed. Artifact `12567233053` and its evidence hashes were verified. This is
isolated candidate evidence; the rollout prerequisites below still apply.

## Proposed change and evidence

The root Dockerfile uses digest-pinned Python 3.11.17 / Alpine 3.24, reviewed
runtime constraints, dash startup, non-root execution and removal of BusyBox
commands/copies. Package inventory is retained for honest scanning. Python
privilege, capability and inventory checks support both Debian and Alpine.
The HTTP startup command, PORT default, application interfaces and data schema
are unchanged. The SQL timeout fix remains dormant unless that optional transport
is selected. No Fabric resource or permission is created.

The branch qualification builds the actual root Dockerfile. It checks native
libraries, TLS trust/hostname behavior, startup and REST/MCP, installed-package
authorization tests with signed fixture tokens, persistent SQLite data across
separate containers on one named volume, and absence of the optional SQL driver.
It runs the full source suite and the actual candidate checker, retaining full
scan/SBOM reports and exact image identities. No real credentials or inference
are used. Live Entra/platform qualification remains distinct from fixture tests.

## Before any separately approved rollout

1. Review and merge only after required checks pass. Capture the approved source
   commit, final immutable image digest, scan, SBOM and verified provenance.
   Rebuilt images require their own checks: the base digest does not pin later
   OS package updates. Do not deploy a mutable tag based on an earlier scan.
2. Record the currently deployed immutable image digest and configuration
   privately, including startup, environment, identity, registry reference,
   volume mounts and numeric UID/GID ownership. Confirm the previous image is
   retained and pullable with the existing identity. Do not copy secrets to Git.
3. Verify the candidate UID/GID can access the actual persistent data without
   widening file permissions. Check platform startup/probes do not invoke removed
   BusyBox tools. Validate live Entra boundaries using existing authorized access.
4. Back up persistent data and verify restore procedures. This migration performs
   no schema conversion. The isolated named-volume test does not prove existing
   production volume permissions, backup recovery or platform networking.
5. Agree on the change window, operator and rollback criteria. Check health,
   authenticated REST/Management/MCP, denied unauthenticated access, storage,
   restarts and service latency/error-rate requirements in the intended environment.
   Use existing rollout controls; do not create infrastructure or broader grants.

## Rollback instructions (operator action only after approval)

Trigger rollback for sustained health failures, authentication/access regression,
storage errors, startup incompatibility or agreed latency/error-rate breaches.

1. Stop the rollout and prevent further promotion. Record the failed digest and
   symptoms without publishing tokens, secrets or customer data.
2. Restore the previously recorded immutable image digest through the existing
   authorized release mechanism, preserving the captured configuration and
   volume mounts. Validate its provenance/identity; never substitute a rebuilt
   floating Debian tag. The normal deploy workflow requires current reviewed
   main: do not bypass that check or dispatch it with an old source SHA. A rollback
   route must be reviewed and available before rollout; otherwise do not start.
3. Recheck health, real authentication and authorization boundaries, read/write
   persistence, restart behavior and error rates. Retain logs and evidence.
4. Restore a data backup only if necessary and separately authorized after checking
   for writes made since the backup. An image rollback alone must not discard data.
5. Prepare a reviewed source revert/fix so future builds agree with the intended
   image. Re-run qualification before another attempt. Keep the failed artifact
   for investigation; do not delete rollback images during the change window.

The previous Debian image has last-verified 44 HIGH and one UNKNOWN findings.
Restoring it may recover availability but also restores those known risks; it
cannot be described as passing the production security gate. Keep the scorecard
on HOLD until the selected deployed artifact satisfies the existing evidence
requirements. Canonical v1 maturity remains 69/100; an open PR earns no points.
