from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from cepio.formation_evaluation import FormationEvaluationAssuranceRuntime
from cepio.petrophysics_v1 import PetrophysicsV1Runtime, run_petrophysics_v1

ROOT = Path(__file__).parents[1]
PET02_BENCHMARK = (
    ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
)
V1_BENCHMARK = ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-v1-portfolio.yaml"


def _pet02_payload() -> dict:
    return yaml.safe_load(PET02_BENCHMARK.read_text(encoding="utf-8"))


def _v1_payload() -> dict:
    return yaml.safe_load(V1_BENCHMARK.read_text(encoding="utf-8"))


def _authoritative_case(payload: dict) -> dict:
    return next(
        case
        for case in payload["formation_evaluation_cases"]
        if str(case.get("state", "")).endswith("#Authoritative")
    )


def test_pet02_from_yaml_rejects_non_mapping_payload(tmp_path: Path):
    bad = tmp_path / "bad-pet02.yaml"
    bad.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="PET-02 input must be a YAML mapping"):
        FormationEvaluationAssuranceRuntime.from_yaml(bad)


def test_pet02_fails_closed_when_no_case_is_authoritative():
    payload = _pet02_payload()
    mutated = deepcopy(payload)
    for case in mutated["formation_evaluation_cases"]:
        case["state"] = "https://cepio.org/ontology/subsurface#UnderReview"

    result = FormationEvaluationAssuranceRuntime(mutated).execute(well="A-17", interval="Zone-B")

    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None
    assert result.blockers[0].code == "AUTHORITATIVE_CASE_NOT_FOUND"
    assert result.trace[-1].status == "BLOCKED"


def test_pet02_fails_closed_when_authoritative_predecessor_is_missing():
    payload = _pet02_payload()
    mutated = deepcopy(payload)
    _authoritative_case(mutated)["supersedes"] = "FE-MISSING"

    result = FormationEvaluationAssuranceRuntime(mutated).execute(well="A-17", interval="Zone-B")

    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None
    assert result.blockers[0].code == "SUPERSEDED_CASE_NOT_FOUND"
    assert "lineage" in result.trace[-1].message.lower()


def test_pet02_rejects_external_evidence_without_stable_id():
    payload = _pet02_payload()
    mutated = deepcopy(payload)
    mutated["external_evidence"].append({"role": "supporting", "source_ref": {}})

    summaries, blockers = FormationEvaluationAssuranceRuntime(mutated)._validated_evidence()

    assert summaries
    assert any(blocker.code == "EVIDENCE_ID_MISSING" for blocker in blockers)


def test_pet02_state_name_handles_missing_state():
    assert FormationEvaluationAssuranceRuntime._state_name(None) == ""


def test_pet02_ignores_confidence_assessments_for_other_cases():
    payload = _pet02_payload()
    mutated = deepcopy(payload)
    mutated["confidence_assessments"].append(
        {
            "id": "CA-OTHER",
            "assesses": "FE-OTHER",
            "rating": "low",
            "rationale": "Unrelated case used to prove filtering.",
        }
    )

    result = FormationEvaluationAssuranceRuntime(mutated).execute(well="A-17", interval="Zone-B")

    assert result.status == "ANSWERED"
    assert result.answer is not None
    assert "CA-OTHER" not in {item.id for item in result.answer.confidence}


def test_petrophysics_v1_from_yaml_rejects_non_mapping_payload(tmp_path: Path):
    bad = tmp_path / "bad-v1.yaml"
    bad.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Petrophysics v1 benchmark must be a YAML mapping"):
        PetrophysicsV1Runtime.from_yaml(bad)


def test_petrophysics_v1_rejects_unknown_journey():
    runtime = PetrophysicsV1Runtime.from_yaml(V1_BENCHMARK)

    with pytest.raises(ValueError, match="Unknown Petrophysics journey"):
        runtime.execute("PET-99")


def test_petrophysics_v1_pet02_wrapper_preserves_fail_closed_result():
    runtime = PetrophysicsV1Runtime.from_yaml(V1_BENCHMARK)

    result = runtime.execute(
        "PET-02",
        actor_id="unauthorized-user",
        actor_roles={"shareholder_viewer"},
    )

    assert result.status == "BLOCKED"
    assert result.answer is None
    assert result.blockers
    assert all(blocker.code == "SKILL_PREFLIGHT_BLOCKED" for blocker in result.blockers)


def test_pet08_preserves_nonnumeric_prior_posterior_values():
    payload = _v1_payload()
    mutated = deepcopy(payload)
    mutated["PET-08"]["prior"]["interpretation_basis"] = "pre-drill"
    mutated["PET-08"]["posterior"]["interpretation_basis"] = "post-drill"
    runtime = PetrophysicsV1Runtime(mutated, resource_root=ROOT)

    result = runtime.execute("PET-08")

    assert result.status == "ANSWERED"
    assert result.answer is not None
    assert result.answer["belief_delta"]["interpretation_basis"] == {
        "prior": "pre-drill",
        "posterior": "post-drill",
    }


def test_run_petrophysics_v1_wrapper_executes_complete_coverage():
    result = run_petrophysics_v1(V1_BENCHMARK)

    assert result.complete is True
    assert result.passed == 8
    assert result.blocked == 0
