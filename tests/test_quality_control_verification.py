"""Execute workflow gates and prove committed changes cannot disappear from checks."""

from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/quality.yml").read_text())


def load_quality():
    spec = importlib.util.spec_from_file_location(
        "check_quality", ROOT / "scripts/check_quality.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("job", ["static", "compatibility"])
def test_comparison_base_uses_immutable_event_history(job):
    steps = [step for step in WORKFLOW["jobs"][job]["steps"] if "BASE_REF" in step.get("env", {})]
    assert steps, "No base-sensitive check was examined"
    for step in steps:
        assert step["env"]["BASE_REF"] == (
            "${{ github.event.pull_request.base.sha || github.event.before || 'HEAD^' }}"
        )
        assert '"$BASE_REF"' in step["run"]


def test_committed_python_change_survives_main_advance(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Control Test")
    git("config", "user.email", "control@example.invalid")
    target = tmp_path / "example.py"
    target.write_text("value = 1\n")
    git("add", ".")
    git("commit", "-m", "base")
    before = git("rev-parse", "HEAD")
    target.write_text("value=2\n")
    git("commit", "-am", "unformatted committed change")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    checker = load_quality()
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker.changed_python("origin/main") == []  # Original push blind spot.
    assert checker.changed_python(before) == ["example.py"]
    (tmp_path / "new.py").write_text("value = 3\n")
    assert checker.changed_python(before) == ["example.py", "new.py"]
    with pytest.raises(RuntimeError):
        checker.changed_python("nonexistent-base")


def test_real_formatter_rejects_unformatted_file(tmp_path):
    pytest.importorskip("ruff", reason="Ruff is installed in the quality lanes")
    (tmp_path / "example.py").write_text("value=2\n")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "example.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "example.py" in result.stdout


def test_failed_untracked_query_is_not_an_empty_success(monkeypatch):
    checker = load_quality()

    def run(*args):
        if args[1] == "diff":
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 1, "", "enumeration failed")

    monkeypatch.setattr(checker, "run", run)
    with pytest.raises(RuntimeError, match="enumeration failed"):
        checker.changed_python("base")


@pytest.mark.parametrize("paths", [[], ["changed.py"]])
def test_format_check_reports_input_count(paths, tmp_path, monkeypatch, capsys):
    checker = load_quality()
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}")
    monkeypatch.setattr(checker, "BASELINE", baseline)
    monkeypatch.setattr(checker, "findings", Counter)
    monkeypatch.setattr(checker, "changed_python", lambda base: paths)
    monkeypatch.setattr(sys, "argv", ["check_quality.py", "--base", "base"])
    calls = []

    def run(*args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "Would reformat", "")

    monkeypatch.setattr(checker, "run", run)
    assert checker.main() == int(bool(paths))
    assert f"Formatting input files: {len(paths)}" in capsys.readouterr().out
    assert len(calls) == int(bool(paths))


REQUIRED = ["static", "architecture", "compatibility", "security", "coverage-head"]
PR_ONLY = ["coverage-base", "coverage-compare"]


def run_aggregate(event, results):
    gate = WORKFLOW["jobs"]["gate"]
    assert gate["if"] == "always()"
    assert set(gate["needs"]) == set(REQUIRED + PR_ONLY)
    assert len(gate["steps"]) == 1
    environment = dict(os.environ, RESULTS=json.dumps(results), EVENT_NAME=event)
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    environment.pop("PYTHONOPTIMIZE", None)
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", gate["steps"][0]["run"]],
        env=environment,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("event", ["pull_request", "push", "workflow_call"])
def test_aggregate_accepts_complete_success(event):
    results = {name: {"result": "success"} for name in REQUIRED + PR_ONLY}
    if event != "pull_request":
        for name in PR_ONLY:
            results[name]["result"] = "skipped"
    result = run_aggregate(event, results)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("lane", REQUIRED + PR_ONLY)
@pytest.mark.parametrize("state", ["failure", "cancelled", "skipped", "missing"])
def test_pr_aggregate_rejects_unsuccessful_or_missing_lane(lane, state):
    results = {name: {"result": "success"} for name in REQUIRED + PR_ONLY}
    if state == "missing":
        del results[lane]
    else:
        results[lane]["result"] = state
    result = run_aggregate("pull_request", results)
    assert result.returncode != 0, f"Gate accepted {lane}: {state}"
    assert lane in result.stderr


@pytest.mark.parametrize("event", ["push", "workflow_call"])
def test_non_pr_aggregate_rejects_skipped_head_coverage(event):
    results = {name: {"result": "success"} for name in REQUIRED + PR_ONLY}
    results["coverage-head"]["result"] = "skipped"
    assert run_aggregate(event, results).returncode != 0


@pytest.mark.parametrize(
    "state", ["success", "failure", "cancelled", "skipped", "missing", "empty"]
)
def test_ci_aggregate_requires_all_six_lanes(state):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    gate = workflow["jobs"]["test"]
    required = {"unit", "contracts", "drilling", "refinery", "package", "container"}
    assert set(gate["needs"]) == required
    assert gate["if"] == "always()"
    results = {name: {"result": "success"} for name in required}
    if state == "empty":
        results = {}
    elif state == "missing":
        del results["unit"]
    else:
        results["unit"]["result"] = state
    environment = dict(os.environ, RESULTS=json.dumps(results))
    environment.pop("PYTHONOPTIMIZE", None)
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", gate["steps"][0]["run"]],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (state == "success"), result.stdout + result.stderr
