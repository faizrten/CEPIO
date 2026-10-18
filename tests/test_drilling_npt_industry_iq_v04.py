from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.runtime import AuthorizationError


def _runtime_with_pack():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])
    return runtime


def _seed_runtime():
    runtime = _runtime_with_pack()
    objects = [
        OntologyObject(id="RIG-1", type="OperatingRig", name="Rig 1"),
        OntologyObject(id="WELL-1", type="Well", name="Well 1"),
        OntologyObject(
            id="ACT-NPT",
            type="ActivityInterval",
            name="Top drive downtime",
            properties={
                "startTime": "2026-10-18T10:00:00+03:00",
                "endTime": "2026-10-18T12:00:00+03:00",
            },
        ),
        OntologyObject(
            id="ACT-PROD",
            type="ActivityInterval",
            name="Drilling ahead",
            properties={
                "startTime": "2026-10-18T12:00:00+03:00",
                "endTime": "2026-10-18T13:30:00+03:00",
            },
        ),
        OntologyObject(
            id="CLASS-NPT",
            type="DrillingActivityClassification",
            name="Non-productive",
            properties={"isProductive": False, "sourceSystem": "synthetic-ddr"},
        ),
        OntologyObject(
            id="CLASS-PROD",
            type="DrillingActivityClassification",
            name="Productive",
            properties={"isProductive": True, "sourceSystem": "synthetic-ddr"},
        ),
    ]
    for obj in objects:
        runtime.upsert_object(obj)

    for activity_id, classification_id in (
        ("ACT-NPT", "CLASS-NPT"),
        ("ACT-PROD", "CLASS-PROD"),
    ):
        runtime.add_relationship(
            Relationship(
                type="activityOnRig",
                source=ObjectRef(id=activity_id, type="ActivityInterval"),
                target=ObjectRef(id="RIG-1", type="OperatingRig"),
            )
        )
        runtime.add_relationship(
            Relationship(
                type="activityForWell",
                source=ObjectRef(id=activity_id, type="ActivityInterval"),
                target=ObjectRef(id="WELL-1", type="Well"),
            )
        )
        runtime.add_relationship(
            Relationship(
                type="classifiedBy",
                source=ObjectRef(id=activity_id, type="ActivityInterval"),
                target=ObjectRef(id=classification_id, type="DrillingActivityClassification"),
            )
        )
    return runtime


def _calculate(runtime, *, activity_id="ACT-NPT", rig_id="RIG-1", well_id="WELL-1"):
    return runtime.call_function(
        "calculateNPTDuration",
        rig_id=rig_id,
        well_id=well_id,
        activity_ids=[activity_id],
    )


def test_drilling_iq_capabilities_are_not_core_defaults():
    runtime = build_runtime()
    assert runtime.has_function("calculateNPTDuration") is False
    assert runtime.has_decision("npt-follow-up-recommendation") is False
    assert runtime.has_action("CreateNPTInvestigation") is False
    assert runtime.industry_iq_packs == {}


def test_drilling_iq_pack_installs_explicit_capabilities():
    runtime = _runtime_with_pack()
    assert runtime.has_function("calculateNPTDuration") is True
    assert runtime.has_decision("npt-follow-up-recommendation") is True
    assert runtime.has_action("CreateNPTInvestigation") is True
    assert runtime.industry_iq_packs == {"cepio.iq.drilling.npt": "0.1.0"}


def test_duplicate_pack_install_fails_closed():
    runtime = _runtime_with_pack()
    with pytest.raises(ValueError, match="already installed"):
        install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])


def test_calculate_npt_duration_uses_governed_activity_semantics():
    runtime = _seed_runtime()
    result = runtime.call_function(
        "calculateNPTDuration",
        rig_id="RIG-1",
        well_id="WELL-1",
        activity_ids=["ACT-NPT", "ACT-PROD"],
    )
    assert result.total_npt_hours == 2.0
    assert result.nonproductive_activity_ids == ["ACT-NPT"]
    assert [item.duration_hours for item in result.intervals] == [2.0, 1.5]


def test_datetime_evidence_is_accepted_when_timezone_aware():
    runtime = _seed_runtime()
    activity = runtime.get_object("ACT-NPT")
    activity.properties["startTime"] = datetime(2026, 10, 18, 7, tzinfo=timezone.utc)
    activity.properties["endTime"] = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)
    runtime.upsert_object(activity, expected_version=activity.version)

    assert _calculate(runtime).total_npt_hours == 2.0


@pytest.mark.parametrize(
    ("property_name", "value", "message"),
    [
        ("startTime", "not-a-timestamp", "ISO-8601 timestamp"),
        ("startTime", None, "missing required governed property startTime"),
        ("startTime", "2026-10-18T10:00:00", "must include timezone context"),
    ],
)
def test_timestamp_evidence_fails_closed(property_name, value, message):
    runtime = _seed_runtime()
    activity = runtime.get_object("ACT-NPT")
    if value is None:
        activity.properties.pop(property_name)
    else:
        activity.properties[property_name] = value
    runtime.upsert_object(activity, expected_version=activity.version)

    with pytest.raises(ValueError, match=message):
        _calculate(runtime)


def test_npt_duration_rejects_wrong_or_unlinked_context():
    runtime = _seed_runtime()
    runtime.upsert_object(OntologyObject(id="RIG-WRONG", type="OperatingRig", name="Wrong rig"))
    runtime.upsert_object(OntologyObject(id="WELL-WRONG", type="Well", name="Wrong well"))
    runtime.upsert_object(OntologyObject(id="NOT-RIG", type="Equipment", name="Not rig"))
    runtime.upsert_object(OntologyObject(id="NOT-WELL", type="Equipment", name="Not well"))
    runtime.upsert_object(OntologyObject(id="NOT-ACTIVITY", type="Equipment", name="Not activity"))

    with pytest.raises(ValueError, match="not an OperatingRig"):
        _calculate(runtime, rig_id="NOT-RIG")
    with pytest.raises(ValueError, match="not a Well"):
        _calculate(runtime, well_id="NOT-WELL")
    with pytest.raises(ValueError, match="not an ActivityInterval"):
        _calculate(runtime, activity_id="NOT-ACTIVITY")
    with pytest.raises(ValueError, match="not linked to rig"):
        _calculate(runtime, rig_id="RIG-WRONG")
    with pytest.raises(ValueError, match="not linked to well"):
        _calculate(runtime, well_id="WELL-WRONG")


def test_npt_duration_rejects_reverse_time_range():
    runtime = _seed_runtime()
    activity = runtime.get_object("ACT-NPT")
    activity.properties["endTime"] = "2026-10-18T09:00:00+03:00"
    runtime.upsert_object(activity, expected_version=activity.version)

    with pytest.raises(ValueError, match="endTime precedes startTime"):
        _calculate(runtime)


def test_npt_duration_rejects_missing_or_conflicting_classification():
    runtime = _seed_runtime()
    unclassified = OntologyObject(
        id="ACT-UNKNOWN",
        type="ActivityInterval",
        name="Unknown interval",
        properties={
            "startTime": "2026-10-18T13:30:00+03:00",
            "endTime": "2026-10-18T14:00:00+03:00",
        },
    )
    runtime.upsert_object(unclassified)
    runtime.add_relationship(
        Relationship(
            type="activityOnRig",
            source=ObjectRef(id="ACT-UNKNOWN", type="ActivityInterval"),
            target=ObjectRef(id="RIG-1", type="OperatingRig"),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="activityForWell",
            source=ObjectRef(id="ACT-UNKNOWN", type="ActivityInterval"),
            target=ObjectRef(id="WELL-1", type="Well"),
        )
    )
    with pytest.raises(ValueError, match="no governed DrillingActivityClassification"):
        runtime.call_function(
            "calculateNPTDuration",
            rig_id="RIG-1",
            well_id="WELL-1",
            activity_ids=["ACT-UNKNOWN"],
        )

    runtime.add_relationship(
        Relationship(
            type="classifiedBy",
            source=ObjectRef(id="ACT-NPT", type="ActivityInterval"),
            target=ObjectRef(id="CLASS-PROD", type="DrillingActivityClassification"),
        )
    )
    with pytest.raises(ValueError, match="conflicting productivity"):
        runtime.call_function(
            "calculateNPTDuration",
            rig_id="RIG-1",
            well_id="WELL-1",
            activity_ids=["ACT-NPT"],
        )


def test_npt_duration_rejects_malformed_productivity_evidence():
    runtime = _seed_runtime()
    classification = runtime.get_object("CLASS-NPT")
    classification.properties["isProductive"] = "false"
    runtime.upsert_object(classification, expected_version=classification.version)

    with pytest.raises(ValueError, match="missing normalized boolean isProductive"):
        _calculate(runtime)


def test_npt_decision_is_activity_scoped_and_recommend_before_act():
    runtime = _seed_runtime()
    decision = runtime.save_decision(
        Decision(
            decision_type="npt-follow-up-recommendation",
            subject=ObjectRef(id="ACT-NPT", type="ActivityInterval"),
            problem="What follow-up is required for the NPT interval?",
            recommendation="Open an evidence-backed NPT investigation.",
            recommended_action="CreateNPTInvestigation",
            created_by="skill-agent-1",
        )
    )
    assert decision.decision_type == "npt-follow-up-recommendation"

    with pytest.raises(ValueError, match="does not allow subject type"):
        runtime.save_decision(
            Decision(
                decision_type="npt-follow-up-recommendation",
                subject=ObjectRef(id="RIG-1", type="OperatingRig"),
                problem="Wrong subject",
                recommendation="Do not persist",
                recommended_action="CreateNPTInvestigation",
            )
        )

    request = ActionRequest(
        action_type="CreateNPTInvestigation",
        target=ObjectRef(id="ACT-NPT", type="ActivityInterval"),
        actor_id="skill-agent-1",
        actor_roles={"drilling_npt_recommender"},
        parameters={"reason": "unexplained top-drive downtime"},
        decision_id=decision.id,
    )
    with pytest.raises(AuthorizationError) as exc:
        runtime.execute_action(request)
    assert exc.value.result is not None
    assert exc.value.result.status.value == "rejected"
    assert runtime.all_audits()[-1].decision_id == decision.id

    executed = runtime.execute_action(
        request.model_copy(
            update={
                "actor_id": "drilling-engineer-1",
                "actor_roles": {"drilling_engineer"},
            }
        )
    )
    assert executed.status.value == "executed"
    investigation_id = str(executed.effects["investigation_id"])
    investigation = runtime.get_object(investigation_id)
    assert investigation.type == "NPTInvestigation"
    assert runtime.neighbors(investigation_id, "investigatesActivity")[0].id == "ACT-NPT"
