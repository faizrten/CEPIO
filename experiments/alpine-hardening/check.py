"""Qualify two isolated Alpine runtime variants without cloud credentials or deployment."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
variant = sys.argv[1]
assert variant in {"default", "integrations", "trixie-control", "nonfabric"}
arguments = sys.argv[:]
sys.argv = ["evaluate.py", "trixie" if variant == "trixie-control" else "alpine324"]
spec = importlib.util.spec_from_file_location(
    "base_evaluator", ROOT / "experiments/base-images/evaluate.py"
)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)
sys.argv = arguments
evaluation.EVIDENCE = ROOT / "evidence/alpine-hardening" / variant
evaluation.EVIDENCE.mkdir(parents=True, exist_ok=True)
evaluation.DOCKERFILE = (
    "Dockerfile" if variant == "nonfabric" else "experiments/alpine-hardening/Dockerfile"
)
report = evaluation.REPORT
report["variant"] = variant
report["extras"] = "mcp" if variant in {"default", "nonfabric"} else "mcp,otel,fabric-sql"
report["production_qualified"] = False
run = evaluation.run
probe = ROOT / "experiments/alpine-hardening/runtime_probe.py"

PRIVILEGES = """
import json, os, stat
findings=[]
for directory, dirs, files in os.walk('/', followlinks=False):
    if directory == '/': dirs[:] = [d for d in dirs if d not in {'proc','dev','sys'}]
    for name in files:
        path=os.path.join(directory, name)
        metadata=os.lstat(path)
        if stat.S_ISREG(metadata.st_mode):
            if metadata.st_mode & 0o6000: findings.append(path)
            if 'security.capability' in os.listxattr(path): findings.append(path + ':capability')
print(json.dumps(findings))
assert not findings
"""

INTEGRATION_TESTS = [
    "test_fabric_sql_reader_v01.py",
    "test_fabric_iq_binding.py",
    "test_hosted_mcp_v01.py",
    "test_management_api_v01.py",
    "test_management_contract_v01.py",
    "test_authorization_negative_matrix.py",
    "test_authenticated_host_diagnostics.py",
    "test_remote_management_read_v01.py",
]


def require(label, command, timeout=900):
    code, output = run(label, command, timeout)
    assert code == 0, f"{label} failed: see {label}.log"
    return output


def probe_result(output, required_key):
    """Docker stdout/stderr frames can arrive in either order; select the schema."""
    matches = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and required_key in value:
            matches.append(value)
    assert len(matches) == 1, "Expected exactly one probe result"
    return matches[0]


def main():
    if variant == "trixie-control":
        require(
            "control-build",
            [
                "docker",
                "build",
                "--target",
                "optional-probe",
                "-f",
                "experiments/base-images/Dockerfile.trixie",
                "-t",
                "cepio:control",
                ".",
            ],
        )
        output = require(
            "control-sql-probe",
            [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "none",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--tmpfs",
                "/tmp:rw",
                "-v",
                f"{probe}:/probe.py:ro",
                "--entrypoint",
                "python",
                "cepio:control",
                "/probe.py",
                "sql",
            ],
            timeout=90,
        )
        report["sql_control"] = probe_result(output, "tds_prelogin")
        assert report["sql_control"]["cepio_connection_configuration"]["accepted"]
        report["isolated_checks_passed"] = True
        return
    require(
        "runtime-build",
        [
            "docker",
            "build",
            "--pull",
            "--target",
            "runtime",
            "--build-arg",
            "CEPIO_RUNTIME_EXTRAS=" + report["extras"],
            "-f",
            evaluation.DOCKERFILE,
            "-t",
            "cepio:ci",
            ".",
        ],
    )
    # Retain full final-image security evidence even if a later integration fails.
    evaluation.scan_runtime()
    require(
        "runtime-minimization-verifier",
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--user",
            "0",
            "--entrypoint",
            "python",
            "cepio:ci",
            "-c",
            (ROOT / "scripts/minimize_runtime.py").read_text(),
        ],
    )
    restrictions = ["--rm", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges"]
    native = require(
        "native-smoke",
        [
            "docker",
            "run",
            *restrictions,
            "--network",
            "none",
            "--entrypoint",
            "python",
            "cepio:ci",
            "-c",
            evaluation.NATIVE,
        ],
    )
    report["native_smoke"] = json.loads(native)
    if variant == "nonfabric":
        report["fabric_qualification"] = (
            "DEFERRED: no Fabric environment; driver absent from default runtime"
        )
        report["runtime_dockerfile"] = "Dockerfile"
        volume = require("volume-create", ["docker", "volume", "create"]).strip()
        try:
            for phase in ("write", "reopen"):
                code = (
                    "import os,sqlite3; assert os.getuid()!=0; "
                    "c=sqlite3.connect('/data/nonfabric.sqlite'); "
                    + (
                        "c.execute('CREATE TABLE fixture(value TEXT)'); c.execute(\"INSERT INTO fixture VALUES ('preserved')\"); c.commit()"
                        if phase == "write"
                        else "assert c.execute('SELECT value FROM fixture').fetchone()==('preserved',)"
                    )
                )
                require(
                    "persistent-volume-" + phase,
                    [
                        "docker",
                        "run",
                        *restrictions,
                        "--network",
                        "none",
                        "-v",
                        volume + ":/data",
                        "--entrypoint",
                        "python",
                        "cepio:ci",
                        "-c",
                        code,
                    ],
                )
            report["persistent_volume_across_containers"] = True
        finally:
            require("volume-remove", ["docker", "volume", "rm", volume])
    require(
        "privilege-bits",
        [
            "docker",
            "run",
            *restrictions,
            "--network",
            "none",
            "--user",
            "0",
            "--entrypoint",
            "python",
            "cepio:ci",
            "-c",
            PRIVILEGES,
        ],
    )
    report["privilege_bits_and_file_capabilities_absent"] = True
    offline = require(
        "hardening-integrations",
        [
            "docker",
            "run",
            *restrictions,
            "--network",
            "none",
            "--tmpfs",
            "/tmp:rw",
            "--tmpfs",
            "/data:rw,mode=1777",
            "-v",
            f"{probe}:/probe.py:ro",
            "--entrypoint",
            "python",
            "cepio:ci",
            "/probe.py",
            variant,
        ],
        timeout=90,
    )
    report["runtime_integrations"] = probe_result(offline, "hardening_passed")
    if variant != "nonfabric":
        online = require(
            "public-dns-https",
            [
                "docker",
                "run",
                *restrictions,
                "-v",
                f"{probe}:/probe.py:ro",
                "--entrypoint",
                "python",
                "cepio:ci",
                "/probe.py",
                "online",
            ],
            timeout=60,
        )
        report["public_dns_https"] = json.loads(online)
    evaluation.hosted_smoke()
    assert report.get("hosted_smoke", {}).get("passed")
    require(
        "tests-build",
        [
            "docker",
            "build",
            "--target",
            "test-runner",
            "-f",
            "experiments/alpine-hardening/Dockerfile",
            "-t",
            "cepio:test",
            ".",
        ],
    )
    require(
        "source-suite",
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cap-drop=ALL",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-e",
            "HOME=/tmp",
            "--security-opt=no-new-privileges",
            "--tmpfs",
            "/tmp:exec",
            "-v",
            f"{ROOT}:/work:ro",
            "-v",
            f"{evaluation.EVIDENCE}:/evidence",
            "cepio:test",
            "python",
            "-c",
            "import os,shutil;shutil.copytree('/work','/tmp/source');os.chdir('/tmp/source');os.execvp('python',['python','-m','pytest','-q','-p','no:cacheprovider','--basetemp=/tmp/pytest','--junitxml=/evidence/source-tests.xml'])",
        ],
    )
    report["source_tests"] = (
        ET.parse(evaluation.EVIDENCE / "source-tests.xml").getroot().find("testsuite").attrib
    )
    with tempfile.TemporaryDirectory(prefix="cepio-alpine-tools-") as temp:
        cid = require("test-tools-create", ["docker", "create", "cepio:test"]).strip()
        try:
            require("test-tools-copy", ["docker", "cp", f"{cid}:/test-tools", temp])
        finally:
            require("test-tools-remove", ["docker", "rm", cid])
        pytest_args = [
            "-q",
            "-c",
            "/dev/null",
            "--import-mode=importlib",
            "-p",
            "no:cacheprovider",
            "--junitxml=/evidence/installed-tests.xml",
            *["tests/" + name for name in INTEGRATION_TESTS],
        ]
        command = (
            "import os,shutil,sys,cepio,pytest;"
            "assert '/site-packages/cepio/' in cepio.__file__,cepio.__file__;"
            "print('Installed CEPIO:',cepio.__file__);"
            "shutil.copytree('/work','/tmp/source');os.chdir('/tmp/source');"
            f"sys.exit(pytest.main({pytest_args!r}))"
        )
        # Test tools are mounted externally; no development packages enter the scanned image.
        require(
            "installed-integration-tests",
            [
                "docker",
                "run",
                *restrictions,
                "--network",
                "none",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "-e",
                "HOME=/tmp",
                "-e",
                "PYTHONPATH=/test-tools",
                "--tmpfs",
                "/tmp:exec",
                "-v",
                f"{ROOT}:/work:ro",
                "-v",
                f"{Path(temp) / 'test-tools'}:/test-tools:ro",
                "-v",
                f"{evaluation.EVIDENCE}:/evidence",
                "--entrypoint",
                "python",
                "cepio:ci",
                "-c",
                command,
            ],
        )
    report["installed_tests"] = (
        ET.parse(evaluation.EVIDENCE / "installed-tests.xml").getroot().find("testsuite").attrib
    )
    report["hardening_and_test_suites_passed"] = True
    # Execute the actual candidate checker, including its archive-bound scan.
    require(
        "production-candidate-checker",
        [sys.executable, "scripts/check_candidate_image.py"],
        timeout=1500,
    )
    candidate = json.loads((ROOT / "evidence/candidate-image/manifest.json").read_text())
    shutil.copytree(ROOT / "evidence/candidate-image", evaluation.EVIDENCE / "candidate-checker")
    report["production_candidate_checker"] = candidate
    report["existing_production_gate_compatible"] = (
        candidate.get("targeted_remediation_passed") is True
        and candidate.get("image_vulnerability_policy_passed") is True
        and candidate.get("runtime_minimization", {}).get("os_inventory_unchanged") is True
    )
    assert report["existing_production_gate_compatible"]
    report["safe_to_switch_production_now"] = False
    assert report.get("vulnerability_gate_passed"), "Final runtime vulnerability gate failed"
    if variant == "integrations":
        report["cepio_fabric_configuration_compatible"] = report["runtime_integrations"]["sql"][
            "cepio_connection_configuration"
        ]["accepted"]
        assert report["cepio_fabric_configuration_compatible"], (
            "CEPIO Fabric connection configuration rejected by installed driver"
        )
    report["isolated_checks_passed"] = True


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        report["error"] = str(error)
        report["isolated_checks_passed"] = False
    finally:
        report["limits"] = (
            "linux/amd64 isolated candidate. No live Fabric/SQL authentication or SELECT, Azure managed-identity token, private networking, deployment, provenance signing or model call. Loopback TDS checks prelogin and fail-closed connection handling, not a successful SQL session. Public Microsoft metadata GET uses no credentials. Production qualification remains false."
        )
        report["files_sha256"] = {
            p.relative_to(evaluation.EVIDENCE).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in evaluation.EVIDENCE.rglob("*")
            if p.is_file() and p != evaluation.EVIDENCE / "report.json"
        }
        (evaluation.EVIDENCE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: report.get(k)
                    for k in (
                        "variant",
                        "counts",
                        "source_tests",
                        "installed_tests",
                        "isolated_checks_passed",
                        "error",
                    )
                }
            )
        )
    sys.exit(0 if report.get("isolated_checks_passed") else 1)
