# Alternative base-image experiment

This directory evaluates supported replacements without changing the production
Dockerfile. Only the `security/base-image-evaluation` branch triggers the isolated
matrix. Its sole token permission is `contents: read`; there is no environment,
cloud login, registry push, signing, deployment or model invocation.

The matrix compares digest-pinned Python 3.11.17 on Trixie (control), Bookworm
(glibc/LTS) and Alpine 3.24 (musl), plus Ubuntu 24.04's packaged Python 3.12.
Runtime Python constraints come from PR300's checksum-verified candidate SBOM to
avoid crediting unrelated Python dependency upgrades to the base migration.
These are experiment controls, not a proposed production dependency lockfile.

For each built runtime, retain an identity-bound full vulnerability report and
SBOM using the same pinned Trivy version as the deployed-image gate. No severity
or unfixed issue is ignored. Preserve the actual distro inventory and report
HIGH/CRITICAL/UNKNOWN as blockers. Check native libraries, trust, DNS, timezones,
SQLite, UUID, JWT, nonroot identity, privilege bits, REST health, MCP auth denial,
initialization and tool listing against the installed wheel. Run the full source
suite under that OS/Python with networking disabled. Separately probe declared
optional MCP/OpenTelemetry/Fabric SQL extras; a default-runtime pass is not proof
that every optional integration works.

The test image adds development dependencies and git; it is never the scanned
runtime. Docker builds and vulnerability DB acquisition use public package
sources. Tests receive no cloud secrets or credentials. Candidate artifacts and
their checksums are evidence, not production qualification. `report.json`
distinguishes successful experiment execution from candidate eligibility.

Support references checked 2026-10-24:

- [Official Python image tags](https://github.com/docker-library/official-images/blob/master/library/python).
- [Python lifecycle](https://devguide.python.org/versions/): Python 3.11 security support through October 2027; Python 3.12 through October 2028.
- [Alpine releases](https://alpinelinux.org/releases/): 3.24 main support through June 2028; community support follows the next stable release.
- [Debian Bookworm](https://www.debian.org/releases/bookworm/): LTS through June 2028, limited architectures/package scope.
- [Ubuntu lifecycle](https://ubuntu.com/about/release-cycle): 24.04 standard main-repository security maintenance through May 2029; Universe/Pro coverage must not be assumed.

Only linux/amd64 is tested. Vendor advisory databases differ, so a lower scan
count is not itself a reachability determination. Alpine's BusyBox may expose
administrative applets through its multicall binary even after CLI links are
removed. Optional extras probes do not establish live connectivity, customer
workload parity, ARM64 parity, performance/SLOs or deployed provenance.
