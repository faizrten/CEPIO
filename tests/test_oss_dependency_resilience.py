"""Positive and adversarial qualification tests for new third-party direct dependencies."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_oss_dependency_resilience.py"
REGISTER = "docs/governance/oss-dependency-register.json"
TRACKED = [
    "pyproject.toml",
    "requirements-quality.txt",
    "deploy/nvidia/requirements-cu12.txt",
    "deploy/nvidia/requirements-cu13.txt",
    REGISTER,
]


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    for path in TRACKED:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
    register = json.loads((tmp_path / REGISTER).read_text(encoding="utf-8"))
    for capability in register["strategic_capabilities"]:
        adapter = capability.get("adapter_path")
        if adapter:
            path = tmp_path / adapter
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
    return tmp_path


def run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--inventory-out",
            str(repo / "inventory.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def add_requirement(repo: Path, requirement: str) -> None:
    path = repo / "pyproject.toml"
    old = path.read_text(encoding="utf-8")
    assert "dependencies = [" in old
    path.write_text(
        old.replace("dependencies = [", f'dependencies = [\n  "{requirement}",', 1),
        encoding="utf-8",
    )


def register_admission(repo: Path, version: str = "1.2.3") -> None:
    path = repo / REGISTER
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["new_package_admissions"].append(
        {
            "source": "pyproject.toml:project.dependencies",
            "name": "synthetic-demo-package",
            "status": "approved",
            "pinned_version": version,
            "owner": "Synthetic test owner",
            "license": "MIT - verified by synthetic test only",
            "security_review": "synthetic security review record",
            "qualification_evidence": "synthetic test record",
            "fallback": "No-op local implementation",
            "exit_plan": "Disable adapter",
        }
    )
    path.write_text(json.dumps(registry), encoding="utf-8")


def test_existing_baseline_generates_deterministic_inventory(repo: Path) -> None:
    result = run(repo)
    assert result.returncode == 0, result.stderr
    first = (repo / "inventory.json").read_bytes()
    assert run(repo).returncode == 0
    assert first == (repo / "inventory.json").read_bytes()
    inventory = json.loads(first)
    assert inventory["packages"]
    assert any(
        cap["id"] == "nvidia-physicsnemo" and cap["status"] == "candidate"
        for cap in inventory["strategic_capabilities"]
    )


def test_new_unregistered_direct_dependency_fails(repo: Path) -> None:
    add_requirement(repo, "synthetic-demo-package==1.2.3")
    result = run(repo)
    assert result.returncode != 0
    assert "UNREGISTERED new direct package" in result.stderr


def test_new_qualified_and_exactly_pinned_dependency_passes(repo: Path) -> None:
    add_requirement(repo, "synthetic-demo-package==1.2.3")
    register_admission(repo)
    result = run(repo)
    assert result.returncode == 0, result.stderr
    inventory = json.loads((repo / "inventory.json").read_text(encoding="utf-8"))
    assert any(
        p["name"] == "synthetic-demo-package" and p["classification"] == "qualified_new_dependency"
        for p in inventory["packages"]
    )


def test_unpinned_new_package_fails_even_with_approval_claim(repo: Path) -> None:
    add_requirement(repo, "synthetic-demo-package>=1.2.3")
    register_admission(repo)
    result = run(repo)
    assert result.returncode != 0
    assert "must declare an exact ==" in result.stderr


def test_missing_security_review_fails_even_with_approval_claim(repo: Path) -> None:
    add_requirement(repo, "synthetic-demo-package==1.2.3")
    register_admission(repo)
    path = repo / REGISTER
    registry = json.loads(path.read_text(encoding="utf-8"))
    del registry["new_package_admissions"][0]["security_review"]
    path.write_text(json.dumps(registry), encoding="utf-8")
    result = run(repo)
    assert result.returncode != 0
    assert "missing security_review" in result.stderr


def test_untracked_extra_group_fails(repo: Path) -> None:
    path = repo / "pyproject.toml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[project.optional-dependencies.new_extra]\nexample = ["bad"]\n',
        encoding="utf-8",
    )
    result = run(repo)
    assert result.returncode != 0
    assert "Untracked optional-dependency groups" in result.stderr


def test_approved_strategic_capability_requires_exit_plan(repo: Path) -> None:
    path = repo / REGISTER
    registry = json.loads(path.read_text(encoding="utf-8"))
    cap = next(c for c in registry["strategic_capabilities"] if c["id"] == "nvidia-nx-cugraph")
    cap["status"] = "approved"
    path.write_text(json.dumps(registry), encoding="utf-8")
    result = run(repo)
    assert result.returncode != 0
    assert "approved capability missing" in result.stderr


def test_historical_baseline_cannot_be_silently_reclassified(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
        capture_output=True,
    )
    base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    path = repo / REGISTER
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["baseline_direct_packages"]["pyproject.toml:project.dependencies"].append("zz-new")
    path.write_text(json.dumps(registry), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "--base-sha", base],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Historical direct-package baseline changed" in result.stderr
