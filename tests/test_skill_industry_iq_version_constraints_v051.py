from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq import install_industry_iq_packs
from cepio.skill_preflight import SkillPreflightSpec, evaluate_skill_preflight


PACK_ID = "cepio.iq.drilling.npt"


def _preflight(runtime, constraint: str):
    return evaluate_skill_preflight(
        runtime,
        SkillPreflightSpec(
            skill_id="cepio.skill.drilling.version-gated",
            industry_iq_pack_constraints={PACK_ID: constraint},
        ),
        actor_id="skill-agent-1",
        actor_roles={"drilling_npt_recommender"},
    )


def test_version_constrained_pack_passes_when_installed_version_is_compatible():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])

    result = _preflight(runtime, ">=0.1.0,<0.2.0")

    assert result.status == "READY"
    assert any(check.code == "INDUSTRY_IQ_PACK_COMPATIBLE" for check in result.checks)


def test_version_constrained_pack_fails_closed_when_installed_version_is_incompatible():
    runtime = build_runtime()
    runtime.industry_iq_packs[PACK_ID] = "0.2.0"

    result = _preflight(runtime, ">=0.1.0,<0.2.0")

    assert result.status == "BLOCKED"
    assert [check.code for check in result.blockers] == [
        "INDUSTRY_IQ_PACK_VERSION_INCOMPATIBLE"
    ]


def test_invalid_skill_pack_constraint_fails_closed_instead_of_raising():
    runtime = build_runtime()
    runtime.industry_iq_packs[PACK_ID] = "0.1.0"

    result = _preflight(runtime, ">=bad")

    assert result.status == "BLOCKED"
    assert [check.code for check in result.blockers] == [
        "INDUSTRY_IQ_PACK_CONSTRAINT_INVALID"
    ]


def test_constraint_only_declaration_still_requires_pack_presence():
    runtime = build_runtime()

    result = _preflight(runtime, "^0.1.0")

    assert result.status == "BLOCKED"
    assert [check.code for check in result.blockers] == ["INDUSTRY_IQ_PACK_UNAVAILABLE"]
