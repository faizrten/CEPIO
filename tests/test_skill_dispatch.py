from dataclasses import replace

import pytest

from cepio import SkillCandidate, dispatch_skill
from cepio.bootstrap import build_runtime
from test_skill_preflight import equipment_skill_spec


def candidate(skill_id="equipment", status="BOUND"):
    spec = equipment_skill_spec().model_copy(update={"skill_id": skill_id})
    return SkillCandidate(skill_id, status, spec)


def run(candidates, roles=None, match=True):
    calls = []
    result = dispatch_skill(
        build_runtime(), candidates, actor_id="actor",
        actor_roles=roles or {"ai_agent_recommender"},
        matches=lambda sid: calls.append(("match", sid)) or match,
        dispatch=lambda sid: calls.append(("dispatch", sid)) or sid,
    )
    return result, calls


@pytest.mark.parametrize("role", ["auditor", "maintenance_engineer"])
def test_blocked_actors_never_reach_trigger_or_dispatch(role):
    result, calls = run([candidate()], {role})
    assert result.status == "NO_READY_SKILL"
    assert result.preflights[0].blockers
    assert calls == []


def test_static_blocked_is_not_preflighted_or_matched():
    result, calls = run([SkillCandidate("blocked", "BLOCKED")])
    assert result.status == "NO_READY_SKILL"
    assert result.preflights == ()
    assert calls == []


def test_empty_and_no_trigger_match():
    assert run([])[0].status == "NO_READY_SKILL"
    result, calls = run([candidate()], match=False)
    assert result.status == "NO_MATCH"
    assert calls == [("match", "equipment")]


def test_unique_ready_dispatch():
    result, calls = run([candidate(), candidate("blocked", "BLOCKED")])
    assert result.status == "DISPATCHED"
    assert result.output == "equipment"
    assert calls == [("match", "equipment"), ("dispatch", "equipment")]


def test_conflicts_are_order_independent_and_never_dispatch():
    for candidates in ([candidate("z"), candidate("a")], [candidate("a"), candidate("z")]):
        result, calls = run(candidates)
        assert result.status == "CONFLICT"
        assert result.matched_ids == ("a", "z")
        assert calls == [("match", "a"), ("match", "z")]


def test_multiple_ready_unique_match_dispatches_only_matching_skill():
    result = dispatch_skill(build_runtime(), [candidate("a"), candidate("b")],
        actor_id="actor", actor_roles={"ai_agent_recommender"},
        matches=lambda sid: sid == "b", dispatch=lambda sid: sid)
    assert result.status == "DISPATCHED"
    assert result.ready_ids == ("a", "b")
    assert result.output == "b"


@pytest.mark.parametrize("candidates", [
    [candidate(), candidate()],
    [SkillCandidate("bad", "BOUND")],
    [replace(candidate(), skill_id="mismatch")],
])
def test_invalid_configuration_fails_before_matching(candidates):
    with pytest.raises(ValueError):
        run(candidates)


def test_preflight_is_repeated_for_each_dispatch():
    runtime = build_runtime()
    spec = candidate()
    kwargs = dict(actor_id="actor", matches=lambda sid: True, dispatch=lambda sid: sid)
    assert dispatch_skill(runtime, [spec], actor_roles={"ai_agent_recommender"}, **kwargs).status == "DISPATCHED"
    assert dispatch_skill(runtime, [spec], actor_roles={"maintenance_engineer"}, **kwargs).status == "NO_READY_SKILL"
