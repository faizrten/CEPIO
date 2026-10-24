"""Inspect the existing CI candidate; validate targeted fixes, never production readiness."""

import hashlib
import json
from pathlib import Path
import tempfile
import tarfile

from check_deployed_image import command, scanner_command, sbom_summary, os_triage, SEVERITIES


def summarize(scan, sbom, image_id):
    if scan.get("SchemaVersion") != 2 or scan.get("Metadata", {}).get("ImageID") != image_id:
        raise ValueError("CANDIDATE_IMAGE_ID_MISMATCH")
    if not isinstance(scan.get("Results"), list) or not scan["Results"]:
        raise ValueError("CANDIDATE_SCAN_INCOMPLETE")
    counts = dict.fromkeys(sorted(SEVERITIES), 0)
    python_blockers = []
    for result in scan["Results"]:
        for finding in result.get("Vulnerabilities") or []:
            severity = finding["Severity"]
            if severity not in counts:
                raise ValueError("INVALID_SEVERITY")
            counts[severity] += 1
            if result.get("Class") == "lang-pkgs" and severity in {"HIGH", "CRITICAL", "UNKNOWN"}:
                python_blockers.append(
                    {
                        "package": finding["PkgName"],
                        "id": finding["VulnerabilityID"],
                        "severity": severity,
                    }
                )
    inventory = sbom_summary(sbom)
    pip_present = any(item.get("name", "").lower() == "pip" for item in sbom["components"])
    return {
        "counts": counts,
        "python_blockers": python_blockers,
        "sbom": inventory,
        "pip_present": pip_present,
        "targeted_remediation_passed": not python_blockers
        and inventory["qualified"]
        and not pip_present,
        "image_vulnerability_policy_passed": not any(
            counts[x] for x in ("HIGH", "CRITICAL", "UNKNOWN")
        ),
        "production_qualified": False,
    }


def archive_identity(path, expected_layers):
    # Read archive members only; never extract an image filesystem onto the runner.
    with tarfile.open(path, "r") as archive:

        def read_json(name):
            member = archive.getmember(name)
            if not member.isfile() or member.size > 2 * 1024 * 1024:
                raise ValueError("INVALID_IMAGE_ARCHIVE_MEMBER")
            raw = archive.extractfile(member).read()
            return raw, json.loads(raw)

        _, manifest = read_json("manifest.json")
        if (
            not isinstance(manifest, list)
            or len(manifest) != 1
            or "cepio:ci" not in manifest[0].get("RepoTags", [])
        ):
            raise ValueError("CANDIDATE_ARCHIVE_TAG_MISMATCH")
        raw, config = read_json(manifest[0]["Config"])
        if not expected_layers or config.get("rootfs", {}).get("diff_ids") != expected_layers:
            raise ValueError("CANDIDATE_ARCHIVE_LAYER_MISMATCH")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def runtime_hardening():
    # Inspect as root so unreadable paths cannot hide privileged regular files.
    # This transient CI inspection never grants the deployed service root.
    privileged = command(
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
            "find",
            "cepio:ci",
            "/",
            "-xdev",
            "-type",
            "f",
            "-perm",
            "/6000",
            "-print",
        ]
    ).strip()
    if privileged:
        raise ValueError("PRIVILEGED_RUNTIME_FILES_PRESENT")
    user = command(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--entrypoint",
            "id",
            "cepio:ci",
            "-u",
        ]
    ).strip()
    if not user.isdecimal() or int(user) == 0:
        raise ValueError("RUNTIME_USER_MUST_BE_NONROOT")
    return {"nonroot": True, "setuid_setgid_files": 0}


def main():
    evidence = Path("evidence/candidate-image")
    evidence.mkdir(parents=True, exist_ok=True)
    report = {"production_qualified": False, "targeted_remediation_passed": False}
    try:
        image_id = command(
            ["docker", "image", "inspect", "--format", "{{.Id}}", "cepio:ci"]
        ).strip()
        report["source_sha"] = command(["git", "rev-parse", "HEAD"]).strip()
        report["image_id"] = image_id
        expected_layers = json.loads(
            command(
                ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", "cepio:ci"]
            )
        )
        # Read-only filesystem checks; no imports of target applications or inference.
        command(
            [
                "docker",
                "run",
                "--rm",
                "--entrypoint",
                "python",
                "cepio:ci",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('pip') is None; "
                "assert importlib.util.find_spec('ensurepip') is None",
            ]
        )
        report["runtime_hardening"] = runtime_hardening()
        report["runtime_minimization"] = json.loads(
            command(
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
                    Path(__file__).with_name("minimize_runtime.py").read_text(),
                ]
            )
        )
        # Exercise retained native libraries, default trust store, name service
        # and timezone data without external requests, tools or model inference.
        command(
            [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "none",
                "--entrypoint",
                "python",
                "cepio:ci",
                "-c",
                "import ssl, socket, sqlite3, uuid, numpy, scipy.linalg; from zoneinfo import ZoneInfo; "
                "assert ssl.create_default_context().get_ca_certs(); "
                "assert socket.getaddrinfo('localhost', 8000); "
                "assert sqlite3.connect(':memory:').execute('select 1').fetchone() == (1,); "
                "assert uuid.uuid4(); assert ZoneInfo('UTC'); "
                "assert scipy.linalg.det(numpy.eye(2)) == 1",
            ]
        )
        with tempfile.TemporaryDirectory(prefix="cepio-candidate-") as temporary:
            base = Path(temporary)
            config, cache, archive = base / "docker", base / "cache", base / "image.tar"
            config.mkdir()
            cache.mkdir()
            command(["docker", "save", "--output", str(archive), "cepio:ci"], timeout=180)
            report["archive_config_digest"] = archive_identity(archive, expected_layers)
            if (
                command(["docker", "image", "inspect", "--format", "{{.Id}}", "cepio:ci"]).strip()
                != image_id
            ):
                raise ValueError("CANDIDATE_CHANGED_DURING_EXPORT")
            with archive.open("rb") as stream:
                report["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
            scan = scanner_command(evidence, config, cache)
            scanner_index = scan.index("image") - 1
            scan[scanner_index:scanner_index] = ["-v", f"{archive.resolve()}:/candidate.tar:ro"]
            remote = scan.index("--image-src")
            del scan[remote : remote + 2]
            for format_name, filename in [
                ("json", "container-vulnerabilities.json"),
                ("cyclonedx", "container-sbom.json"),
            ]:
                command(
                    scan
                    + [
                        "--input",
                        "/candidate.tar",
                        "--format",
                        format_name,
                        "--exit-code",
                        "0",
                        "--output",
                        "/evidence/" + filename,
                    ],
                    timeout=660,
                )
        (evidence / "os-triage.json").write_text(
            json.dumps(
                os_triage(json.loads((evidence / "container-vulnerabilities.json").read_text())),
                indent=2,
            )
            + "\n"
        )
        report.update(
            summarize(
                json.loads((evidence / "container-vulnerabilities.json").read_text()),
                json.loads((evidence / "container-sbom.json").read_text()),
                report["archive_config_digest"],
            )
        )
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        report["error"] = "CANDIDATE_INSPECTION_FAILED"
    report["files_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in evidence.glob("*.json")
        if p.name != "manifest.json"
    }
    report["limits"] = (
        "Local CI candidate only. Remaining OS findings still block image qualification; this targeted regression check is not a production promotion gate. No registry access, deployment, signing or inference."
    )
    (evidence / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("CANDIDATE_IMAGE_EVIDENCE " + json.dumps(report, sort_keys=True))
    return 0 if report["targeted_remediation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
