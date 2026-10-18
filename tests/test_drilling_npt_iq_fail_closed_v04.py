import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship


def test_registry_disabled_runtime_still_rejects_wrong_classification_target():
    runtime = build_runtime(validate_types=False)
    install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])

    for obj in (
        OntologyObject(id="RIG-1", type="OperatingRig", name="Rig 1"),
        OntologyObject(id="WELL-1", type="Well", name="Well 1"),
        OntologyObject(
            id="ACT-1",
            type="ActivityInterval",
            name="NPT interval",
            properties={
                "startTime": "2026-10-18T10:00:00+03:00",
                "endTime": "2026-10-18T11:00:00+03:00",
            },
        ),
        OntologyObject(
            id="BAD-CLASS",
            type="Risk",
            name="Wrong classification target",
            properties={"isProductive": False},
        ),
    ):
        runtime.upsert_object(obj)

    for relationship in (
        Relationship(
            type="activityOnRig",
            source=ObjectRef(id="ACT-1", type="ActivityInterval"),
            target=ObjectRef(id="RIG-1", type="OperatingRig"),
        ),
        Relationship(
            type="activityForWell",
            source=ObjectRef(id="ACT-1", type="ActivityInterval"),
            target=ObjectRef(id="WELL-1", type="Well"),
        ),
        Relationship(
            type="classifiedBy",
            source=ObjectRef(id="ACT-1", type="ActivityInterval"),
            target=ObjectRef(id="BAD-CLASS", type="Risk"),
        ),
    ):
        runtime.add_relationship(relationship)

    with pytest.raises(ValueError, match="is not a DrillingActivityClassification"):
        runtime.call_function(
            "calculateNPTDuration",
            rig_id="RIG-1",
            well_id="WELL-1",
            activity_ids=["ACT-1"],
        )
