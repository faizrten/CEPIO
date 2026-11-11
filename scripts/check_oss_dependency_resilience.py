#!/usr/bin/env python3
"""Fail-closed direct-dependency admission and deterministic OSS inventory.

This is not a transitive SBOM, security scanner, or upstream-health monitor.
Those remain responsibilities of existing CEPIO release/security workflows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

REGISTER = Path("docs/governance/oss-dependency-register.json")
SOURCES = (
    "pyproject.toml:project.dependencies",
    "pyproject.toml:project.optional-dependencies.dev",
    "pyproject.toml:project.optional-dependencies.fabric-sql",
    "pyproject.toml:project.optional-dependencies.mcp",
    "pyproject.toml:project.optional-dependencies.otel",
    "requirements-quality.txt",
    "deploy/nvidia/requirements-cu12.txt",
    "deploy/nvidia/requirements-cu13.txt",
)
PACKAGE_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?=\[|\s|[!<=>~;@]|$)")
CANON_RE = re.compile(r"[-_.]+")
CAPABILITY_STATUSES = {"candidate", "evaluation", "existing_optional", "approved", "retired"}
REQUIRED_APPROVAL = (
    "owner",
    "upstream",
    "license",
    "pinned_revision",
    "adapter_path",
    "fallback",
    "security_review",
    "qualification_evidence",
    "exit_plan",
)
REQUIRED_NEW_PACKAGE = (
    "pinned_version",
    "owner",
    "license",
    "security_review",
    "qualification_evidence",
    "fallback",
    "exit_plan",
)


def canonical(name: str) -> str:
    return CANON_RE.sub("-", name).lower()


def requirement_package(requirement: str) -> str:
    match = PACKAGE_RE.match(requirement.strip())
    if not match:
        raise ValueError(f"Unsupported dependency declaration: {requirement!r}")
    return canonical(match.group(1))


def read_sources(root: Path) -> dict[str, list[dict[str, str]]]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    extras = project.get("optional-dependencies", {})
    expected_extras = {
        source.rsplit(".", 1)[1]
        for source in SOURCES
        if source.startswith("pyproject.toml:project.optional-dependencies.")
    }
    if set(extras) != expected_extras:
        difference = sorted(set(extras) ^ expected_extras)
        raise ValueError(f"Untracked optional-dependency groups: {difference}")
    output: dict[str, list[dict[str, str]]] = {}
    for source in SOURCES:
        if source.startswith("pyproject.toml:"):
            field = source.split(":", 1)[1]
            if field == "project.dependencies":
                entries = project.get("dependencies", [])
            else:
                extra = field.removeprefix("project.optional-dependencies.")
                entries = project.get("optional-dependencies", {}).get(extra, [])
        else:
            entries = []
            for line in (root / source).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("--extra-index-url "):
                    continue
                if line.startswith("-"):
                    raise ValueError(f"Unexpected pip option in {source}: {line}")
                entries.append(line)
        seen: set[str] = set()
        result = []
        for raw in entries:
            name = requirement_package(raw)
            if name in seen:
                raise ValueError(f"Duplicate dependency {name} in {source}")
            seen.add(name)
            result.append({"name": name, "requirement": raw})
        output[source] = sorted(result, key=lambda item: item["name"])
    return output


def nonempty(obj: dict, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if not isinstance(obj.get(key), str) or not obj[key].strip()]


def check(root: Path) -> tuple[dict, list[str]]:
    register = json.loads((root / REGISTER).read_text(encoding="utf-8"))
    if register.get("schema_version") != 1:
        raise ValueError("OSS register schema_version must be 1")
    sources = read_sources(root)
    baseline = register.get("baseline_direct_packages")
    if not isinstance(baseline, dict) or set(baseline) != set(SOURCES):
        raise ValueError("OSS register baseline sources must exactly match tracked source set")
    errors: list[str] = []
    approvals: dict[tuple[str, str], dict] = {}
    for record in register.get("new_package_admissions", []):
        if not isinstance(record, dict):
            errors.append("Package admission record must be an object")
            continue
        key = (record.get("source"), record.get("name"))
        if key in approvals:
            errors.append(f"Duplicate package admission {key}")
        approvals[key] = record
        if key[0] not in SOURCES or not isinstance(key[1], str) or canonical(key[1]) != key[1]:
            errors.append(f"Invalid package admission key {key}")
        if record.get("status") != "approved":
            errors.append(f"Package admission {key} is not approved")
        missing = nonempty(record, REQUIRED_NEW_PACKAGE)
        if missing:
            errors.append(f"Package admission {key} missing {', '.join(missing)}")
    entries = []
    newly_admitted = set()
    for source in SOURCES:
        declared_baseline = baseline[source]
        if (
            not isinstance(declared_baseline, list)
            or declared_baseline != sorted(set(declared_baseline))
            or any(
                not isinstance(name, str) or canonical(name) != name
                for name in declared_baseline
            )
        ):
            raise ValueError(f"Invalid/unsorted baseline list for {source}")
        for item in sources[source]:
            name, raw = item["name"], item["requirement"]
            if name in declared_baseline:
                classification = "existing_baseline_not_requalified"
            else:
                key = (source, name)
                admission = approvals.get(key)
                if admission is None:
                    errors.append(f"UNREGISTERED new direct package {name!r} in {source}")
                    classification = "unregistered"
                elif not re.search(
                    rf"(?<![!<>=~])==(?!=)\s*"
                    rf"{re.escape(admission.get('pinned_version', ''))}(?:\s|;|$)",
                    raw,
                ):
                    errors.append(f"New package {name} must declare an exact == pinned_version")
                    classification = "invalid_pin"
                else:
                    classification = "qualified_new_dependency"
                    newly_admitted.add(key)
            entries.append(
                {"source": source, "name": name, "requirement": raw, "classification": classification}
            )
    for key in approvals:
        if key not in newly_admitted:
            errors.append(f"Unused or invalid new package admission {key}")
    capabilities = register.get("strategic_capabilities", [])
    if not isinstance(capabilities, list):
        raise ValueError("strategic_capabilities must be a list")
    ids: set[str] = set()
    for cap in capabilities:
        if not isinstance(cap, dict):
            errors.append("Capability must be a JSON object")
            continue
        identifier = cap.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", identifier):
            errors.append(f"Invalid capability ID: {identifier!r}")
            continue
        if identifier in ids:
            errors.append(f"Duplicate capability ID: {identifier}")
        ids.add(identifier)
        status = cap.get("status")
        if status not in CAPABILITY_STATUSES:
            errors.append(f"{identifier}: invalid status {status!r}")
        upstream = cap.get("upstream", "")
        if not isinstance(upstream, str) or not upstream.startswith("https://"):
            errors.append(f"{identifier}: upstream must be an HTTPS URL")
        adapter = cap.get("adapter_path")
        if status in {"evaluation", "existing_optional", "approved"} and (
            not isinstance(adapter, str) or not (root / adapter).is_file()
        ):
            errors.append(f"{identifier}: integration path does not exist: {adapter!r}")
        if status == "approved":
            missing = nonempty(cap, REQUIRED_APPROVAL)
            if missing:
                errors.append(f"{identifier}: approved capability missing {', '.join(missing)}")
    output = {
        "schema_version": 1,
        "scope": "declared direct Python packages plus registered strategic OSS capabilities",
        "limitations": [
            "Not a transitive dependency graph or SBOM; existing CI/release security scanning "
            "remains authoritative.",
            "Repository source imports, runtime-downloaded assets and upstream maintenance "
            "are not auto-discovered.",
            "Existing baseline packages and optional integrations are not retroactively qualified.",
        ],
        "packages": sorted(entries, key=lambda x: (x["source"], x["name"])),
        "strategic_capabilities": sorted(capabilities, key=lambda x: x["id"]),
    }
    return output, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inventory-out", type=Path)
    args = parser.parse_args()
    try:
        inventory, errors = check(args.repo_root.resolve())
        if args.inventory_out:
            args.inventory_out.parent.mkdir(parents=True, exist_ok=True)
            args.inventory_out.write_text(
                json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        if errors:
            for error in errors:
                print("OSS dependency gate: " + error, file=sys.stderr)
            return 1
        print(f"OSS dependency gate PASS: {len(inventory['packages'])} direct declarations; "
              f"{len(inventory['strategic_capabilities'])} strategic capability entries")
        return 0
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"OSS dependency gate ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
