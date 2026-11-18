"""IC-1 synthetic contract checks; no industrial diagnosis or live source proof."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.capability_registry import CapabilityRecord, CapabilityRegistry
from cepio.competence_activation import (
    ActivationPolicy,
    ActivationScope,
    ActivationStatus,
    ActivationTask,
    EvidenceAdmission,
    activate_competence,
)

AT = datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc)
ASSET = "fixture:refinery/K-201"
CAPABILITY = "industrial.reliability.compressor-vibration-triage"
REQUIREMENTS = {"condition signal", "maintenance history", "operating context"}
REFS = {
    "condition signal": "fixture:condition",
    "maintenance history": "fixture:maintenance",
    "operating context": "fixture:operating",
}


def capability(**changes) -> CapabilityRecord:
    record = {
        "id": CAPABILITY,
        "version": "0.1",
        "title": "Compressor vibration triage",
        "description": "Compressor vibration investigation and operating state review",
        "layer": "DOMAIN",
        "maturity": "QUALIFIED",
        "evidence_requirements": REQUIREMENTS,
        "evidence": [
            {
                "id": "fixture:qualification-reference",
                "domain": "refinery",
                "kind": "synthetic-contract",
                "artifact": "tests/test_competence_activation_ic1.py",
            }
        ],
        "provenance": {"mode": "synthetic-contract", "source_ids": ["local-fixture"]},
    }
    record.update(changes)
    return CapabilityRecord.model_validate(record)


def registry(*records) -> CapabilityRegistry:
    return CapabilityRegistry(
        id="test-registry",
        version="0.1",
        capabilities=list(records) if records else [capability()],
    )


def scope(**changes) -> ActivationScope:
    content = {
        "actor_id": "fixture:engineer",
        "tenant_id": "fixture-tenant",
        "permitted_asset_ids": {ASSET},
        "permitted_capability_ids": {CAPABILITY},
        "permitted_evidence_refs": set(REFS.values()),
    }
    content.update(changes)
    return ActivationScope.model_validate(content)


def task(**changes) -> ActivationTask:
    content = {
        "query_text": "Investigate compressor vibration and operating state",
        "asset_id": ASSET,
        "at": AT,
    }
    content.update(changes)
    return ActivationTask.model_validate(content)


def receipt(requirement: str, **changes) -> EvidenceAdmission:
    content = {
        "requirement": requirement,
        "reference": REFS[requirement],
        "tenant_id": "fixture-tenant",
        "asset_id": ASSET,
        "observed_at": AT - timedelta(minutes=30),
        "valid_until": AT + timedelta(minutes=30),
        "state": "HOST_ADMITTED",
    }
    content.update(changes)
    return EvidenceAdmission.model_validate(content)


def evidence():
    return [receipt(item) for item in sorted(REQUIREMENTS)]


def activate(**changes):
    params = {
        "task": task(),
        "scope": scope(),
        "evidence": evidence(),
    }
    params.update(changes)
    return activate_competence(registry(), **params)


def test_sufficient_synthetic_evidence_only_routes_review_candidate():
    result = activate()
    assert result.status is ActivationStatus.CANDIDATE
    assert result.capability_id == CAPABILITY
    assert result.capability_version == "0.1"
    assert result.reason_codes == []
    assert set(result.admitted_evidence_refs) == set(REFS.values())
    assert 0.35 < result.route_score <= 1
    payload = result.model_dump(mode="json")
    assert not any(key in payload for key in ("decision", "diagnosis", "action", "approved"))


def test_missing_maintenance_history_fails_closed():
    remaining = [item for item in evidence() if item.requirement != "maintenance history"]
    result = activate(evidence=remaining)
    assert result.status is ActivationStatus.BLOCKED
    assert result.missing_requirements == ["maintenance history"]
    assert "REQUIRED_EVIDENCE_MISSING" in result.reason_codes
    assert result.admitted_evidence_refs == []


@pytest.mark.parametrize(
    "state,reason",
    [
        ("CONFLICT", "CONFLICTING_EVIDENCE"),
        ("UNVERIFIED", "UNVERIFIED_EVIDENCE"),
    ],
)
def test_conflict_or_unverified_source_blocks_even_when_a_clean_receipt_exists(state, reason):
    source = receipt("maintenance history", state=state, reference="fixture:maintenance")
    result = activate(evidence=evidence() + [source])
    assert result.status is ActivationStatus.BLOCKED
    assert reason in result.reason_codes
    assert result.admitted_evidence_refs == []


def test_duplicate_source_identity_with_changed_validity_is_not_silently_accepted():
    duplicate = receipt("maintenance history", observed_at=AT - timedelta(minutes=5))
    result = activate(evidence=evidence() + [duplicate])
    assert result.status is ActivationStatus.BLOCKED
    assert "CONFLICTING_EVIDENCE" in result.reason_codes


@pytest.mark.parametrize(
    "change",
    [
        {"valid_until": AT - timedelta(minutes=1), "observed_at": AT - timedelta(hours=1)},
        {"observed_at": AT + timedelta(minutes=1), "valid_until": AT + timedelta(hours=1)},
    ],
)
def test_stale_and_future_dated_evidence_do_not_qualify(change):
    items = [receipt("maintenance history", **change)]
    items += [receipt("condition signal"), receipt("operating context")]
    result = activate(evidence=items)
    assert result.status is ActivationStatus.BLOCKED
    assert "STALE_OR_FUTURE_EVIDENCE" in result.reason_codes


@pytest.mark.parametrize(
    "change",
    [
        {"tenant_id": "other-tenant"},
        {"asset_id": "fixture:refinery/K-202"},
        {"reference": "fixture:unpermitted-evidence"},
    ],
)
def test_foreign_or_unpermitted_receipts_do_not_satisfy_required_evidence(change):
    items = [receipt("maintenance history", **change)]
    items += [receipt("condition signal"), receipt("operating context")]
    result = activate(evidence=items)
    assert result.status is ActivationStatus.BLOCKED
    assert result.missing_requirements == ["maintenance history"]
    assert result.admitted_evidence_refs == []


def test_asset_denial_precedes_route_and_discloses_no_capability():
    result = activate(scope=scope(permitted_asset_ids=set()))
    assert result.status is ActivationStatus.BLOCKED
    assert result.reason_codes == ["ASSET_NOT_AUTHORIZED"]
    assert result.capability_id is None
    assert result.admitted_evidence_refs == []


def test_scope_denies_nonpermitted_capability_without_revealing_it():
    result = activate(scope=scope(permitted_capability_ids=set()))
    assert result.status is ActivationStatus.NO_MATCH
    assert result.capability_id is None
    assert result.admitted_evidence_refs == []


@pytest.mark.parametrize("maturity", ["EXPERIMENTAL", "PREVIEW"])
def test_prequalified_capabilities_are_not_implicitly_activated(maturity):
    result = activate_competence(
        registry(capability(maturity=maturity)), task=task(), scope=scope(), evidence=evidence()
    )
    assert result.status is ActivationStatus.NO_MATCH


def test_registry_qualification_reference_is_required_but_not_independent_proof():
    result = activate_competence(
        registry(capability(evidence=[])), task=task(), scope=scope(), evidence=evidence()
    )
    assert result.status is ActivationStatus.BLOCKED
    assert "CAPABILITY_ASSURANCE_NOT_RECORDED" in result.reason_codes


def test_required_evidence_contract_cannot_be_empty():
    result = activate_competence(
        registry(capability(evidence_requirements=set())),
        task=task(),
        scope=scope(),
        evidence=evidence(),
    )
    assert result.status is ActivationStatus.BLOCKED
    assert "NO_EVIDENCE_REQUIREMENTS" in result.reason_codes


def test_two_equally_matched_qualified_capabilities_are_ambiguous():
    second = capability(id="industrial.reliability.alternative-compressor-method")
    result = activate_competence(
        registry(capability(), second),
        task=task(),
        scope=scope(permitted_capability_ids={CAPABILITY, second.id}),
        evidence=evidence(),
    )
    assert result.status is ActivationStatus.AMBIGUOUS
    assert result.capability_id is None
    assert result.admitted_evidence_refs == []


def test_unrelated_job_does_not_select_something_merely_because_it_is_qualified():
    result = activate(task=task(query_text="Forecast payroll tax obligations"))
    assert result.status is ActivationStatus.NO_MATCH


@pytest.mark.parametrize(
    "task_changes",
    [
        {"query_text": ""},
        {"query_text": " "},
        {"query_text": "   "},
        {"at": datetime(2026, 11, 19, 9, 0)},
    ],
)
def test_blank_task_or_naive_time_rejected(task_changes):
    with pytest.raises(ValidationError):
        task(**task_changes)


def test_source_validity_requires_aware_ordered_window():
    with pytest.raises(ValidationError):
        receipt("maintenance history", valid_until=AT - timedelta(hours=1))
    with pytest.raises(ValidationError):
        receipt("maintenance history", observed_at=datetime(2026, 11, 19, 9, 0))


def test_host_models_reject_unknown_authority_claims():
    with pytest.raises(ValidationError):
        ActivationScope.model_validate(
            {
                **scope().model_dump(),
                "roles": ["administrator"],
            }
        )
    with pytest.raises(ValidationError):
        ActivationTask.model_validate(
            {
                **task().model_dump(),
                "approval": True,
            }
        )


def test_lexical_threshold_is_not_exposed_as_confidence_or_a_decision():
    result = activate(policy=ActivationPolicy(minimum_route_score=0.99))
    assert result.status is ActivationStatus.NO_MATCH
