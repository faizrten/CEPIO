from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
UPSTREAM_FILTER = (
    r"ignore:^Dataset\.default_context is deprecated, use Dataset\.default_graph instead\.$:"
    r"DeprecationWarning:rdflib\.graph$"
)


def test_warning_policy_is_fail_closed_and_quarantine_is_exact():
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    filters = config["tool"]["pytest"]["ini_options"]["filterwarnings"]
    assert filters[0] == "error"
    assert filters[1:] == [UPSTREAM_FILTER]


def test_unexpected_runtime_warning_fails_pytest(tmp_path):
    probe = tmp_path / "test_warning_probe.py"
    probe.write_text(
        textwrap.dedent(
            """
            import warnings

            def test_probe():
                warnings.warn("unexpected CEPIO warning budget probe", RuntimeWarning)
            """
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-c", str(PYPROJECT), str(probe)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "RuntimeWarning: unexpected CEPIO warning budget probe" in output
