"""Inspect the existing CI candidate; validate targeted fixes, never production readiness."""

import hashlib
import json
from pathlib import Path
import tempfile

from check_deployed_image import command, scanner_command, sbom_summary, SEVERITIES


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
        with tempfile.TemporaryDirectory(prefix="cepio-candidate-") as temporary:
            base = Path(temporary)
            config, cache, archive = base / "docker", base / "cache", base / "image.tar"
            config.mkdir()
            cache.mkdir()
            command(["docker", "save", "--output", str(archive), "cepio:ci"], timeout=180)
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
        report.update(
            summarize(
                json.loads((evidence / "container-vulnerabilities.json").read_text()),
                json.loads((evidence / "container-sbom.json").read_text()),
                image_id,
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
