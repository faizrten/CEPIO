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
