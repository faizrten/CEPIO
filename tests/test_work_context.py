from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.accc_host_admission import HostPrincipal
from cepio.work_context import (
    EvidenceReceipt,
    WorkContextRequest,
    WorkQuestion,
    WorkSnapshot,
    read_work_context,
)

NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


class Host:
    def __init__(self, **updates):
        self.principal = HostPrincipal("professional", "tenant-a", frozenset({"reader"}))
        self.denied = False
        self.loads = 0
        self.snapshot = WorkSnapshot(
            **dict(
                {
                    "work_id": "customer-problem-123",
                    "revision": 2,
                    "tenant_id": "tenant-a",
                    "objective": "Understand recurring quality losses",
                    "questions": tuple(
                        WorkQuestion(
                            id=stage,
                            stage=stage,
                            text=f"Help with {stage}",
                            required_evidence_ids={"source"},
                            capability_admission="ready",
                        )
                        for stage in ("understand", "assess", "work", "learn")
                    ),
                    "evidence": (
                        EvidenceReceipt(
                            id="source",
                            version="v2",
                            observed_at=NOW,
                            valid_until=NOW + timedelta(hours=1),
                            applicable=True,
                        ),
                    ),
                    "selected_evidence_ids": {"source"},
                },
                **updates,
            )
        )

    def authenticated_principal(self):
        return self.principal

    def load_authorized_snapshot(self, work_id, principal):
        self.loads += 1
        if self.denied:
            raise PermissionError("rights revoked")
        return self.snapshot


def read(host, revision=2, at=NOW):
    return read_work_context(
        WorkContextRequest(work_id="customer-problem-123", expected_revision=revision),
        host,
        at=at,
    )


def test_four_stages_ready_never_grants_job_or_action_authority():
    view = read(Host())
    assert len(view.questions) == 4
    assert all(q.assistance_state == "ready_for_assessment" for q in view.questions)
    assert view.job_readiness == "not_assessed"
    assert view.action_authority == "not_granted"
    assert view.read_only
    assert view.evidence[0].version == "v2"


@pytest.mark.parametrize(
    "updates,code",
    [
        ({"evidence": ()}, "MISSING_EVIDENCE"),
        ({"selected_evidence_ids": set()}, "REQUIRED_EVIDENCE_NOT_SELECTED"),
    ],
)
def test_missing_or_dropped_required_evidence(updates, code):
    q = read(Host(**updates)).questions[0]
    assert q.assistance_state == "unresolved"
    assert q.evidence_completeness == "incomplete"
    assert code in q.blockers


@pytest.mark.parametrize("delta", [-1, 3600, 7200])
def test_future_or_expired_evidence(delta):
    assert (
        "EVIDENCE_NOT_CURRENT"
        in read(Host(), at=NOW + timedelta(seconds=delta)).questions[0].blockers
    )


@pytest.mark.parametrize(
    "updates,code",
    [
        ({"conflict": True}, "EVIDENCE_CONFLICT"),
        ({"applicable": False}, "EVIDENCE_NOT_APPLICABLE"),
    ],
)
def test_source_conflict_and_applicability(updates, code):
    host = Host()
    receipt = host.snapshot.evidence[0].model_copy(update=updates)
    host.snapshot = host.snapshot.model_copy(update={"evidence": (receipt,)})
    assert code in read(host).questions[0].blockers


@pytest.mark.parametrize("status", ["blocked", "unknown"])
def test_complete_evidence_does_not_grant_capability(status):
    host = Host()
    q = host.snapshot.questions[0].model_copy(update={"capability_admission": status})
    host.snapshot = host.snapshot.model_copy(update={"questions": (q,)})
    result = read(host).questions[0]
    assert result.evidence_completeness == "complete"
    assert result.assistance_state == "unresolved"


@pytest.mark.parametrize("updates", [{"tenant_id": "other"}, {"work_id": "other"}])
def test_mismatched_scope_denied(updates):
    with pytest.raises(PermissionError):
        read(Host(**updates))


def test_revision_and_rights_rechecked_on_resume():
    host = Host()
    read(host)
    with pytest.raises(ValueError, match="revision changed"):
        read(host, revision=1)
    host.denied = True
    with pytest.raises(PermissionError):
        read(host)
    assert host.loads == 3


def test_missing_principal_denied_before_load():
    host = Host()
    host.principal = None
    with pytest.raises(PermissionError):
        read(host)
    assert host.loads == 0


@pytest.mark.parametrize("field", ["tenant_id", "actor_id", "roles", "approved"])
def test_request_cannot_supply_authority(field):
    with pytest.raises(ValidationError):
        WorkContextRequest(work_id="x", expected_revision=1, **{field: "fake"})


def test_invalid_time_duplicate_ids_and_empty_evidence_requirements():
    host = Host()
    with pytest.raises(ValueError, match="timezone"):
        read(host, at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="positive"):
        EvidenceReceipt(id="x", version="1", observed_at=NOW, valid_until=NOW, applicable=True)
    with pytest.raises(ValidationError, match="duplicate"):
        Host(evidence=host.snapshot.evidence * 2)
    with pytest.raises(ValidationError):
        WorkQuestion(id="x", stage="work", text="x", required_evidence_ids=set())


def test_projection_does_not_mutate_snapshot():
    host = Host()
    before = host.snapshot.model_dump_json()
    read(host)
    assert host.snapshot.model_dump_json() == before
