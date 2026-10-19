from __future__ import annotations

import pytest

from cepio.application_contract import EvidenceReference
from cepio.bootstrap import build_runtime
from cepio.industry_iq import IndustryIQPackRegistry
from cepio.model import ObjectRef, OntologyObject
from cepio.performance_industry_iq import PERFORMANCE_RESPONSE_IQ_PACK
from cepio.reasoning_contribution import (
    BoundedReasoningHost,
    ReasoningContribution,
    ReasoningContributionEngine,
    ReasoningContributionError,
    ReasoningContributionRequest,
    ReasoningEvidence,
    ReasoningHypothesis,
    ReasoningUncertainty,
    UncertaintyBand,
)
from cepio.reliability_reasoning import (
    RELIABILITY_REASONING_CONTRIBUTOR_ID,
    RELIABILITY_REASONING_IQ_PACK,
    RELIABILITY_REASONING_IQ_PACK_ID,
    ReliabilityReasoningContributor,
)


def objects() -> tuple[OntologyObject, ...]:
    return (
        OntologyObject(
            id="COND-1",
            type="ConditionObservation",
            name="Drive-end vibration",
            properties={
                "metric": "vibration",
                "value": 9.2,
                "unit": "mm/s",
                "status": "degraded",
                "trend": "rising",
            },
        ),
        OntologyObject(
            id="COND-2",
            type="ConditionObservation",
            name="Non-drive-end vibration",
            properties={
                "metric": "vibration",
                "status": "normal",
            },
        ),
        OntologyObject(
            id="FAIL-1",
            type="FailureEvent",
            name="Bearing failure September",
            properties={"failure_mode": "bearing-degradation", "repeat_failure": True},
        ),
        OntologyObject(
            id="FAIL-2",
            type="FailureEvent",
            name="Bearing failure October",
            properties={"failure_mode": "bearing-degradation"},
        ),
        OntologyObject(
            id="WO-1",
            type="WorkOrder",
            name="Replace drive-end bearing",
            properties={"status": "reopened", "reopen_count": 1},
        ),
        OntologyObject(
            id="WO-2",
            type="WorkOrder",
            name="Alignment verification",
            properties={"status": "closed-verified", "verification_status": "verified"},
        ),
    )


def request(context: tuple[OntologyObject, ...]) -> ReasoningContributionRequest:
    return ReasoningContributionRequest(
        subject=ObjectRef(id="COMP-1", type="Equipment"),
        problem="How should Compressor C-4102 respond to availability being off_track?",
        performance_node_id="availability",
        performance_status="off_track",
        performance_evidence_refs=("pi://availability/C-4102",),
        context_object_refs=tuple(ObjectRef(id=obj.id, type=obj.type) for obj in context),
    )


def base_contribution(**overrides: object) -> ReasoningContribution:
    values: dict[str, object] = {
        "contributor_id": "stub",
        "contributor_version": "1.0.0",
        "domain": "stub-domain",
        "subject": ObjectRef(id="COMP-1", type="Equipment"),
    }
    values.update(overrides)
    return ReasoningContribution(**values)


class StubContributor:
    contributor_id = "stub"
    version = "1.0.0"
    domain = "stub-domain"
    required_pack_id = None

    def __init__(self, contribution: ReasoningContribution) -> None:
        self._contribution = contribution

    def contribute(
        self,
        contribution_request: ReasoningContributionRequest,
        host: BoundedReasoningHost,
    ) -> ReasoningContribution:
        del contribution_request, host
        return self._contribution


def test_reliability_pack_depends_on_performance_reasoning_and_adds_no_execution_authority():
    manifest = RELIABILITY_REASONING_IQ_PACK.manifest

    assert manifest.requires_packs == {"cepio.iq.performance.response": ">=0.1.0,<0.2.0"}
    assert manifest.functions == set()
    assert manifest.decisions == set()
    assert manifest.actions == set()

    runtime = build_runtime()
    registry = IndustryIQPackRegistry(core_version="0.4.0")
    registry.register(PERFORMANCE_RESPONSE_IQ_PACK)
    registry.register(RELIABILITY_REASONING_IQ_PACK)
    deployment = registry.install(runtime, [RELIABILITY_REASONING_IQ_PACK_ID])

    assert deployment.install_order == [
        "cepio.iq.performance.response",
        RELIABILITY_REASONING_IQ_PACK_ID,
    ]
    assert runtime.has_decision("performance-deviation-response") is True


def test_reliability_contribution_emits_hypotheses_uncertainty_and_information_gain():
    context = objects()
    host = BoundedReasoningHost(context)
    contributor = ReliabilityReasoningContributor()

    contribution = contributor.contribute(request(context), host)

    assert contribution.contributor_id == RELIABILITY_REASONING_CONTRIBUTOR_ID
    assert contribution.domain == "reliability"
    assert contribution.causal_claim_made is False
    assert contribution.authority == "recommend_only"
    assert {item.id for item in contribution.hypotheses} == {
        "reliability.condition-degradation",
        "reliability.recurring-failure-mechanism",
        "reliability.corrective-action-effectiveness",
    }
    condition = next(
        item for item in contribution.hypotheses if item.id == "reliability.condition-degradation"
    )
    assert condition.supporting_evidence_ids == ("reliability.condition:COND-1",)
    assert condition.contradicting_evidence_ids == ("reliability.condition:COND-2",)
    assert condition.confidence.value == "low"
    assert all(item.claim_status == "hypothesis_only" for item in contribution.hypotheses)
    assert len(contribution.uncertainties) == 3
    assert {item.priority for item in contribution.information_gain} == {"high", "medium"}
    assert all(item.authority == "recommend_only" for item in contribution.intervention_options)
    assert all(item.policy_required is True for item in contribution.intervention_options)


def test_reasoning_engine_requires_installed_domain_pack():
    context = objects()
    engine = ReasoningContributionEngine([ReliabilityReasoningContributor()])

    with pytest.raises(ReasoningContributionError) as exc_info:
        engine.evaluate(request(context), BoundedReasoningHost(context), installed_packs={})

    assert exc_info.value.code == "REASONING_PACK_NOT_INSTALLED"


def test_reasoning_engine_rejects_duplicate_contributor_identity():
    engine = ReasoningContributionEngine([ReliabilityReasoningContributor()])

    with pytest.raises(ReasoningContributionError) as exc_info:
        engine.register(ReliabilityReasoningContributor())

    assert exc_info.value.code == "CONTRIBUTOR_ALREADY_REGISTERED"


def test_bounded_reasoning_host_cannot_read_object_outside_authorized_context():
    host = BoundedReasoningHost(objects()[:1])

    with pytest.raises(ReasoningContributionError) as exc_info:
        host.read_object(ObjectRef(id="WO-SECRET", type="WorkOrder"))

    assert exc_info.value.code == "CONTEXT_OBJECT_NOT_AUTHORIZED"


def test_bounded_reasoning_host_rejects_identity_collision_and_type_mismatch():
    with pytest.raises(ReasoningContributionError) as exc_info:
        BoundedReasoningHost(
            (
                OntologyObject(id="X-1", type="Asset", name="Asset X"),
                OntologyObject(id="X-1", type="WorkOrder", name="Work X"),
            )
        )
    assert exc_info.value.code == "CONTEXT_IDENTITY_COLLISION"

    host = BoundedReasoningHost((OntologyObject(id="X-2", type="Asset", name="Asset X2"),))
    with pytest.raises(ReasoningContributionError) as exc_info:
        host.read_object(ObjectRef(id="X-2", type="WorkOrder"))
    assert exc_info.value.code == "CONTEXT_OBJECT_TYPE_MISMATCH"


def test_reasoning_contribution_validates_internal_evidence_and_hypothesis_references():
    evidence = ReasoningEvidence(
        id="evidence-1",
        reference=EvidenceReference(object_ref=ObjectRef(id="COND-1", type="ConditionObservation")),
        summary="Condition evidence",
    )
    hypothesis = ReasoningHypothesis(id="hypothesis-1", statement="Potential degradation")

    with pytest.raises(ValueError, match="evidence IDs must be unique"):
        base_contribution(evidence=(evidence, evidence))

    with pytest.raises(ValueError, match="hypothesis IDs must be unique"):
        base_contribution(hypotheses=(hypothesis, hypothesis))

    with pytest.raises(ValueError, match="unknown evidence IDs"):
        base_contribution(
            hypotheses=(
                ReasoningHypothesis(
                    id="hypothesis-missing-evidence",
                    statement="Potential degradation",
                    supporting_evidence_ids=("missing-evidence",),
                ),
            )
        )

    with pytest.raises(ValueError, match="unknown hypothesis IDs"):
        base_contribution(
            uncertainties=(
                ReasoningUncertainty(
                    id="uncertainty-1",
                    description="Mechanism remains uncertain",
                    level=UncertaintyBand.medium,
                    related_hypothesis_ids=("missing-hypothesis",),
                ),
            )
        )


def test_reasoning_engine_fails_closed_on_contributor_contract_mismatch():
    context = objects()[:1]
    contribution_request = request(context)
    host = BoundedReasoningHost(context)

    cases = (
        (
            base_contribution(contributor_id="other"),
            "CONTRIBUTOR_IDENTITY_MISMATCH",
        ),
        (
            base_contribution(contributor_version="2.0.0"),
            "CONTRIBUTOR_VERSION_MISMATCH",
        ),
        (
            base_contribution(domain="other-domain"),
            "CONTRIBUTOR_DOMAIN_MISMATCH",
        ),
        (
            base_contribution(subject=ObjectRef(id="COMP-2", type="Equipment")),
            "CONTRIBUTION_SUBJECT_MISMATCH",
        ),
    )

    for contribution, expected_code in cases:
        engine = ReasoningContributionEngine([StubContributor(contribution)])
        with pytest.raises(ReasoningContributionError) as exc_info:
            engine.evaluate(contribution_request, host)
        assert exc_info.value.code == expected_code


def test_reliability_contributor_fails_safe_when_context_has_no_reliability_evidence():
    unrelated = (
        OntologyObject(
            id="DOC-1",
            type="Document",
            name="Shift log",
            properties={"secret": "not inspected by the contributor"},
        ),
    )
    contribution = ReliabilityReasoningContributor().contribute(
        request(unrelated),
        BoundedReasoningHost(unrelated),
    )

    assert contribution.evidence == ()
    assert contribution.hypotheses == ()
    assert contribution.intervention_options == ()
    assert contribution.messages == (
        "Reliability context did not contain enough explicit evidence to form a supported hypothesis.",
    )
