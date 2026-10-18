from pathlib import Path
from runpy import run_path


PREFLIGHT = run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "preflight.py"))
select_fast_tests = PREFLIGHT["select_fast_tests"]


def test_fast_preflight_selects_module_and_profile_regressions():
    selected = select_fast_tests(
        [
            "src/cepio/agent_retrieval.py",
            "profiles/satorp/profile.yaml",
        ]
    )
    assert "tests/test_architecture_invariants.py" in selected
    assert "tests/test_quality_governance.py" in selected
    assert "tests/test_agent_retrieval.py" in selected
    assert "tests/test_profiles.py" in selected
    assert any(
        "production module changed" in reason
        for reason in selected["tests/test_agent_retrieval.py"]
    )


def test_fast_preflight_selects_changed_test_directly():
    selected = select_fast_tests(["tests/test_api.py"])
    assert "tests/test_api.py" in selected
    assert selected["tests/test_api.py"] == ["test file changed: tests/test_api.py"]
