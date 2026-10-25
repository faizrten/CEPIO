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

## Existing-OIDC implementation: registry-backed exact-image provenance

This implementation supersedes the inactive GitHub attestation-API design above.
Both existing jobs keep exactly `contents: read` and `id-token: write`. There is
no `attestations: write`, `actions: read`, new Entra identity/role, registry policy
change, key vault or persistent signing key. Cross-run artifact downloads require
Actions-read permission, so verification reads the signed attestation from the
existing CEPIO image repository instead. Signing adds OCI attestation metadata
beside the exact newly built digest using the existing ACR login. It does not
change the image layers/digest or App Service configuration. If the identity
cannot publish there, fail before deployment; never grant a role automatically.

`install_cosign.py` pins official Cosign v3.1.4 by SHA256 and installs only into
runner temporary storage. The demo build now runs `build_demo_image.py` after
the existing current-main guard. The helper verifies GitHub run/source/attempt
and hosted-runner metadata; rejects tracked, untracked or ignored working-tree
changes; captures a clean `git archive` SHA256, Dockerfile and `.dockerignore`
hashes before ACR submission; uses the same local context, Dockerfile and MCP
extra; and rereads the authenticated successful ACR run/tag/digest mapping.
The archive hash describes the clean committed source snapshot, not the Azure
CLI's separately compressed/excluded upload bytes. The context policy and
`.dockerignore` hash are explicit. This does not claim complete transitive/base
image dependency resolution or reproducible builds.

The helper constructs a custom SLSA v1 predicate for **GitHub orchestration of
ACR**: exact source/ref, source snapshot/Dockerfile/ignore hashes, build type,
runtime extra, ACR run/tag/output digest and GitHub invocation. Cosign obtains
its short-lived certificate through the existing GitHub OIDC permission and
publishes the attestation into the same repository. Public Sigstore services
retain certificate/transparency metadata and signed predicate contents; only
public source identifiers, hashes and sanitized build identifiers are included,
never customer data, tokens, complete cloud records or source archives.

Before any App Service mutation, a separate `cosign verify-attestation` reads
the registry and requires exact issuer, workflow certificate identity, source
SHA, source ref, repository, workflow_dispatch trigger, transparency verification and
default image-claim verification. Authenticated GitHub job metadata must show
one GitHub-hosted `deploy` job, with ubuntu-latest and no self-hosted label. Only
successful verifier stdout is decoded; its in-toto statement must exactly match
the expected subject, custom predicate type/build type, materials, builder and
ACR/GitHub invocation. Valid signatures over another image/source/build do not
qualify. No insecure/ignore flag or wildcard identity is allowed. Signing or
verification failure withholds deployment outputs. Public predicate, bundle and
verified statement are retained as workflow artifacts for 90 days; registry
attestation is the independent read-only verification source, not those files.

The read-only image workflow installs the same pinned verifier, uses its existing
temporary registry login, and runs the same signature and semantic checks.
GitHub subject API discovery remains diagnostic only: a 404 cannot invalidate a
valid registry attestation and cannot qualify a missing one. Missing, expired,
inaccessible or mismatched registry provenance remains a blocking failure. The
checker never signs, pushes or retrofits a statement for a historic deployment.
An image predating this build-time path remains unqualified until a fresh source
is merged, built and deployed through the guarded workflow.

Validation includes source/image/material/runner/invocation mismatch controls,
withheld-output and credential-restoration checks, unchanged permission checks,
and native pinned-Cosign positive/tampered-file/wrong-identity/wrong-issuer tests
using the official public Cosign release bundle. PR CI uses no CEPIO signing or
cloud identity. Native fixture success is not a live CEPIO signing proof: the
first main build must still establish existing registry push permission, GitHub
certificate claims and read-only exact-image verification. A signed vulnerable
image remains production HOLD; every scan/SBOM/authorization gate is independent.

References: [Cosign attest](https://github.com/sigstore/cosign/blob/v3.1.4/doc/cosign_attest.md),
[verification constraints](https://github.com/sigstore/cosign/blob/v3.1.4/doc/cosign_verify-attestation.md),
[GitHub artifact download permission](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact).

### Compatibility with separately authorized manual deployment

After ADR-0043, the active builder and certificate verifier require only
`workflow_dispatch` on current main. The deployment run must contain exactly the
seven successful reusable CI validation jobs and one GitHub-hosted deploy job;
missing, failed, extra or truncated job records fail closed before image outputs.
The inactive historical proposal retains its former trigger by default. This
changes no identity permissions or deployment authorization boundary.
The builder process disables Python bytecode writes so its own helper imports
cannot contaminate the clean source context; unexpected existing ignored files
still fail the clean-worktree gate.

### Alternative base evaluation — 2026-10-24 (experiment, not deployment)

The isolated `security/base-image-evaluation` branch compares supported,
digest-pinned bases while leaving the production Dockerfile, application code,
dependency manifest, infrastructure, authorization and deployment workflows unchanged.
The experiment has only `contents: read`, uses no cloud credentials or model calls,
and never publishes an image. The test harness is in `experiments/base-images/`.

Evidence: [completed matrix](https://github.com/faizrten/CEPIO/actions/runs/40101146245)
at `9d76126c07e5d85b0075500ceec33564c21940ed`, using application main
`f3f4e7ce8988f2b386b5f355fe7433ee0fa18e53`, and
[passing standard CI](https://github.com/faizrten/CEPIO/actions/runs/40101146256).
All four downloaded artifact ZIP digests and every report-listed file hash were
verified. Earlier harness runs are superseded by this completed matrix.

| Base / Python | Critical | High | Medium | Low | Unknown | Source tests |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Trixie / 3.11.17 control | 0 | 44 | 58 | 61 | 1 | 1,168 pass / 1 skip |
| Bookworm / 3.11.17 | 2 | 61 | 111 | 107 | 1 | 1,168 pass / 1 skip |
| Alpine 3.24.3 / 3.11.17 | 0 | 0 | 0 | 0 | 0 | 1,168 pass / 1 skip |
| Ubuntu 24.04 / packaged 3.12.3 | 0 | 0 | 26 | 5 | 0 | 1,168 pass / 1 skip |

The skipped test requires Node, absent from each Python test container; it is
part of passing host CI. The source suite runs with networking disabled in a
writable disposable copy, with all capabilities dropped. The exact installed
runtime wheel separately passes nonroot/privilege-bit, absent-pip, preserved
package inventory, SQLite, UUID, CA trust, localhost resolution, timezone,
NumPy/SciPy, JWT, health, anonymous MCP denial, authenticated MCP initialization
and the same eight-tool listing checks on all four bases. The same pinned Trivy
0.76.1 scanner performs unfiltered image-identity-bound scans and CycloneDX SBOMs;
runtime Python versions are constrained to the previous verified PR300 SBOM.

Optional MCP/OpenTelemetry/Fabric SQL extras install, import and load the native
SQL driver on all four bases. Alpine requires `libstdc++` in addition to the
documented libtool/Kerberos prerequisites. These optional probes are separate
images: the table scans the default runtime, not those extra-equipped images.
No live SQL/Fabric connection or paid inference was attempted.

**Recommendation:** Alpine 3.24 is the strongest candidate for a narrowly scoped
default-runtime migration PR. The tested image is
`python:3.11.17-alpine3.24@sha256:5fb4bc53dd0180955e31e5245b648bbb24a4ac4ab03a1de81513642325220bcd`.
It preserves the Python minor version and passes the tested CEPIO behavior.
The original 45 package-level findings have evidence beyond scanner silence:

| Original finding group | Count | Alpine default-runtime disposition |
| --- | ---: | --- |
| CVE-2025-69720, ncurses | 4 HIGH | Retained ncurses 6.6_p20260516-r0 is newer than upstream fix 6.5-20251213. |
| CVE-2026-76642, -78408, -78409, -78410, util-linux | 36 HIGH | Retained libuuid 2.42.3-r1 meets Alpine vendor fixes: 2.42.3-r0 for three issues and r1 for -78408. |
| CVE-2026-16742, systemd | 2 HIGH | No systemd-source packages in preserved Alpine inventory/SBOM. |
| CVE-2026-54369, ACL | 1 HIGH | No ACL-source packages in preserved Alpine inventory/SBOM. |
| CVE-2026-9538 / -82560, Perl | 1 HIGH / 1 UNKNOWN | No Perl-source packages in preserved Alpine inventory/SBOM. |

References: [Alpine vendor security database](https://secdb.alpinelinux.org/v3.24/main.json),
[ncurses CVE record](https://www.cve.org/CVERecord?id=CVE-2025-69720),
[upstream ncurses fix](https://invisible-island.net/ncurses/NEWS.html#index-t20251213).
Alpine's main repository support runs to June 2028; Python 3.11 security support
ends October 2027, so that earlier date constrains this combination. See
[Alpine support](https://alpinelinux.org/releases/) and
[Python lifecycle](https://devguide.python.org/versions/).

**Ubuntu is not evidence that all original findings were fixed.** It installs
fixed ncurses, systemd and Perl versions for -69720, -16742 and -9538, but
[ACL -54369 is ignored by Ubuntu](https://ubuntu.com/security/CVE-2026-54369)
because the backport is too intrusive; retained libacl1 is 2.3.2-1build1.1.
The four util-linux advisories and [Perl -82560](https://ubuntu.com/security/CVE-2026-82560)
remain vendor "Needs evaluation", with util-linux 2.39.3-9ubuntu6.6 and perl-base
5.38.2-3.2ubuntu0.6 still in inventory. For example,
[util-linux -76642](https://ubuntu.com/security/CVE-2026-76642).
The clean HIGH/UNKNOWN scanner count cannot close those original advisories.
Bookworm is rejected because it increases blocking findings. Trixie still has
the original 44 HIGH and one UNKNOWN.

Limits: linux/amd64 only; no live service, external DNS/TLS integration,
performance/SLO, ARM64, optional-image security or deployment qualification.
Alpine uses musl and BusyBox: removing standalone administrative links does not
prove their BusyBox multicall equivalents are absent. A production migration
must explicitly preserve the required hardening contract and scan its final
Dockerfile output, including any selected extras. These findings authorize no
waiver or deployment. The current deployed image remains 44 HIGH / 1 UNKNOWN,
production-security G6 remains FAIL/HOLD, and canonical v1 maturity stays 69/100.

Artifacts (30-day workflow retention): Alpine `12563211244`, Bookworm
`12563027893`, Trixie `12562418607`, Ubuntu `12561949971`. Each includes full
scanner JSON, SBOM, grouped OS triage, JUnit results, build/smoke logs and hashes.

### Alpine follow-up: removal of BusyBox and final optional-runtime scans

`experiments/alpine-hardening/` adds isolated default and optional-extra final
images. A supported dash shell preserves the existing startup command while the
BusyBox executable and its aliases are removed after installation. The preserved
apk inventory continues to describe installed package provenance for scanning;
it is never edited to erase findings. Runtime probes require the administrative
commands, BusyBox copies, privilege bits and file capabilities to be absent.

The follow-up scans both final runtime variants, exercises installed-wheel
authorization/Management/MCP/Fabric contracts, TLS trust rejection, persistent
SQLite reopening, public Microsoft DNS/HTTPS, and real SQL-driver prelogin with
a loopback fixture. These tests use no cloud credentials or model calls. The
existing full source suite is also rerun. Live Fabric authentication/queries,
managed identity and private networking remain unqualified by these isolated
checks. Verified results follow; this harness makes no production or maturity
claim.

### Verified Alpine hardening outcome: production switch remains blocked

The [completed hardening run](https://github.com/faizrten/CEPIO/actions/runs/40108881924)
tested commit `5c7e2c271af27fe2fc38ea2d4f11368eabe3e104` on linux/amd64.
Both final Alpine images (default and `mcp,otel,fabric-sql`) have **0 CRITICAL,
0 HIGH, 0 MEDIUM, 0 LOW and 0 UNKNOWN** in the retained Trivy reports.
Each passed 1,168 source tests with one Node-dependent skip and all 93
installed-wheel integration/authorization tests. Host CI covers the Node test.
CodeQL passed after making the TLS fixture's minimum version explicitly TLS 1.2.

Both images removed BusyBox and 304 aliases, retained dash startup/PORT behavior,
ran as non-root, preserved apk inventory, and passed absence checks for
administrative commands, privilege bits and file capabilities. Native libraries,
REST/MCP, SQLite reopen, TLS trust/hostname rejection, public Microsoft DNS/HTTPS
and OpenTelemetry context checks passed where applicable. No telemetry exporter,
cloud authentication or paid inference was invoked.

The optional-runtime job **fails**, correctly, on the existing CEPIO Fabric
connection configuration. `FabricSqlSettings.connection_string` supplies
`Connection Timeout=...`, which installed `mssql-python==1.16.0` rejects with
`Unknown keyword 'connection timeout' is not recognized`. The same rejection
was reproduced on Trixie. With the driver's supported `timeout=` argument,
both native drivers sent an 88-byte TDS prelogin packet to the loopback fixture
and rejected the closed peer. This proves native initialization and protocol
startup, not successful authentication or a SQL query. Mocked integration tests
did not expose this existing application issue; no application fix is included.

Read-only probes also establish that the unchanged production candidate checker
cannot qualify this Alpine image: it requires removed `find`/`id` commands and
the Debian dpkg/minimization manifest. The isolated harness does not waive or
replace that gate. A reviewed portability update is needed before qualification.
Live Fabric authentication/SELECT, managed identity and private endpoint
networking remain unverified without authorized credentials and environment.

**Decision: not safe to switch production now.** The security and isolated
hardening results are favorable, but the existing gate incompatibility and
Fabric configuration failure must be resolved and relevant live integration
evidence obtained. Production Dockerfile, application code, manifests and
infrastructure are unchanged; no deployment, merge or permission expansion.
The last verified deployed findings remain 44 HIGH / 1 UNKNOWN, G6 remains
FAIL/HOLD, and canonical v1 maturity remains 69/100. No open-PR credit is added.

Retained artifacts (30 days): default `12566086108`, integrations `12565559231`,
Trixie control `12565558851`. ZIP SHA-256 digests and every report-listed evidence
file hash were verified locally. The local v1 production-security scorecard and
`alpine-hardening-assessment-2026-10-24.json` record the results and blockers.

### Verified timeout and candidate-checker fixes

The authorized follow-up removes the unsupported connection-string timeout keyword
and passes the configured 1–300 second timeout through `mssql_python.connect(timeout=)`.
Encryption, server certificate validation, Entra authentication, allow-listed SQL
and parameterized values are unchanged. Injected one-argument connection factories
retain their existing interface.

The candidate checker now uses Python for non-root and filesystem privilege
inspection, including file capabilities, without requiring administrative CLI
tools. Alpine verification checks the preserved apk inventory hash, removed paths,
administrative command absence, dash shell and renamed BusyBox copies; missing or
invalid evidence fails closed. Debian verification and all scanner thresholds,
image archive identity checks and production-qualification restrictions remain.
Regression fixtures cover inventory tampering, restored commands, copied BusyBox,
invalid manifests, root users, privilege bits, capabilities and inspection errors.
The isolated matrix executes the actual candidate checker against both final
Alpine variants, plus the corrected SQL connector against Alpine and Trixie.
Live authentication/query and private-network qualification still require separate
evidence; these changes authorize no deployment or permission expansion.

The [completed follow-up run](https://github.com/faizrten/CEPIO/actions/runs/40110762560)
at `c1052ca88814c1f296a4673d3cba06950b83221f` closes the two implementation blockers
above. Both final Alpine variants pass the actual candidate checker, including
its independent archive-bound scan, inventory verification, non-root checks,
privilege-bit and file-capability rejection. Both scans agree on zero findings at
every severity and on the exact image identity. Both variants pass 1,183 source
tests (one Node-dependent skip covered by host CI) and 96 installed-wheel tests.
The Linux regression fixtures pass, including tampered inventory, restored
administrative commands, renamed BusyBox binaries, malformed manifests and
privilege regressions. Legitimate package records named `busybox` remain retained;
binary-copy detection compares content, and known command paths must be absent.
The Debian container CI also passes with the updated checker.

The real driver parser accepts CEPIO's corrected configuration on Alpine and
Trixie. The CEPIO connector using the supported timeout API sends an 88-byte TDS
prelogin packet on both and rejects the incomplete fixture connection. These are
isolated transport tests, not live authenticated Fabric query evidence.

Artifacts: default `12566845756`, integrations `12567030564`, Trixie control
`12566970375`. ZIP digests, report evidence hashes, nested candidate-checker hashes
and image/config identity agreement were independently verified locally. The local
security scorecard and `alpine-fixes-assessment-2026-10-24.json` record these verified
fixes without overwriting historical failed results.

**Remaining switch conditions:** live Fabric authentication and read-only query
qualification with the intended existing identity; private-network/DNS/TLS and
managed-identity evidence where used; reviewed production Dockerfile migration,
exact final artifact security/provenance qualification, and rollout/rollback
approval. The production Dockerfile still selects the existing base. No merge,
deployment, infrastructure change, cloud permission expansion or inference was
performed. Production remains G6 FAIL/HOLD and canonical maturity remains 69/100.

### Proposed default-runtime migration without Fabric

The user has confirmed Fabric is not provisioned. Live Fabric testing is deferred
and is not a blocker for qualification of the default runtime without Fabric.
The root Dockerfile now proposes the tested digest-pinned Alpine runtime and
reviewed version constraints, with the build hardener promoted to
`scripts/harden_alpine.py`. The branch workflow validates the actual root
Dockerfile in `nonfabric` mode; optional SQL transport is absent. Existing pure
unit tests may still cover its code, but no Fabric connection is attempted.
Named-volume persistence across separate containers supplements the prior
SQLite reopen check. Signed-token authorization and REST/Management/MCP tests run
against the installed wheel.

Verified root-Dockerfile run:
[40113997169](https://github.com/faizrten/CEPIO/actions/runs/40113997169), source
`3afa74ef37ac2a91795d74061f534261d42de5fa`, artifact `12567233053`.
Both archive-bound scans report zero findings at every severity and agree on image
identity. The runtime passes 1,183 source tests with one Node-dependent skip
covered by host CI, all 96 installed-wheel tests, native/TLS and REST/MCP checks,
and actual candidate-checker hardening/inventory checks. Named-volume SQLite data
written by one non-root container is reopened by a separate container. The SQL
driver is absent. No live Fabric test or public Microsoft metadata request ran.
Artifact ZIP, evidence-file and nested checker hashes were verified locally;
the scorecard records this in `nonfabric-migration-assessment-2026-10-24.json`.
This validates the proposed default image for review; deployment-specific identity,
startup/probe and volume ownership checks, exact release provenance and an
authorized rollout remain required. Production remains HOLD until then.

The [migration and rollback instructions](../operations/alpine-migration-rollback.md)
cover previous immutable image retention, identity/provenance, data and ownership
checks, rollback triggers, configuration preservation and post-rollback checks.
They require a separately authorized rollout and do not execute a deployment.
