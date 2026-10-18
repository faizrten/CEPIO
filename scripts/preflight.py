"""Local CEPIO preflight with fast iteration and full qualification modes."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "evidence" / "local-preflight.json"


@dataclass
class StepResult:
    name: str
    command: str
    duration_seconds: float
    returncode: int


def git_changed_files(base: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Cannot resolve preflight base {base!r}. Fetch it or pass --base explicitly.\n"
            f"{completed.stderr.strip()}"
        )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def add_test(selected: dict[str, set[str]], path: str, reason: str) -> None:
    if (ROOT / path).exists():
        selected.setdefault(path, set()).add(reason)


def select_fast_tests(changed: list[str]) -> dict[str, list[str]]:
    selected: dict[str, set[str]] = {}
    add_test(selected, "tests/test_architecture_invariants.py", "always-on architecture guardrail")
    add_test(selected, "tests/test_quality_governance.py", "always-on quality-governance guardrail")

    for path in changed:
        if path.startswith("tests/") and path.endswith(".py"):
            add_test(selected, path, f"test file changed: {path}")
            continue

        if path.startswith("src/cepio/") and path.endswith(".py"):
            stem = Path(path).stem
            add_test(selected, f"tests/test_{stem}.py", f"production module changed: {path}")

        if path.startswith("profiles/"):
            add_test(selected, "tests/test_profiles.py", f"profile changed: {path}")
        if (
            path.startswith("ontologies/")
            or path.startswith("shapes/")
            or path == "ontology-modules.yaml"
        ):
            add_test(
                selected,
                "tests/test_ontology_contract_integration.py",
                f"ontology surface changed: {path}",
            )
            add_test(selected, "tests/test_domain_modules.py", f"ontology surface changed: {path}")
        if path.startswith("openapi/"):
            add_test(selected, "tests/test_api_v1_contract.py", f"OpenAPI contract changed: {path}")
        if path.startswith("generalization/"):
            for candidate in sorted((ROOT / "tests").glob("test_*generalization*.py")):
                rel = candidate.relative_to(ROOT).as_posix()
                add_test(selected, rel, f"generalization fixture changed: {path}")
        if "drilling" in path:
            for candidate in sorted((ROOT / "tests").glob("test_drilling_*.py")):
                rel = candidate.relative_to(ROOT).as_posix()
                add_test(selected, rel, f"drilling surface changed: {path}")
        if "refinery" in path:
            for candidate in sorted((ROOT / "tests").glob("test_refinery_*.py")):
                rel = candidate.relative_to(ROOT).as_posix()
                add_test(selected, rel, f"refinery surface changed: {path}")

    return {path: sorted(reasons) for path, reasons in sorted(selected.items())}


def run_step(name: str, argv: list[str], results: list[StepResult], env: dict[str, str]) -> bool:
    command = shlex.join(argv)
    print(f"\n==> {name}\n$ {command}", flush=True)
    started = perf_counter()
    completed = subprocess.run(argv, cwd=ROOT, env=env, check=False)
    duration = perf_counter() - started
    results.append(
        StepResult(
            name=name,
            command=command,
            duration_seconds=round(duration, 3),
            returncode=completed.returncode,
        )
    )
    print(f"<== {name}: {'PASS' if completed.returncode == 0 else 'FAIL'} ({duration:.2f}s)")
    return completed.returncode == 0


def core_contract_steps(python: str) -> list[tuple[str, list[str]]]:
    return [
        ("security scan", [python, "scripts/check_security.py"]),
        ("API contract", [python, "scripts/check_api_contract.py"]),
        ("client contract", [python, "scripts/check_client_contract.py"]),
        ("ontology compatibility", [python, "scripts/check_ontology_compat.py"]),
    ]


def full_domain_steps(python: str) -> list[tuple[str, list[str]]]:
    return [
        (
            "query load baseline",
            [python, "scripts/query_load_baseline.py", "--objects", "5000", "--max-ms", "5000"],
        ),
        ("deployment profiles", [python, "scripts/validate_deployment_profiles.py"]),
        (
            "drilling generalization v0.1",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--json-out",
                "generalization-report.json",
            ],
        ),
        (
            "drilling persona v0.2",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--competency",
                "generalization/competency/drilling-contractor-persona-expansion-v0.2.yaml",
                "--personas",
                "generalization/personas/drilling-contractor-v0.2.yaml",
                "--gaps",
                "generalization/gaps/drilling-contractor-persona-v0.2.yaml",
                "--json-out",
                "generalization-persona-v0.2-report.json",
            ],
        ),
        (
            "drilling capability v0.3",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--competency",
                "generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml",
                "--personas",
                "generalization/personas/drilling-contractor-v0.2.yaml",
                "--skip-gap-triage",
                "--fail-on-critical-gap",
                "--json-out",
                "generalization-persona-v0.3-report.json",
            ],
        ),
        (
            "drilling operational assurance v0.4",
            [
                python,
                "scripts/run_operational_assurance.py",
                "--fail-on-gap",
                "--json-out",
                "operational-assurance-v0.4-report.json",
            ],
        ),
        (
            "drilling runtime coverage v0.5",
            [
                python,
                "scripts/run_runtime_coverage.py",
                "--fail-on-gap",
                "--json-out",
                "runtime-coverage-v0.5-report.json",
            ],
        ),
        (
            "drilling domain runtime v0.4.1",
            [
                python,
                "scripts/run_runtime_coverage.py",
                "--suite",
                "generalization/runtime/drilling-contractor-domain-qualification-runtime-v0.4.1.yaml",
                "--fail-on-gap",
                "--json-out",
                "drilling-domain-runtime-qualification-v0.4.1-report.json",
            ],
        ),
        (
            "drilling cross-customer v0.5",
            [
                python,
                "scripts/run_cross_customer_qualification.py",
                "--fail-on-gap",
                "--json-out",
                "drilling-cross-customer-qualification-v0.5-report.json",
            ],
        ),
        (
            "refinery baseline v0.1",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--archetype",
                "generalization/archetypes/refinery-process-manufacturing-v0.1.yaml",
                "--competency",
                "generalization/competency/refinery-process-manufacturing-v0.1.yaml",
                "--personas",
                "generalization/personas/refinery-process-manufacturing-v0.1.yaml",
                "--standards",
                "generalization/standards/refinery-process-references.yaml",
                "--skip-gap-triage",
                "--json-out",
                "refinery-generalization-v0.1-report.json",
            ],
        ),
        (
            "build refinery normalized benchmark",
            [
                python,
                "scripts/build_refinery_normalized_benchmark.py",
                "--source",
                "generalization/competency/refinery-process-manufacturing-v0.1.yaml",
                "--out",
                "/tmp/refinery-process-manufacturing-v0.1.2.yaml",
            ],
        ),
        (
            "refinery normalized v0.1.2",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--archetype",
                "generalization/archetypes/refinery-process-manufacturing-v0.1.yaml",
                "--competency",
                "/tmp/refinery-process-manufacturing-v0.1.2.yaml",
                "--personas",
                "generalization/personas/refinery-process-manufacturing-v0.1.yaml",
                "--standards",
                "generalization/standards/refinery-process-references.yaml",
                "--skip-gap-triage",
                "--json-out",
                "refinery-generalization-v0.1.2-report.json",
            ],
        ),
        (
            "refinery persona challenge v0.2",
            [
                python,
                "scripts/run_generalization_harness.py",
                "--archetype",
                "generalization/archetypes/refinery-process-manufacturing-v0.1.yaml",
                "--competency",
                "generalization/competency/refinery-process-manufacturing-persona-expansion-v0.2.yaml",
                "--personas",
                "generalization/personas/refinery-process-manufacturing-v0.2.yaml",
                "--standards",
                "generalization/standards/refinery-process-references-v0.2.yaml",
                "--skip-gap-triage",
                "--json-out",
                "refinery-generalization-v0.2-report.json",
            ],
        ),
    ]


def write_report(
    path: Path,
    mode: str,
    base: str,
    changed: list[str],
    selected: dict[str, list[str]],
    results: list[StepResult],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": mode,
        "base": base,
        "changed_files": changed,
        "selected_tests": selected,
        "steps": [asdict(result) for result in results],
        "passed": bool(results) and all(result.returncode == 0 for result in results),
        "total_duration_seconds": round(sum(result.duration_seconds for result in results), 3),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nPreflight evidence: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast", "full"), required=True)
    parser.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    changed = git_changed_files(args.base)
    selected = select_fast_tests(changed)
    python = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    results: list[StepResult] = []

    steps: list[tuple[str, list[str]]] = [
        ("quality ratchet", [python, "scripts/check_quality.py", "--base", args.base]),
        *core_contract_steps(python),
    ]

    if args.mode == "fast":
        tests = list(selected)
        print("Fast preflight selected tests:")
        for test, reasons in selected.items():
            print(f"- {test}: {'; '.join(reasons)}")
        steps.append(("targeted tests", [python, "-m", "pytest", "-q", *tests]))
    else:
        steps.append(("full pytest", [python, "-m", "pytest", "-q"]))
        steps.extend(full_domain_steps(python))
        steps.extend(
            [
                ("deterministic validation", ["make", "validate"]),
                ("reference demo", [python, "examples/demo.py"]),
                ("build wheel", [python, "-m", "build", "--wheel"]),
                ("installed wheel smoke", [python, "scripts/smoke_wheel.py"]),
            ]
        )

    passed = True
    for name, argv in steps:
        if not run_step(name, argv, results, env):
            passed = False
            break

    write_report(args.report, args.mode, args.base, changed, selected, results)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
