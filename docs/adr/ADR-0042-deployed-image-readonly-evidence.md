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
