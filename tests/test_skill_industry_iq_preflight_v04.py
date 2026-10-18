from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq import install_industry_iq_packs
from cepio.skill_preflight import SkillPreflightSpec, evaluate_skill_preflight


PACK_ID = "cepio.iq.drilling.npt"


def test_required_industry_iq_pack_blocks_default_runtime():
    runtime = build_runtime()
    spec = SkillPreflightSpec(
        skill_id="cepio.skill.drilling.test-pack-gate",
        industry_iq_packs={PACK_ID},
    )

    result = evaluate_skill_preflight(
        runtime,
        spec,
        actor_id="skill-agent-1",
        actor_roles={"drilling_npt_recommender"},
    )

    assert result.status == "BLOCKED"
    assert [check.code for check in result.blockers] == ["INDUSTRY_IQ_PACK_UNAVAILABLE"]


def test_required_industry_iq_pack_passes_when_installed():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])
    spec = SkillPreflightSpec(
        skill_id="cepio.skill.drilling.test-pack-gate",
        industry_iq_packs={PACK_ID},
    )

    result = evaluate_skill_preflight(
        runtime,
        spec,
        actor_id="skill-agent-1",
        actor_roles={"drilling_npt_recommender"},
    )

    assert result.status == "READY"
    assert any(check.code == "INDUSTRY_IQ_PACK_AVAILABLE" for check in result.checks)
