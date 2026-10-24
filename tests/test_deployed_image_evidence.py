"""Negative controls for exact deployed-image evidence; no registry or model calls."""

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "image_probe", Path(__file__).resolve().parents[1] / "scripts/check_deployed_image.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
DIGEST = "sha256:" + "a" * 64
SOURCE = "b" * 40
IMAGE = probe.REGISTRY + "/cepio@" + DIGEST


def scan():
    return {
        "SchemaVersion": 2,
        "ArtifactName": IMAGE,
        "Metadata": {"RepoDigests": [IMAGE], "OS": {"Family": "debian"}},
        "Results": [{"Class": "os-pkgs", "Vulnerabilities": []}],
    }


def sbom():
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [{"name": "setuptools", "version": "84.1.0"}],
    }


def verified():
    return [
        {
            "verificationResult": {
                "statement": {
                    "predicateType": "https://slsa.dev/provenance/v1",
                    "subject": [{"digest": {"sha256": "a" * 64}}],
                }
            }
        }
    ]


def run_record():
    return {
        "head_sha": SOURCE,
        "conclusion": "success",
        "event": "workflow_run",
        "path": ".github/workflows/deploy-azure.yml",
        "run_attempt": 1,
        "repository": {"full_name": "faizrten/CEPIO"},
    }


def acr_record():
    return {
        "status": "Succeeded",
        "outputImages": [
            {
                "registry": probe.REGISTRY,
                "repository": "cepio",
                "digest": DIGEST,
                "tag": SOURCE + "-123-1",
            }
        ],
    }


@pytest.mark.parametrize(
    "digest,source,run",
    [
        ("latest", SOURCE, "123"),
        (DIGEST, "main", "123"),
        (DIGEST, SOURCE, "123;malicious"),
        (DIGEST, SOURCE, "0"),
    ],
)
def test_untrusted_target_inputs_rejected(digest, source, run):
    with pytest.raises(ValueError):
        probe.target(digest, source, run)


def test_exact_digest_target_and_clean_scan():
    assert probe.target(DIGEST, SOURCE, "123") == IMAGE
    assert probe.scan_summary(scan(), IMAGE)["qualified"]


@pytest.mark.parametrize(
    "severity,expected",
    [("CRITICAL", False), ("HIGH", False), ("UNKNOWN", False), ("MEDIUM", True)],
)
def test_unfixed_and_unknown_findings_block(severity, expected):
    data = scan()
    data["Results"][0]["Vulnerabilities"] = [{"Severity": severity, "FixedVersion": ""}]
    assert probe.scan_summary(data, IMAGE)["qualified"] is expected


@pytest.mark.parametrize(
    "change", [{"ArtifactName": "other"}, {"SchemaVersion": 1}, {"Results": []}, {"Metadata": {}}]
)
def test_scan_subject_and_inventory_fail_closed(change):
    with pytest.raises(ValueError):
        probe.scan_summary({**scan(), **change}, IMAGE)


@pytest.mark.parametrize(
    "version,expected",
    [("84.0.0", False), ("84.1.0", True), ("85.0.0", True), ("84.1.0rc1", False)],
)
def test_inventory_confirms_patched_setuptools(version, expected):
    data = sbom()
    data["components"][0]["version"] = version
    assert probe.sbom_summary(data)["qualified"] is expected


def test_empty_or_wrong_sbom_and_missing_setuptools():
    for data in ({}, {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}):
        with pytest.raises(ValueError):
            probe.sbom_summary(data)
    data = sbom()
    data["components"] = [{"name": "other", "version": "1.0.0"}]
    assert not probe.sbom_summary(data)["qualified"]


def test_verified_provenance_requires_exact_subject_and_predicate():
    assert probe.provenance_summary(verified(), DIGEST)["qualified"]
    for data in ([], {}, [{"verificationResult": {"statement": {}}}]):
        with pytest.raises(ValueError):
            probe.provenance_summary(data, DIGEST)
    with pytest.raises(ValueError):
        probe.provenance_summary(verified(), "sha256:" + "c" * 64)


def test_unsigned_build_linkage_is_distinct_and_rejects_other_source_or_digest():
    result = probe.build_linkage(run_record(), acr_record(), SOURCE, IMAGE, "123")
    assert result["qualified"] and "not_signed" in result["evidence_type"]
    for run, acr in [
        ({**run_record(), "head_sha": "wrong"}, acr_record()),
        (run_record(), {**acr_record(), "status": "Failed"}),
        (run_record(), {**acr_record(), "outputImages": []}),
    ]:
        with pytest.raises(ValueError):
            probe.build_linkage(run, acr, SOURCE, IMAGE, "123")


@pytest.mark.parametrize("failure", [None, "provenance", "drift", "linkage", "scan", "cleanup"])
def test_full_readonly_report_retains_independent_failures_and_no_credentials(
    monkeypatch, tmp_path, capsys, failure
):
    monkeypatch.chdir(tmp_path)
    if failure == "cleanup":
        from contextlib import contextmanager

        original = probe.tempfile.TemporaryDirectory

        @contextmanager
        def cleanup_failure(*args, **kwargs):
            with original(*args, **kwargs) as directory:
                yield directory
            raise PermissionError("SECRET cleanup details")

        monkeypatch.setattr(probe.tempfile, "TemporaryDirectory", cleanup_failure)
    for name, value in {
        "EXPECTED_DIGEST": DIGEST,
        "SOURCE_SHA": SOURCE,
        "DEPLOYMENT_RUN_ID": "123",
        "ACR_RUN_ID": "cb7",
        "APP_NAME": "cepio-demo-31d48",
        "RESOURCE_GROUP": "test-group",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("DOCKER_CONFIG", raising=False)
    current = iter(["DOCKER|" + IMAGE, "DOCKER|other" if failure == "drift" else "DOCKER|" + IMAGE])
    monkeypatch.setattr(probe, "current_image", lambda: next(current))
    monkeypatch.setattr(probe, "provenance_discovery", lambda digest: {"http_status": 404})
    calls = []

    def command(args, *, stdin=None, timeout=60):
        calls.append(args)
        if args[:2] == ["gh", "api"]:
            return json.dumps(run_record())
        if args[:4] == ["az", "acr", "task", "show-run"]:
            if failure == "linkage":
                raise ValueError("SECRET")
            return json.dumps(acr_record())
        if args[:3] == ["az", "acr", "login"]:
            return json.dumps({"accessToken": "PRIVATE_REGISTRY_CREDENTIAL"})
        if "login" in args:
            assert stdin == "PRIVATE_REGISTRY_CREDENTIAL"
            return ""
        if args[:3] == ["docker", "run", "--rm"]:
            evidence = tmp_path / "evidence/deployed-image"
            if "cyclonedx" in args:
                (evidence / "container-sbom.json").write_text(json.dumps(sbom()))
            else:
                if failure == "scan":
                    raise ValueError("SECRET")
                (evidence / "container-vulnerabilities.json").write_text(json.dumps(scan()))
            assert "--image-src" in args and args[-1] == IMAGE
            assert "/var/run/docker.sock" not in " ".join(args)
            return ""
        assert args[:3] == ["gh", "attestation", "verify"]
        assert "--source-digest" in args and SOURCE in args and "--deny-self-hosted-runners" in args
        if failure == "provenance":
            raise ValueError("SECRET")
        return json.dumps(verified())

    monkeypatch.setattr(probe, "command", command)
    assert probe.main() == (0 if failure is None else 1)
    report = json.loads((tmp_path / "evidence/deployed-image/manifest.json").read_text())
    assert report["qualified"] is (failure is None)
    assert report["checks"]["sbom"]["qualified"]
    assert report["checks"]["target_consistency"]["qualified"] is (failure != "drift")
    if failure == "cleanup":
        assert report["errors"] == [
            {"stage": "temporary-cleanup", "type": "PermissionError", "code": "CHECK_FAILED"}
        ]

    assert all(len(value) == 64 for value in report["files_sha256"].values())
    login = next(args for args in calls if "--config" in args)
    assert not Path(login[login.index("--config") + 1]).exists()
    assert "DOCKER_CONFIG" not in probe.os.environ
    output = capsys.readouterr().out + (tmp_path / "summary").read_text()
    assert "SECRET" not in output and "PRIVATE_REGISTRY_CREDENTIAL" not in output
    assert not any("build" in args or "restart" in args or "set" in args for args in calls)


def test_subprocess_failure_never_echoes_secrets(monkeypatch):
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout="SECRET", stderr="SECRET"),
    )
    with pytest.raises(ValueError, match="^COMMAND_FAILED$"):
        probe.command(["read-only-tool"], stdin="SECRET")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("SECRET", 1)

    monkeypatch.setattr(probe.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="^COMMAND_UNAVAILABLE_OR_TIMEOUT$"):
        probe.command(["read-only-tool"])


def test_current_image_reads_only_expected_app(monkeypatch):
    monkeypatch.setenv("APP_NAME", "other")
    with pytest.raises(ValueError, match="UNEXPECTED_AZURE_TARGET"):
        probe.current_image()
    monkeypatch.setenv("APP_NAME", "cepio-demo-31d48")
    monkeypatch.setenv("RESOURCE_GROUP", "test-group")
    seen = []

    def command(args):
        seen.append(args)
        return "DOCKER|" + IMAGE + "\n"

    monkeypatch.setattr(probe, "command", command)
    assert probe.current_image() == "DOCKER|" + IMAGE
    assert seen[0][:4] == ["az", "webapp", "config", "show"]
    assert seen[0][seen[0].index("--query") + 1] == "linuxFxVersion"


def test_invalid_target_retains_failure_manifest_without_external_calls(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EXPECTED_DIGEST", "latest")
    monkeypatch.setenv("SOURCE_SHA", SOURCE)
    monkeypatch.setenv("DEPLOYMENT_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid inputs must not reach Azure or registry")

    monkeypatch.setattr(probe, "command", unexpected)
    assert probe.main() == 1
    report = json.loads((tmp_path / "evidence/deployed-image/manifest.json").read_text())
    assert not report["qualified"] and report["errors"]


def test_workflow_preserves_main_oidc_and_readonly_permissions():
    import yaml

    root = Path(__file__).resolve().parents[1]
    data = yaml.safe_load((root / ".github/workflows/deployed-image-readonly.yml").read_text())
    job = data["jobs"]["evidence"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "azure-demo"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    steps = job["steps"]
    assert steps[0]["with"]["ref"] == "refs/heads/main"
    assert steps[0]["with"]["persist-credentials"] is False
    assert steps[-1]["if"] == "always()"
    assert steps[-1]["with"]["path"] == "evidence/deployed-image/"


def test_scanner_runs_as_runner_with_owned_cache_and_no_root_home(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.os, "getuid", lambda: 1001, raising=False)
    monkeypatch.setattr(probe.os, "getgid", lambda: 127, raising=False)
    args = probe.scanner_command(tmp_path, tmp_path / "docker", tmp_path / "cache")
    assert args[args.index("--user") + 1] == "1001:127"
    assert "HOME=/tmp" in args and "DOCKER_CONFIG=/docker" in args
    assert "/root" not in " ".join(args)
    assert args[args.index("--cache-dir") + 1] == "/cache"
    monkeypatch.setattr(probe.os, "getuid", lambda: 0)
    with pytest.raises(ValueError, match="SCANNER_RUNNER_MUST_BE_NONROOT"):
        probe.scanner_command(tmp_path, tmp_path, tmp_path)


def test_os_triage_preserves_package_entries_and_unknowns_without_waivers():
    data = scan()
    data["Results"][0]["Vulnerabilities"] = [
        {"VulnerabilityID": "CVE-1", "Severity": "HIGH", "PkgName": name}
        for name in ["library", "utility"]
    ] + [{"VulnerabilityID": "CVE-2", "Severity": "UNKNOWN", "PkgName": "other"}]
    result = probe.os_triage(data)
    assert result["blocking_package_entries"] == 3
    assert len(result["advisories"]) == 2
    assert all(x["disposition"] == "OPEN" for x in result["advisories"])
    assert not probe.scan_summary(data, IMAGE)["qualified"]


@pytest.mark.parametrize("status,count", [(200, 1), (404, None), (403, None)])
def test_provenance_discovery_never_counts_as_verification(monkeypatch, status, count):
    def run(args, **kwargs):
        assert args[:3] == ["gh", "api", "--include"]
        assert DIGEST in args[-1]
        return SimpleNamespace(
            returncode=0 if status == 200 else 1,
            stdout=f"HTTP/2.0 {status} Status\nHeader: SECRET\n\n"
            + json.dumps({"attestations": ["SECRET"]}),
            stderr="SECRET bearer token",
        )

    monkeypatch.setattr(probe.subprocess, "run", run)
    result = probe.provenance_discovery(DIGEST)
    assert result["http_status"] == status
    assert result.get("first_page_record_count") == count
    assert not result["qualified"] and "SECRET" not in json.dumps(result)


def test_provenance_discovery_timeout_stays_unverified(monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("SECRET", 60)

    monkeypatch.setattr(probe.subprocess, "run", run)
    result = probe.provenance_discovery(DIGEST)
    assert not result["qualified"] and "SECRET" not in json.dumps(result)
