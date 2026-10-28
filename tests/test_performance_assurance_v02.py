"""Assurance v0.2: host-owned evidence handles and Decision receipts."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from cepio.performance_assurance import (
    AssuranceError, AssurancePolicy, AssuredPerformanceService,
    EvidenceHandleRequest, SourceVersionLock, verify_assurance_receipt,
)
from cepio.performance_executive import ExecutivePerformanceService
from cepio.performance_industry_iq import PerformanceIndustryIQService
from test_performance_evidence_binding_v01 import (
    EVALUATED_AT, LEAKAGE, NPT, ORG, SAFETY, SOURCE, UPTIME,
    context, entries, fixture,
)


def source_key(record):
    return f"{SOURCE}:performance-observation:{record}:revision-001"


def policy():
    pairs = (
        (NPT, "rig07-npt"), (UPTIME, "rig07-uptime"),
        (LEAKAGE, "rig07-leakage"), (SAFETY, "rig07-safety"),
    )
    return AssurancePolicy(
        policy_id="rig07-development", policy_version="0.2.0",
        organization_id=ORG, plan_id="rig07-ceo-performance",
        subject_id="rig-07", focus_node_id=NPT,
        source_locks=tuple(
            SourceVersionLock(node_id=node, reference_key=source_key(record),
                              record_version="revision-001")
            for node, record in pairs
        ),
    )


def make_service(*, data=None, policies=None, clock=None, capacity=1024):
    bound, source, app, performance = fixture(data=data)
    executive = ExecutivePerformanceService(PerformanceIndustryIQService(performance, app))
    tick = clock if clock is not None else [EVALUATED_AT + timedelta(minutes=20)]
    return (
        AssuredPerformanceService(
            bound, executive, policies or (policy(),),
            clock=lambda: tick[0], max_handles=capacity,
        ),
        source, tick,
    )


def request(*, offset=10, mode="historical_replay"):
    return EvidenceHandleRequest(
        plan_id="rig07-ceo-performance",
        evaluated_at=EVALUATED_AT + timedelta(minutes=offset),
        mode=mode,
    )


def fails(code, callback):
    with pytest.raises(AssuranceError) as caught:
        callback()
    assert caught.value.code == code


def test_issued_handle_produces_stable_nonexecuting_receipt():
    service, binding, _ = make_service()
    handle = service.issue(request(), context())
    assert len(handle.handle) > 32
    calls = len(binding.calls)
    result = service.preview(handle.handle, context(), financial_node_id=LEAKAGE)
    assert len(binding.calls) == calls
    assert result.receipt.evidence_trust == "host_bound_not_source_attested"
    assert result.receipt.assurance_status == "development_conformance_only"
    assert len(result.receipt.source_record_keys) == 4
    assert result.package.financial_observation.value == 32000
    assert result.package.evidence_status == "caller_supplied_unverified"
    assert result.receipt.authority == "recommend_only"
    assert not result.receipt.decision_persisted
    assert not result.receipt.workflow_started
    assert not result.receipt.action_executed
    assert verify_assurance_receipt(result.receipt)
    assert service.preview(handle.handle, context(), financial_node_id=LEAKAGE) == result


def test_handle_rejects_cross_tenant_actor_and_role():
    service, _, _ = make_service()
    handle = service.issue(request(), context()).handle
    fails("HANDLE_UNKNOWN", lambda: service.preview("not-real", context()))
    fails("HANDLE_ACCESS_DENIED", lambda: service.preview(handle, context("other-tenant")))
    fails("HANDLE_ACCESS_DENIED", lambda: service.preview(
        handle, context().model_copy(update={"actor_id": "another-actor"})))
    fails("HANDLE_ACCESS_DENIED", lambda: service.preview(handle, context(role="auditor")))
    fails("TENANT_DENIED", lambda: service.issue(request(), context("other-tenant")))
    fails("ROLE_DENIED", lambda: service.issue(request(), context(role="auditor")))


def test_expiry_and_capacity_are_fail_closed():
    service, _, clock = make_service(capacity=1)
    handle = service.issue(request(), context()).handle
    fails("HANDLE_CAPACITY", lambda: service.issue(request(), context()))
    clock[0] += timedelta(seconds=301)
    fails("HANDLE_EXPIRED", lambda: service.preview(handle, context()))
    assert service.issue(request(), context()).handle != handle


def test_historical_replay_does_not_imply_current_freshness():
    service, source, _ = make_service()
    fails("CURRENT_EVIDENCE_STALE", lambda: service.issue(
        request(mode="current"), context()))
    fails("EVALUATION_TIME_INVALID", lambda: service.issue(
        request(offset=90), context()))
    fails("EVALUATION_TIME_INVALID", lambda: service.issue(
        EvidenceHandleRequest(
            plan_id="rig07-ceo-performance",
            evaluated_at=EVALUATED_AT.replace(tzinfo=None),
        ), context()))
    assert source.calls == []


def test_version_conflicts_are_denied():
    changed = policy().model_copy(update={
        "source_locks": (
            SourceVersionLock(
                node_id=NPT, reference_key=source_key("rig07-npt"),
                record_version="revision-002",
            ),
            *policy().source_locks[1:],
        ),
    })
    service, _, _ = make_service(policies=(changed,))
    fails("SOURCE_VERSION_CONFLICT", lambda: service.issue(request(), context()))
    limited = policy().model_copy(update={
        "source_locks": policy().source_locks[:2]
    })
    service, _, _ = make_service(policies=(limited,))
    fails("UNPINNED_SOURCE", lambda: service.issue(request(), context()))


def test_optional_finance_and_safety_remain_unknown():
    data = entries()
    del data["rig07-leakage"]
    del data["rig07-safety"]
    service, _, _ = make_service(data=data)
    token = service.issue(request(), context()).handle
    result = service.preview(token, context(), financial_node_id=LEAKAGE)
    assert result.package.financial_status == "evidence_missing"
    assert result.package.financial_observation is None
    assert len(result.receipt.source_record_keys) == 2
    assert verify_assurance_receipt(result.receipt)


def test_receipt_edit_and_client_evidence_are_not_trusted():
    service, _, _ = make_service()
    token = service.issue(request(), context()).handle
    receipt = service.preview(token, context()).receipt
    assert verify_assurance_receipt(receipt)
    assert not verify_assurance_receipt(
        receipt.model_copy(update={"actor_id": "other-actor"})
    )
    with pytest.raises(ValidationError):
        EvidenceHandleRequest.model_validate({
            "plan_id": "rig07-ceo-performance",
            "evaluated_at": EVALUATED_AT,
            "observations": [{"value": 0.0}],
            "evidence_trust": "source_attested",
        })


def test_bad_host_policy_and_clock_fail_closed():
    with pytest.raises(ValueError):
        make_service(policies=(policy(), policy()))
    duplicate = policy().model_copy(update={
        "source_locks": (policy().source_locks[0], policy().source_locks[0])
    })
    with pytest.raises(ValueError):
        make_service(policies=(duplicate,))
    service, _, _ = make_service(
        clock=[EVALUATED_AT.replace(tzinfo=None)]
    )
    fails("TRUSTED_CLOCK_INVALID", lambda: service.issue(request(), context()))
