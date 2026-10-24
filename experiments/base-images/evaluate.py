"""CI-only candidate experiment: no registry push, cloud identity, deploy or inference."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_deployed_image import SCANNER, os_triage, scanner_command  # noqa: E402
from check_candidate_image import archive_identity  # noqa: E402

NAME = sys.argv[1]
CONFIG = json.loads((ROOT / "experiments/base-images/candidates.json").read_text())[NAME]
EVIDENCE = ROOT / "evidence/base-images" / NAME
EVIDENCE.mkdir(parents=True, exist_ok=True)
DOCKERFILE = "experiments/base-images/Dockerfile." + NAME
REPORT = {"candidate": NAME, "base": CONFIG, "production_qualified": False,
          "steps": {}, "scanner": SCANNER, "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()}


def run(label, args, timeout=900):
    start = time.monotonic()
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=timeout, check=False)
        code, output = result.returncode, result.stdout
    except subprocess.TimeoutExpired as error:
        code, output = 124, str(error)
    (EVIDENCE / (label + ".log")).write_text(output, encoding="utf-8")
    REPORT["steps"][label] = {"exit_code": code, "seconds": round(time.monotonic() - start, 2)}
    print(f"{NAME} {label}: exit={code}", flush=True)
    return code, output


def request(path, payload=None, roles=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if roles:
        headers.update({"X-CEPIO-Dev-Actor": "base-image-evaluation", "X-CEPIO-Dev-Roles": roles})
    req = urllib.request.Request("http://127.0.0.1:18000" + path,
        data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def hosted_smoke():
    code, output = run("host-start", ["docker", "run", "-d", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "-p", "127.0.0.1:18000:8000",
        "-e", "CEPIO_ENVIRONMENT=test", "-e", "CEPIO_DB_URL=memory://",
        "-e", "CEPIO_AUTH_MODE=dev", "cepio:ci"])
    if code:
        return
    cid = output.strip()
    result = {"passed": False}
    try:
        for _ in range(30):
            try:
                status, body = request("/api/v1/health")
                if status == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            raise ValueError("HEALTH_NOT_READY")
        result["health"] = status
        status, _ = request("/mcp", {})
        result["anonymous_mcp"] = status
        assert status == 403
        status, body = request("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "base-eval", "version": "1"}}}, "ai_agent_recommender")
        assert status == 200 and json.loads(body)["result"]["protocolVersion"]
        result["authenticated_mcp_initialize"] = status
        status, body = request("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, "ai_agent_recommender")
        assert status == 200 and isinstance(json.loads(body)["result"]["tools"], list)
        result["authenticated_mcp_tools_list"] = status
        result["tool_names"] = sorted(x["name"] for x in json.loads(body)["result"]["tools"])
        result["passed"] = True
    except Exception as error:
        result["error"] = str(error)
    finally:
        run("host-logs", ["docker", "logs", cid])
        run("host-stop", ["docker", "rm", "-f", cid])
    REPORT["hosted_smoke"] = result


def scan_runtime():
    with tempfile.TemporaryDirectory(prefix="cepio-base-eval-") as temp:
        base = Path(temp)
        config, cache, archive = base / "docker", base / "cache", base / "image.tar"
        config.mkdir()
        cache.mkdir()
        code, raw = run("image-identity", ["docker", "image", "inspect", "cepio:ci"])
        assert code == 0
        identity = json.loads(raw)[0]
        REPORT["image_id"] = identity["Id"]
        assert run("image-export", ["docker", "save", "-o", str(archive), "cepio:ci"])[0] == 0
        REPORT["archive_config_digest"] = archive_identity(archive, identity["RootFS"]["Layers"])
        with archive.open("rb") as stream:
            REPORT["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        scan = scanner_command(EVIDENCE, config, cache)
        scan[scan.index("image") - 1:scan.index("image") - 1] = ["-v", f"{archive.resolve()}:/candidate.tar:ro"]
        index = scan.index("--image-src")
        del scan[index:index + 2]
        for format_name, filename in [("json", "vulnerabilities.json"), ("cyclonedx", "sbom.json")]:
            assert run("scan-" + format_name, scan + ["--input", "/candidate.tar", "--format", format_name,
                "--exit-code", "0", "--output", "/evidence/" + filename], timeout=800)[0] == 0
    data = json.loads((EVIDENCE / "vulnerabilities.json").read_text())
    assert data["SchemaVersion"] == 2 and data["Metadata"]["ImageID"] == REPORT["archive_config_digest"]
    assert data.get("Results") and any(r.get("Class") == "os-pkgs" for r in data["Results"])
    assert data["Metadata"]["OS"]["Family"] == CONFIG["os_family"]
    counts = dict.fromkeys(["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"], 0)
    by_class = {}
    blockers = []
    for result in data["Results"]:
        for finding in result.get("Vulnerabilities") or []:
            severity = finding["Severity"]
            counts[severity] += 1
            key = result["Class"] + "/" + severity
            by_class[key] = by_class.get(key, 0) + 1
            if severity in {"CRITICAL", "HIGH", "UNKNOWN"}:
                blockers.append({"class": result["Class"], "package": finding["PkgName"],
                    "id": finding["VulnerabilityID"], "severity": severity,
                    "installed": finding["InstalledVersion"], "fixed": finding.get("FixedVersion", "")})
    REPORT.update(counts=counts, counts_by_class=by_class, blockers=blockers,
        os=data["Metadata"]["OS"], vulnerability_gate_passed=not blockers)
    (EVIDENCE / "os-triage.json").write_text(json.dumps(os_triage(data), indent=2) + "\n")


NATIVE = r'''
import hashlib, importlib.metadata, importlib.resources, importlib.util, json, os, pathlib, socket, sqlite3, ssl, sys, uuid
import numpy, scipy.linalg, yaml, jwt, rdflib, mcp
from zoneinfo import ZoneInfo
assert os.getuid() != 0
assert importlib.util.find_spec("pip") is None and importlib.util.find_spec("ensurepip") is None
assert ssl.create_default_context().get_ca_certs()
assert socket.getaddrinfo("localhost", 8000)
assert sqlite3.connect(":memory:").execute("select 1").fetchone() == (1,)
assert uuid.uuid4() and ZoneInfo("Asia/Riyadh") and ZoneInfo("UTC")
assert scipy.linalg.det(numpy.eye(3)) == 1
token = jwt.encode({"test": "base-image"}, "evaluation-only-key-with-sufficient-length", algorithm="HS256")
assert jwt.decode(token, "evaluation-only-key-with-sufficient-length", algorithms=["HS256"])["test"] == "base-image"
inventory=json.loads(pathlib.Path("/usr/local/share/cepio/base-evaluation-minimization.json").read_text())
assert hashlib.sha256(pathlib.Path(inventory["inventory"]).read_bytes()).hexdigest() == inventory["inventory_sha256"]
assert all(not pathlib.Path(p).exists() and not pathlib.Path(p).is_symlink() for p in inventory["removed_paths"])
assert pathlib.Path("/bin/sh").exists()
print(json.dumps({"python": sys.version, "uid": os.getuid(), "inventory": inventory,
    "distributions": sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()), "passed": True}))
'''


def main():
    try:
        if run("runtime-build", ["docker", "build", "--pull", "--target", "runtime", "-f", DOCKERFILE, "-t", "cepio:ci", "."])[0] != 0:
            return
        code, output = run("native-smoke", ["docker", "run", "--rm", "--read-only", "--network", "none",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--entrypoint", "python", "cepio:ci", "-c", NATIVE])
        if code == 0:
            REPORT["native_smoke"] = json.loads(output)
        code, output = run("privilege-bits", ["docker", "run", "--rm", "--read-only", "--network", "none",
            "--user", "0", "--entrypoint", "find", "cepio:ci", "/", "-xdev", "-type", "f", "(", "-perm", "-4000", "-o", "-perm", "-2000", ")", "-print"])
        REPORT["privilege_bits_absent"] = code == 0 and not output.strip()
        hosted_smoke()
        scan_runtime()
        code, _ = run("tests-build", ["docker", "build", "--target", "test-runner", "-f", DOCKERFILE, "-t", "cepio:test", "."])
        if code == 0:
            run("source-suite", ["docker", "run", "--rm", "--network", "none", "--cap-drop=ALL",
                "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
                "--security-opt=no-new-privileges", "--tmpfs", "/tmp:exec",
                "-v", f"{ROOT}:/work:ro", "-v", f"{EVIDENCE}:/evidence", "cepio:test",
                "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp=/tmp/pytest",
                "--junitxml=/evidence/tests.xml"], timeout=900)
            xml = EVIDENCE / "tests.xml"
            if xml.exists():
                REPORT["tests"] = ET.parse(xml).getroot().find("testsuite").attrib
        optional, _ = run("optional-fabric-sql-build", ["docker", "build", "--target", "optional-probe",
            "-f", DOCKERFILE, "-t", "cepio:optional", "."])
        REPORT["optional_extras_install_and_import"] = optional == 0
    except Exception as error:
        REPORT["evaluation_error"] = str(error)
    finally:
        REPORT["default_runtime_compatible"] = bool(REPORT.get("native_smoke", {}).get("passed")
            and REPORT.get("hosted_smoke", {}).get("passed") and REPORT.get("privilege_bits_absent")
            and REPORT["steps"].get("source-suite", {}).get("exit_code") == 0)
        REPORT["eligible_for_proposal"] = bool(REPORT["default_runtime_compatible"]
            and REPORT.get("vulnerability_gate_passed") and REPORT.get("optional_extras_install_and_import"))
        REPORT["limits"] = "linux/amd64 CI experiment only. Source suite uses candidate OS/Python plus test dependencies; native/host checks use the final installed wheel. Optional extras are install/import probes, not live Fabric/SQL connectivity. No deployment, signing, cloud access, model calls, or production qualification. Different vendor severity databases are not reachability proof. BusyBox applets may remain reachable via busybox even when standalone links are removed."
        REPORT["files_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in EVIDENCE.iterdir() if p.is_file() and p.name != "report.json"}
        (EVIDENCE / "report.json").write_text(json.dumps(REPORT, indent=2) + "\n")
        print(json.dumps({k: REPORT.get(k) for k in ("candidate", "counts", "tests", "default_runtime_compatible", "optional_extras_install_and_import", "eligible_for_proposal", "evaluation_error")}), flush=True)


if __name__ == "__main__":
    main()
