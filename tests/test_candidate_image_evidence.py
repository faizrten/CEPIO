import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "check_deployed_image", SCRIPTS / "check_deployed_image.py"
)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
sys.modules.setdefault("check_deployed_image", helper)
SPEC = importlib.util.spec_from_file_location(
    "candidate_probe", SCRIPTS / "check_candidate_image.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
IMAGE_ID = "sha256:" + "a" * 64


def scan():
    return {
        "SchemaVersion": 2,
        "Metadata": {"ImageID": IMAGE_ID},
        "Results": [
            {
                "Class": "os-pkgs",
                "Vulnerabilities": [
                    {"Severity": "HIGH", "PkgName": "os-lib", "VulnerabilityID": "OS-UNFIXED"}
                ],
            },
            {"Class": "lang-pkgs", "Vulnerabilities": []},
        ],
    }


def sbom():
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [{"name": "setuptools", "version": "84.2.1"}],
    }


def test_targeted_remediation_preserves_remaining_os_release_failure():
    result = probe.summarize(scan(), sbom(), IMAGE_ID)
    assert result["targeted_remediation_passed"]
    assert not result["image_vulnerability_policy_passed"]
    assert not result["production_qualified"]
    assert result["counts"]["HIGH"] == 1


@pytest.mark.parametrize("severity", ["HIGH", "CRITICAL", "UNKNOWN"])
def test_remaining_language_findings_block_targeted_fix(severity):
    data = scan()
    data["Results"][1]["Vulnerabilities"] = [
        {"Severity": severity, "PkgName": "vendor", "VulnerabilityID": "PYTHON-FINDING"}
    ]
    result = probe.summarize(data, sbom(), IMAGE_ID)
    assert not result["targeted_remediation_passed"] and result["python_blockers"]


@pytest.mark.parametrize(
    "component", [{"name": "pip", "version": "26.2.2"}, {"name": "setuptools", "version": "70.3.0"}]
)
def test_old_tooling_inventory_blocks_remediation(component):
    data = sbom()
    data["components"].append(component)
    assert not probe.summarize(scan(), data, IMAGE_ID)["targeted_remediation_passed"]


def test_other_candidate_image_rejected():
    with pytest.raises(ValueError, match="CANDIDATE_IMAGE_ID_MISMATCH"):
        probe.summarize(scan(), sbom(), "sha256:" + "b" * 64)


@pytest.mark.parametrize(
    "files,uid",
    [
        ("{}", "100"),
        ('{"setuid_setgid_files": 0, "file_capabilities": 0}', "0"),
        ('{"setuid_setgid_files": 0, "file_capabilities": 0}', "invalid"),
    ],
)
def test_runtime_privilege_regressions_block_candidate(monkeypatch, files, uid):
    responses = iter([files, uid])
    monkeypatch.setattr(probe, "command", lambda args: next(responses))
    with pytest.raises(ValueError):
        probe.runtime_hardening()


def test_runtime_hardening_checks_all_files_as_root_without_network(monkeypatch):
    calls = []

    def command(args):
        calls.append(args)
        return (
            "100"
            if "print(os.getuid())" in args[-1]
            else '{"setuid_setgid_files": 0, "file_capabilities": 0}'
        )

    monkeypatch.setattr(probe, "command", command)
    assert probe.runtime_hardening() == {
        "nonroot": True,
        "setuid_setgid_files": 0,
        "file_capabilities": 0,
    }
    assert "0" in calls[0] and "0o6000" in calls[0][-1]
    assert all("--read-only" in args and "none" in args for args in calls)


def test_exported_config_hash_tag_and_layer_chain_bind_candidate(tmp_path):
    import io
    import json
    import hashlib
    import tarfile

    path = tmp_path / "candidate.tar"
    layers = ["sha256:" + "c" * 64]
    config = json.dumps({"rootfs": {"diff_ids": layers}}).encode()
    with tarfile.open(path, "w") as archive:
        for name, data in [
            (
                "manifest.json",
                json.dumps([{"Config": "config.json", "RepoTags": ["cepio:ci"]}]).encode(),
            ),
            ("config.json", config),
        ]:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    assert probe.archive_identity(path, layers) == "sha256:" + hashlib.sha256(config).hexdigest()
    with pytest.raises(ValueError, match="CANDIDATE_ARCHIVE_LAYER_MISMATCH"):
        probe.archive_identity(path, ["wrong"])
