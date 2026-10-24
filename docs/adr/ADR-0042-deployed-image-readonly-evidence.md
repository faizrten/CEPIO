# ADR-0042: read-only evidence for the configured deployed image

Status: proposed automation; not production qualification.

## Problem and decision

Release qualification rebuilds a local image. Its scan, SBOM and archive
attestation do not attest the separately built ACR image configured in App
Service. The existing deployment path records a source/run/tag/digest mapping
but does not retain image scan/SBOM or a verified signed provenance statement.

Add `CEPIO Deployed Image Read-only Evidence`, a main-only, manually approved
`azure-demo` workflow using the existing federated identity. Supply the exact
expected sha256 digest, deployed source commit, successful GitHub deployment
run and ACR quick-build run. The checker reads App Service before and after the
scan and rejects drift. Existing GitHub/ACR records must bind source, deployment
attempt, registry/repository and image digest. This linkage is explicitly not
signed provenance.

The pinned official Trivy 0.76.1 image is resolved by immutable digest. It reads
the target from the registry, without executing target image code or mounting
the Docker socket. Retain all reported vulnerability severities, including
unfixed issues; HIGH, CRITICAL, UNKNOWN severity, missing/unusable data or
scanner failure blocks qualification. Produce CycloneDX SBOM for the same
immutable subject, require nonempty inventory and confirm installed setuptools
is a stable version >=84.1.0. Retain checksums of reports in a subject manifest.

Verify any existing SLSA v1 build provenance with `gh attestation verify`, exact
image digest, CEPIO repository, deploy workflow identity, source commit/main ref
and GitHub-hosted runner requirement. Missing, invalid or inaccessible provenance
fails the overall check even if scan/SBOM succeed. The checker never signs or
retroactively manufactures build provenance. Current workflow artifacts,
registry linkage and signatures are different evidence classes.

## Permission and IP boundary

Use the existing environment, contents-read/id-token-write permissions and
Azure identity; add no Entra, Azure RBAC, Graph, registry or attestation-write
grants. Acquire a registry read credential through the existing login, store
Docker configuration only in an ephemeral temporary directory, capture command
output privately and clean up afterward. Access failure remains a blocker;
never request broader grants automatically. Upload scan/SBOM/verified-public
provenance and a sanitized manifest only: no credentials, App Service settings,
raw build logs, image layers or customer/protected corpora. The current public
CEPIO runtime package inventory is publication-safe; customer images require
their own private evidence boundary.

No rebuild, deployment, image signing, resource provisioning, model inference
or MCP tool invocation occurs. A failed provenance check cannot be repaired by
relabelling a scan as build provenance. A future release must produce verifiable
exact-image provenance at build time under separately reviewed permissions;
the existing release attestation job does not establish current ACR provenance.

## Validation and remaining gates

Deterministic tests cover exact-target validation, digest/schema mismatch,
empty inventory, unfixed high/critical and unknown severity, patched setuptools,
wrong source/build linkage, absent/mismatched provenance, independent evidence
retention, deployment drift and credential suppression. Run full existing CI,
quality, CodeQL and governance. New cloud diagnostics must merge before the
main-only guard permits existing OIDC use; PR tests cannot substitute for the
live digest scan. Do not change release/maturity scores or declare production
readiness from this bounded check.

References: [Trivy image scanning](https://trivy.dev/docs/latest/target/container_image/),
[GitHub provenance verification](https://cli.github.com/manual/gh_attestation_verify).


## 2026-10-24 follow-up: runner ownership, final read and runtime tooling

The first live check completed scan/SBOM/provenance attempts, then reported a
postcollection error. The old scanner ran as container root against a runner-owned
temporary cache; root-owned cache directories are a cleanup failure mode not
covered by mocks. Run the scanner with the runner UID/GID, `/docker` credentials,
`/cache` storage and `/tmp` HOME. Keep the root filesystem read-only and never
mount the Docker socket. Safe stage/type/code diagnostics now identify failures;
the final configured-image read runs independently even after cleanup failure.
A cleanup error still fails qualification. The original generic error alone
does not prove which operation failed; a successful patched live run remains
necessary to close that incident.

Verified pip 26.2.2 wheel SHA256
`fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70`
contains `pip/_vendor/bom.cdx.json` (SHA256
`7be976001ba70fe6b38530af13063bea96e1bd894c271c4e57908c737079ef93`)
listing setuptools 70.3.0, msgpack 1.1.2 and urllib3 2.7.0. The wheel actually
ships vendored msgpack/urllib3 code; the older setuptools entry must not be
represented as the installed top-level setuptools when the image also records
84.2.1 METADATA. Keep all old-image scan findings pending exact applicability
review; add no ignore, VEX waiver or scanner exclusion.

The final runtime needs no pip invocation. Install and validate dependencies at
image build time, then uninstall pip and remove ensurepip (including bundled
installer wheels). Keep patched top-level setuptools. Optional runtime extras
must be selected during the build using CEPIO_RUNTIME_EXTRAS; use a rebuilt
immutable image for dependency changes. Developer wheel installation is unchanged.
This removes unused tooling and its vendor code/metadata rather than hiding it.

Existing CI builds one candidate, inspects its immutable config ID/archive hash,
scans it without executing target application code, and retains all severities
and a full CycloneDX inventory. The targeted regression requires no Python
HIGH/CRITICAL/UNKNOWN entries, no pip inventory and patched setuptools; the
existing host/MCP smoke must also pass. This targeted regression does not waive
remaining OS findings or the full deployed-image qualification check. Its
manifest always says production_qualified=false, and reports full image-policy
status separately. No candidate is deployed or signed by CI. Current deployed
image findings cannot be cleared by a candidate PR alone.

Upstream context: [pip's vendor SBOM](https://github.com/pypa/pip/blob/26.2.2/src/pip/_vendor/bom.cdx.json),
[msgpack advisory](https://github.com/msgpack/msgpack-python/security/advisories/GHSA-6v7p-g79w-8964),
[urllib3 advisory](https://github.com/advisories/GHSA-8988-9CW3-XX77).
