from copy import deepcopy
from pathlib import Path

from cepio.production_technology_v02 import ProductionTechnologistV02Runtime

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "generalization" / "benchmarks" / "production-technologist-p118-v0.2.yaml"


def _runtime() -> ProductionTechnologistV02Runtime:
    return ProductionTechnologistV02Runtime.from_yaml(BENCHMARK)


def test_v02_cumulative_coverage_answers_six_journeys():
    result = _runtime().execute_all()
    assert result.complete
    assert result.answered == 6
    assert result.blocked == 0
    assert set(result.results) == {"PROD-01", "PROD-02", "PROD-03", "PROD-04", "PROD-05", "PROD-06"}
    assert all(r.status == "ANSWERED" for r in result.results.values())
    assert all(all(p.status == "READY" for p in r.preflights) for r in result.results.values())


def test_prod03_is_constraint_aware_not_max_uplift_only():
    result = _runtime().execute("PROD-03")
    assert result.status == "ANSWERED"
    answer = result.answer
    assert answer is not None
    assert answer["recommended_option"] == "OPT-BP-14"
    assert answer["ranked_feasible_options"] == ["OPT-BP-14", "OPT-GL-18"]
    assert answer["conditional_review_options"] == ["OPT-COMB-18-14"]
    assert answer["rejected_options"] == ["OPT-PUSH-20-12"]
    assert "max_governed_drawdown" in answer["options"]["OPT-PUSH-20-12"]["constraint_violations"]
    assert "lift_gas_allocation_cap" in answer["options"]["OPT-PUSH-20-12"]["constraint_violations"]
    assert "surface_backpressure_operability_floor" in answer["options"]["OPT-PUSH-20-12"]["constraint_violations"]
    assert answer["live_control_permitted"] is False
    assert answer["cepio_solved_network_or_nodal_hydraulics"] is False


def test_prod04_uses_external_lift_sensitivity_and_respects_allocation_cap():
    result = _runtime().execute("PROD-04")
    assert result.status == "ANSWERED"
    answer = result.answer
    assert answer is not None
    assert answer["current_gas_lift_mmscfd"] == 1.4
    assert answer["field_allocation_cap_mmscfd"] == 1.85
    assert answer["constrained_candidate_mmscfd"] == 1.8
    assert answer["diminishing_returns_after_mmscfd"] == 1.8
    assert answer["cepio_calculated_lift_hydraulics"] is False
    assert answer["live_setpoint_change_permitted"] is False
    assert "authorized" in answer["recommended_next_step"].lower()
    assert answer["falsification_test"]


def test_prod05_classifies_envelope_margin_and_never_approves_exception():
    result = _runtime().execute("PROD-05")
    assert result.status == "ANSWERED"
    answer = result.answer
    assert answer is not None
    assert answer["safe_options"] == ["OPT-CURRENT", "OPT-GL-18", "OPT-BP-14"]
    assert answer["requires_integrity_or_operations_review"] == ["OPT-COMB-18-14"]
    assert answer["prohibited_under_current_envelope"] == ["OPT-PUSH-20-12"]
    assert answer["option_assessments"]["OPT-COMB-18-14"]["drawdown_margin_bar"] == 0.5
    assert answer["option_assessments"]["OPT-PUSH-20-12"]["drawdown_margin_bar"] == -2.0
    assert answer["autonomous_exception_approval"] is False
    assert answer["autonomous_operating_change"] is False


def test_v02_unauthorized_actor_fails_closed():
    result = _runtime().execute(
        "PROD-03",
        actor_id="autonomous_control_agent",
        actor_roles={"autonomous_control_agent"},
    )
    assert result.status == "BLOCKED"
    assert any(blocker.code == "SKILL_PREFLIGHT_BLOCKED" for blocker in result.blockers)


def test_v02_new_external_model_identity_is_required():
    runtime = _runtime()
    data = deepcopy(runtime.data)
    data["artificial_lift"]["source_ref"]["record_version"] = ""
    broken = ProductionTechnologistV02Runtime(data, resource_root=ROOT)
    result = broken.execute("PROD-04")
    assert result.status == "BLOCKED"
    assert any(blocker.code == "INCOMPLETE_EXTERNAL_IDENTITY" for blocker in result.blockers)


def test_v02_does_not_add_new_domain_classes_for_the_three_journeys():
    text = (ROOT / "ontologies" / "production.ttl").read_text(encoding="utf-8")
    for existing in (
        "prod:ProductionConstraintAssessment",
        "prod:ArtificialLiftPerformanceAssessment",
        "prod:WellIntegrityAssessment",
        "prod:WellOperatingEnvelope",
        "prod:WellOperatingLimit",
    ):
        assert existing in text
    for avoided in (
        "prod:ProductionOptimizationOption",
        "prod:GasLiftCurve",
        "prod:IntegrityExceptionApproval",
    ):
        assert avoided not in text
