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

## 2026-10-24 OS and provenance triage

Live [image check 40074019268](https://github.com/faizrten/CEPIO/actions/runs/40074019268)
binds source `1579f53087456dd04dc4e628f866a85aa4c74b02` to deployed digest
`sha256:de1b0c42f0a183f060983e88c3ca6f09d7279134cefebb739e9b6ebbe0a78747`.
Its checksum-verified Debian 13.7 report has 44 HIGH package/advisory entries,
one UNKNOWN and no CRITICAL. Python blockers are zero; SBOM has 143 components
and only setuptools 84.2.1. This is a historical deployed result, not a result
for the hardening change below.

| Debian source | HIGH entries | Advisory / vendor triage | Next owner action |
| --- | ---: | --- | --- |
| util-linux | 36 | [76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [78410](https://security-tracker.debian.org/tracker/CVE-2026-78410): four advisories repeated across nine binary packages. Stable trixie/bookworm remain vulnerable; fixes listed in unstable/testing. | Base-image maintainer: track stable updates; qualify minimization separately. |
| acl | 1 | [54369](https://security-tracker.debian.org/tracker/CVE-2026-54369): privileged path/ACL symlink handling; stable vulnerable, new ABI fix in unstable/testing. | Base-image maintainer: await/qualify vendor fix; no ad hoc ABI backport. |
| ncurses | 4 | [69720](https://security-tracker.debian.org/tracker/CVE-2025-69720): infocmp utility overflow attributed to four source-related binary packages. Stable vulnerable; newer unstable/testing fixed. | Security owner: establish executable/module reachability; source-package attribution alone is not proof of application exploitation or a waiver. |
| systemd | 2 | [16742](https://security-tracker.debian.org/tracker/CVE-2026-16742): systemd-homed issue attributed to libsystemd0/libudev1. Stable vulnerable. | Security owner: prove presence/use of affected component before any applicability disposition. |
| perl | 1 | [9538](https://security-tracker.debian.org/tracker/CVE-2026-9538): Archive::Tar allocation DoS; stable fix postponed. Also one UNKNOWN [82560](https://security-tracker.debian.org/tracker/CVE-2026-82560), Pod::Text exhaustion, remains unfixed in Debian. | Security owner: verify shipped module paths and actual callers; retain UNKNOWN as blocking. |

All nine advisories remain OPEN. No fixed version is listed in the scanned
stable package entries. Vendor severity/deferral does not override the release
gate. Do not mix unstable libraries into the runtime, force-remove essential
packages, change scanner severity, or switch distributions just to reduce a
count. Any future base migration requires the full host/MCP and dependency
qualification plus a fresh exact-image scan.

Safe bounded mitigation: remove all regular-file setuid/setgid bits in the final
image, preserve package inventory and the existing nonroot service user. CEPIO
does not require privilege-transition utilities. Existing candidate CI checks
the complete root filesystem as root in an isolated read-only, network-disabled
container, rejects any remaining privileged regular file, checks the default
user is nonroot, and still runs the existing host/MCP smoke. This reduces
file-based escalation opportunities; it does not patch libraries, prove all
exploit preconditions absent, remove file capabilities, or waive any findings.

Both image checkers retain checksum-bound `os-triage.json` grouped by advisory,
including every HIGH/CRITICAL/UNKNOWN package entry, installed/fixed version and
vendor status. Grouping is for owner review, not deduplication of gate counts.

Provenance: the current demo build workflow invokes ACR build, records a digest
and deploys it; it has no attestation-generation step and only contents-read /
id-token-write permissions. The existing release workflow's attestation is for
its separately built local archive and wheel, not the deployed ACR manifest.
The exact deployed-subject GitHub API returned HTTP 404 on this review; that
can mean absent or inaccessible and is not global proof of absence. Add safe
read-only HTTP-status / first-page-count discovery alongside verification;
discovery never earns signature qualification and no error bodies are logged.

Build/provenance owner: propose a separately approved build-time, exact-manifest
provenance design with trusted ACR build inputs/materials and workflow/source
identity verification. GitHub attestation creation needs attestation-write
permission (see [official guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)).
This PR adds no permission, signing step, federation, role or registry write.
Do not attest an old scan or unrelated archive as the deployed build, weaken
the verifier, or claim source/build linkage is signed provenance. Production
remains HOLD pending all applicable release gates; no maturity score changes.

## Runtime minimization and exact-image provenance proposal

After all dependency installation and user/directory setup, the final Docker
stage removes unused mount/namespace, privilege-transition and terminal CLI
entry points, Perl executables, and any shipped Archive::Tar / Pod::Text /
Text::Wrap module entry files. The hosted HTTP service does not invoke these
programs. Python, `/bin/sh`, CA roots, resolver/name service, timezone data and
shared libraries remain. In particular, retain libuuid/libtinfo and other native
dependencies rather than breaking Python modules or forcing essential-package
removal. Installation and user creation occur before minimization. Rebuild the
image for maintenance; administrative CLI and terminal/Perl tooling are outside
the hosted image contract. Developer/source installations are unchanged.

`scripts/minimize_runtime.py` defaults to read-only verification; only the
Dockerfile uses `--apply`. It writes removed paths and a SHA256 of the unchanged
dpkg status database into `/usr/local/share/cepio/runtime-minimization.json`.
CI inspects the actual candidate as root, read-only and without networking,
rejects remaining entry points or modified inventory, and exercises native
NumPy/SciPy, SQLite, UUID, TLS trust, localhost resolution and UTC timezone
support before the existing hosted MCP smoke. Shared library advisories and
unknown severity stay blocking. Package-level scanner counts may remain
unchanged because package records and libraries intentionally remain: removed
entry points are bounded exposure reduction, not a CVE fix, complete component
reachability analysis, VEX statement or release exception. All live-image
findings remain OPEN until governed exact-artifact disposition.

The [inactive provenance design](../proposals/demo-exact-image-provenance.yaml)
is deliberately outside `.github/workflows`. It proposes signing the exact ACR
manifest digest during the same deployment job, after the build and before
deployment, with a custom SLSA v1 predicate that describes GitHub orchestration
of a remote ACR build honestly. Source commit, actual submitted context bytes,
Dockerfile hash, runtime extras, ACR run/tag/digest and GitHub invocation must
be captured by the trusted job, not supplied by workflow-dispatch callers.
The pure unsigned constructor has negative controls for subject/source/tag,
builder workflow, failed build and material hash mismatch; its output explicitly
is NOT evidence. It makes no network, signing, grant or infrastructure call.

The proposed pinned official `actions/attest` step uses an exact subject-name
and subject-digest, a custom predicate, GitHub storage and no registry signature
push. Activation would need a separately approved `attestations: write` job
permission; this PR applies no permission delta and adds no live signing step.
Existing Entra OIDC identity and Azure/registry grants remain unchanged. Before
activation the build/provenance owner must implement/review context capture and
record collection, strict signed-bundle semantic verification, retention and
fail-before-deploy ordering. Certificate/workflow/source validation and exact
subject verification must remain mandatory. Do not claim an isolated ACR
builder attestation, a SLSA assurance level or immutable dependency resolution
from this orchestration proposal. The current image's missing/unverified
provenance is not repaired by this document or an unsigned JSON statement.

Release owner: review this bounded minimization on green CI; separately authorize
merge/deploy and retain exact-image scan/OIDC evidence. Security/base-image owner:
continue stable vendor tracking and component applicability review, especially
retained shared libraries. Provenance owner: resolve the explicit design and
permission review before enabling signing. Production HOLD and canonical
maturity remain unchanged.

References: [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/),
[official attestation action inputs](https://github.com/actions/attest/blob/v4/action.yml).
