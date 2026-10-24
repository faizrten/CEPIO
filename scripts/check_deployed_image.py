"""Read the deployed image; retain exact-digest evidence without rebuilding or signing."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


REGISTRY = "cepiodemo31d48.azurecr.io"
SCANNER = (
    "aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c"
)
REPOSITORY = "faizrten/CEPIO"
SEVERITIES = {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


def command(args, *, stdin=None, timeout=60):
    """Never echo credentials or untrusted command output into public logs."""
    try:
        result = subprocess.run(
            args, input=stdin, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("COMMAND_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode:
        raise ValueError("COMMAND_FAILED")
    return result.stdout


def target(digest, source, deployment):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("INVALID_DIGEST")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("INVALID_SOURCE")
    if not re.fullmatch(r"[1-9][0-9]{0,19}", deployment):
        raise ValueError("INVALID_DEPLOYMENT")
    return REGISTRY + "/cepio@" + digest


def scan_summary(data, image):
    if (
        data.get("SchemaVersion") != 2
        or data.get("ArtifactName") != image
        or image not in data.get("Metadata", {}).get("RepoDigests", [])
        or not data.get("Metadata", {}).get("OS", {}).get("Family")
        or not isinstance(data.get("Results"), list)
        or not data["Results"]
    ):
        raise ValueError("SCAN_SUBJECT_OR_SCHEMA_MISMATCH")
    counts = dict.fromkeys(sorted(SEVERITIES), 0)
    for result in data["Results"]:
        vulnerabilities = result.get("Vulnerabilities") or []
        if not isinstance(vulnerabilities, list):
            raise ValueError("INVALID_VULNERABILITY_LIST")
        for vulnerability in vulnerabilities:
            severity = vulnerability.get("Severity")
            if severity not in counts:
                raise ValueError("UNKNOWN_SEVERITY_SCHEMA")
            counts[severity] += 1
    return {
        "counts": counts,
        "qualified": not any(counts[x] for x in ("HIGH", "CRITICAL", "UNKNOWN")),
    }


def sbom_summary(data):
    if (
        data.get("bomFormat") != "CycloneDX"
        or data.get("specVersion") not in {"1.4", "1.5", "1.6", "1.7"}
        or not isinstance(data.get("components"), list)
        or not data["components"]
    ):
        raise ValueError("INVALID_OR_EMPTY_SBOM")
    versions = sorted(
        {item.get("version", "") for item in data["components"] if item.get("name") == "setuptools"}
    )
    patched = bool(versions) and all(
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
        and tuple(map(int, version.split("."))) >= (84, 1, 0)
        for version in versions
    )
    return {
        "component_count": len(data["components"]),
        "setuptools_versions": versions,
        "setuptools_patched": bool(patched),
        "qualified": bool(patched),
    }


def os_triage(data):
    """Group blocking OS entries without suppressing or reclassifying findings."""
    advisories = {}
    for result in data.get("Results", []):
        if result.get("Class") != "os-pkgs":
            continue
        for finding in result.get("Vulnerabilities") or []:
            if finding["Severity"] not in {"HIGH", "CRITICAL", "UNKNOWN"}:
                continue
            key = (finding["VulnerabilityID"], finding["Severity"])
            entry = advisories.setdefault(
                key,
                {"id": key[0], "severity": key[1], "packages": [], "disposition": "OPEN"},
            )
            entry["packages"].append(
                {
                    "name": finding["PkgName"],
                    "installed": finding.get("InstalledVersion", ""),
                    "fixed": finding.get("FixedVersion", ""),
                    "vendor_status": finding.get("Status", "unknown"),
                }
            )
    return {
        "advisories": [advisories[key] for key in sorted(advisories)],
        "blocking_package_entries": sum(len(x["packages"]) for x in advisories.values()),
        "limits": "Package attribution is not runtime reachability proof or a vulnerability waiver.",
    }


def provenance_discovery(digest):
    """Report only an allowlisted HTTP status/count; never echo API bodies/errors."""
    result = {"qualified": False, "evidence_type": "discovery_only_not_signature_verification"}
    try:
        response = subprocess.run(
            ["gh", "api", "--include", f"repos/{REPOSITORY}/attestations/{digest}?per_page=100"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        raw = response.stdout.replace("\r\n", "\n")
        status = re.match(r"HTTP/[0-9.]+ (200|401|403|404|429|500|502|503)\b", raw)
        result["http_status"] = int(status[1]) if status else None
        if response.returncode == 0 and result["http_status"] == 200:
            body = json.loads(raw.split("\n\n", 1)[1])
            records = body.get("attestations")
            if isinstance(records, list):
                result["first_page_record_count"] = len(records)
        result["interpretation"] = (
            "404 may mean absent or inaccessible; API discovery never establishes signature validity."
        )
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError, AttributeError):
        result["error"] = "DISCOVERY_UNAVAILABLE_OR_INVALID"
    return result


def provenance_summary(verified, digest):
    # Only call on successful gh attestation verify output, never raw bundle JSON.
    if not isinstance(verified, list) or not verified:
        raise ValueError("NO_VERIFIED_PROVENANCE")
    for item in verified:
        statement = item.get("verificationResult", {}).get("statement", {})
        if statement.get("predicateType") == "https://slsa.dev/provenance/v1" and any(
            subject.get("digest", {}).get("sha256") == digest.removeprefix("sha256:")
            for subject in statement.get("subject", [])
        ):
            return {"qualified": True, "predicate_type": "https://slsa.dev/provenance/v1"}
    raise ValueError("PROVENANCE_SUBJECT_MISMATCH")


def build_linkage(run, acr_run, source, image, deployment):
    if not (
        run.get("head_sha") == source
        and run.get("conclusion") == "success"
        and run.get("event") == "workflow_run"
        and run.get("path") == ".github/workflows/deploy-azure.yml"
        and run.get("repository", {}).get("full_name") == REPOSITORY
        and acr_run.get("status") == "Succeeded"
        and any(
            output.get("registry") == REGISTRY
            and output.get("repository") == "cepio"
            and output.get("digest") == image.split("@", 1)[1]
            and output.get("tag") == f"{source}-{deployment}-{run.get('run_attempt')}"
            for output in acr_run.get("outputImages", [])
        )
    ):
        raise ValueError("DEPLOYMENT_LINKAGE_MISMATCH")
    return {"qualified": True, "evidence_type": "github_and_acr_records_not_signed_provenance"}


def current_image():
    if os.environ.get("APP_NAME") != "cepio-demo-31d48" or not os.environ.get("RESOURCE_GROUP"):
        raise ValueError("UNEXPECTED_AZURE_TARGET")
    return command(
        [
            "az",
            "webapp",
            "config",
            "show",
            "--resource-group",
            os.environ["RESOURCE_GROUP"],
            "--name",
            os.environ["APP_NAME"],
            "--query",
            "linuxFxVersion",
            "--output",
            "tsv",
            "--only-show-errors",
        ]
    ).strip()


def scanner_command(evidence, docker_config, cache):
    # Root-owned cache directories can make TemporaryDirectory cleanup fail on
    # hosted runners. Keep every scanner-created file owned by the runner.
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    gid = os.getgid() if hasattr(os, "getgid") else 1000
    if uid == 0:
        raise ValueError("SCANNER_RUNNER_MUST_BE_NONROOT")
    return [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{uid}:{gid}",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "-e",
        "HOME=/tmp",
        "-e",
        "DOCKER_CONFIG=/docker",
        "-v",
        f"{docker_config.resolve()}:/docker:ro",
        "-v",
        f"{cache.resolve()}:/cache",
        "-v",
        f"{evidence.resolve()}:/evidence",
        SCANNER,
        "image",
        "--cache-dir",
        "/cache",
        "--image-src",
        "remote",
        "--timeout",
        "10m",
        "--scanners",
        "vuln",
    ]


def safe_failure(stage, error):
    allowed = {
        "INVALID_DIGEST",
        "INVALID_SOURCE",
        "INVALID_DEPLOYMENT",
        "INVALID_ACR_RUN",
        "UNEXPECTED_AZURE_TARGET",
        "DEPLOYED_IMAGE_CHANGED_OR_MISMATCHED",
        "COMMAND_FAILED",
        "COMMAND_UNAVAILABLE_OR_TIMEOUT",
        "SCANNER_RUNNER_MUST_BE_NONROOT",
    }
    code = str(error) if isinstance(error, ValueError) and str(error) in allowed else "CHECK_FAILED"
    return {"stage": stage, "type": type(error).__name__, "code": code}


def main():
    evidence = Path("evidence/deployed-image")
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"qualified": False, "checks": {}, "errors": [], "scanner_image": SCANNER}
    stage, initial_target_confirmed, image = "inputs", False, None
    try:
        digest = os.environ["EXPECTED_DIGEST"]
        source, deployment = os.environ["SOURCE_SHA"], os.environ["DEPLOYMENT_RUN_ID"]
        image = target(digest, source, deployment)
        report.update(image=image, deployed_source_sha=source, deployment_run_id=int(deployment))
        stage = "target-before"
        if current_image() != "DOCKER|" + image:
            raise ValueError("DEPLOYED_IMAGE_CHANGED_OR_MISMATCHED")
        initial_target_confirmed = True
        stage = "build-linkage"
        acr_run_id = os.environ["ACR_RUN_ID"]
        if not re.fullmatch(r"[a-z0-9]{1,64}", acr_run_id):
            raise ValueError("INVALID_ACR_RUN")
        try:
            run = json.loads(
                command(["gh", "api", f"repos/{REPOSITORY}/actions/runs/{deployment}"])
            )
            acr_run = json.loads(
                command(
                    [
                        "az",
                        "acr",
                        "task",
                        "show-run",
                        "--registry",
                        "cepiodemo31d48",
                        "--run-id",
                        acr_run_id,
                        "--output",
                        "json",
                        "--only-show-errors",
                    ]
                )
            )
            report["checks"]["build_linkage"] = build_linkage(
                run, acr_run, source, image, deployment
            )
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            report["checks"]["build_linkage"] = {
                "qualified": False,
                "error": "BUILD_LINKAGE_UNAVAILABLE_OR_MISMATCHED",
            }
        with tempfile.TemporaryDirectory(prefix="cepio-image-") as temporary:
            docker_config = Path(temporary) / "docker"
            docker_config.mkdir(mode=0o700)
            cache = Path(temporary) / "cache"
            cache.mkdir()
            stage = "registry-login"
            credential = json.loads(
                command(
                    [
                        "az",
                        "acr",
                        "login",
                        "--name",
                        "cepiodemo31d48",
                        "--expose-token",
                        "--output",
                        "json",
                        "--only-show-errors",
                    ]
                )
            )
            command(
                [
                    "docker",
                    "--config",
                    str(docker_config),
                    "login",
                    REGISTRY,
                    "--username",
                    "00000000-0000-0000-0000-000000000000",
                    "--password-stdin",
                ],
                stdin=credential["accessToken"],
            )
            del credential
            scan = scanner_command(evidence, docker_config, cache)
            for name, options, summarize in [
                (
                    "scan",
                    [
                        "--format",
                        "json",
                        "--list-all-pkgs",
                        "--exit-code",
                        "0",
                        "--output",
                        "/evidence/container-vulnerabilities.json",
                    ],
                    lambda: scan_summary(
                        json.loads((evidence / "container-vulnerabilities.json").read_text()), image
                    ),
                ),
                (
                    "sbom",
                    ["--format", "cyclonedx", "--output", "/evidence/container-sbom.json"],
                    lambda: sbom_summary(
                        json.loads((evidence / "container-sbom.json").read_text())
                    ),
                ),
            ]:
                stage = name
                try:
                    command(scan + options + [image], timeout=660)
                    report["checks"][name] = summarize()
                except (ValueError, OSError, KeyError, TypeError, AttributeError):
                    report["checks"][name] = {
                        "qualified": False,
                        "error": "SCAN_OR_SBOM_UNAVAILABLE_OR_INVALID",
                    }
            # gh uses the temporary registry login, not a new permission grant.
            stage = "signed-provenance"
            report["provenance_discovery"] = provenance_discovery(digest)
            old_config = os.environ.get("DOCKER_CONFIG")
            os.environ["DOCKER_CONFIG"] = str(docker_config)
            try:
                verified = json.loads(
                    command(
                        [
                            "gh",
                            "attestation",
                            "verify",
                            "oci://" + image,
                            "--repo",
                            REPOSITORY,
                            "--signer-workflow",
                            REPOSITORY + "/.github/workflows/deploy-azure.yml",
                            "--source-digest",
                            source,
                            "--source-ref",
                            "refs/heads/main",
                            "--deny-self-hosted-runners",
                            "--predicate-type",
                            "https://slsa.dev/provenance/v1",
                            "--format",
                            "json",
                        ],
                        timeout=180,
                    )
                )
                report["checks"]["signed_provenance"] = provenance_summary(verified, digest)
                (evidence / "verified-provenance.json").write_text(
                    json.dumps(verified, indent=2) + "\n"
                )
            except (ValueError, OSError, KeyError, TypeError, AttributeError):
                report["checks"]["signed_provenance"] = {
                    "qualified": False,
                    "error": "VERIFICATION_UNAVAILABLE_OR_FAILED",
                }
            finally:
                if old_config is None:
                    os.environ.pop("DOCKER_CONFIG", None)
                else:
                    os.environ["DOCKER_CONFIG"] = old_config
            stage = "temporary-cleanup"
    except (ValueError, OSError, KeyError, TypeError, AttributeError, StopIteration) as error:
        report["errors"].append(safe_failure(stage, error))
    finally:
        # A cleanup failure must not suppress the independent final target read.
        if initial_target_confirmed:
            try:
                same = current_image() == "DOCKER|" + image
                report["checks"]["target_consistency"] = {"qualified": same}
            except (ValueError, OSError, KeyError, TypeError, AttributeError) as error:
                report["checks"]["target_consistency"] = {"qualified": False}
                report["errors"].append(safe_failure("target-after", error))
    report["qualified"] = not report["errors"] and all(
        report["checks"].get(name, {}).get("qualified") is True
        for name in ("build_linkage", "scan", "sbom", "signed_provenance", "target_consistency")
    )
    scan_path = evidence / "container-vulnerabilities.json"
    if scan_path.exists():
        try:
            triage = os_triage(json.loads(scan_path.read_text()))
            (evidence / "os-triage.json").write_text(json.dumps(triage, indent=2) + "\n")
        except (ValueError, KeyError, TypeError, AttributeError):
            report["errors"].append({"stage": "os-triage", "code": "INVALID_TRIAGE_INPUT"})
            report["qualified"] = False
    report["files_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in evidence.glob("*.json")
        if path.name != "manifest.json"
    }
    report["limits"] = (
        "Registry reads only; no rebuild, deployment, signing, grants or inference. Build linkage is not signed provenance."
    )
    (evidence / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("DEPLOYED_IMAGE_EVIDENCE " + json.dumps(report, sort_keys=True))
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(
            "## Deployed image evidence\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n"
        )
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
