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


def test_assistance_names_missing_source_without_inventing_version():
    result = read(Host(evidence=())).questions[0]
    assert result.evidence_refs == ()
    assert result.evidence_gaps[0].evidence_id == "source"
    assert result.evidence_gaps[0].source_version is None
    assert "authorized source" in result.evidence_gaps[0].next_check
    assert "Resolve" in result.guidance


def test_changed_evidence_reassesses_and_retains_original_result():
    host = Host()
    original = read(host)
    changed = host.snapshot.evidence[0].model_copy(update={"version": "v3", "conflict": True})
    host.snapshot = host.snapshot.model_copy(update={"revision": 3, "evidence": (changed,)})
    with pytest.raises(ValueError, match="revision changed"):
        read(host)
    revised = read(host, revision=3)
    assert original.questions[0].assistance_state == "ready_for_assessment"
    assert original.questions[0].evidence_refs[0].version == "v2"
    assert revised.questions[0].assistance_state == "unresolved"
    assert revised.questions[0].evidence_gaps[0].source_version == "v3"
    assert "technical authority" in revised.questions[0].evidence_gaps[0].next_check


def test_expiry_reassesses_without_needing_source_revision_change():
    host = Host()
    before = read(host)
    after = read(host, at=NOW + timedelta(hours=1))
    assert before.revision == after.revision
    assert before.questions[0].assistance_state == "ready_for_assessment"
    assert after.questions[0].assistance_state == "unresolved"
    assert after.questions[0].evidence_gaps[0].reason == "EVIDENCE_NOT_CURRENT"


def test_ready_guidance_does_not_claim_to_answer_domain_question():
    ready = read(Host()).questions[0]
    assert "no technical conclusion or work permission" in ready.guidance
    host = Host()
    question = host.snapshot.questions[0].model_copy(update={"capability_admission": "unknown"})
    host.snapshot = host.snapshot.model_copy(update={"questions": (question,)})
    assert "admitted capability is still needed" in read(host).questions[0].guidance


def test_walkthrough_is_generated_by_current_core_contract():
    import runpy
    from pathlib import Path

    demo = runpy.run_path(str(Path(__file__).parents[1] / "examples/work_context_walkthrough.py"))
    views = demo["walkthrough"]()
    missing = views["missing"]["questions"][0]
    current = views["current"]["questions"][0]
    changed = views["changed"]["questions"][0]
    assert missing["evidence_gaps"][0]["evidence_id"] == "approved-procedure"
    assert current["evidence_completeness"] == "complete"
    assert current["assistance_state"] == "unresolved"
    assert changed["evidence_gaps"][0]["reason"] == "EVIDENCE_CONFLICT"
    assert changed["evidence_gaps"][0]["source_version"] == "2"
