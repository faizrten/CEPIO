from dataclasses import replace
from datetime import timedelta

import pytest

from cepio.auth import ActorContext
from cepio.repositories import InMemoryRepository, SQLiteRepository
from cepio.semantic_mapping_gate import SemanticMappingGate
from cepio.semantic_review_store import EventMappingReviewStore, ReviewConflictError
from test_semantic_mapping_gate import NOW, setup_gate


def setup_store(repo):
    _, state, envelope, graph, params = setup_gate()
    state["attested"] = True
    store = EventMappingReviewStore(
        repo,
        principal=lambda: state["actor"],
        authorize=lambda actor, op, key: state["allowed"],
        attest=lambda actor, review, token: state["attested"],
        clock=lambda: state["now"],
    )
    gate = SemanticMappingGate(
        principal=lambda: state["actor"],
        authorize=lambda actor, key: state["allowed"],
        lookup=store.lookup,
        clock=lambda: state["now"],
    )
    return store, gate, state, envelope, graph, params


def revision(review, identity, **changes):
    return replace(review, decision=review.decision.model_copy(update={"id": identity}), **changes)


def test_sqlite_restart_revocation_restoration_preserves_history(tmp_path):
    path = tmp_path / "reviews.sqlite"
    repo = SQLiteRepository(path)
    store, gate, state, envelope, graph, params = setup_store(repo)
    review = state["review"]
    key = review.decision.subject_id
    assert store.lookup("tenant-a", key) is None
    with pytest.raises(PermissionError):
        gate.resolve(envelope, graph, **params)
    assert store.record(review, expected_revision=0, attestation_id="test-attestation-1") == 1
    assert gate.resolve(envelope, graph, **params).target_iri == review.target_iri
    repo._conn.close()
    store, gate, state, envelope, graph, params = setup_store(SQLiteRepository(path))
    assert gate.resolve(envelope, graph, **params).decision_id == review.decision.id
    store.record(
        revision(review, "revoke-2", active=False), expected_revision=1, attestation_id="test-2"
    )
    with pytest.raises(PermissionError, match="revoked"):
        gate.resolve(envelope, graph, **params)
    store.record(revision(review, "restore-3"), expected_revision=2, attestation_id="test-3")
    assert gate.resolve(envelope, graph, **params).decision_id == "restore-3"
    history = store.history("tenant-a", key)
    assert [e.properties["active"] for e in history] == [True, False, True]
    history[0].properties["active"] = False
    assert store.history("tenant-a", key)[0].properties["active"] is True
    envelope.evidence["term"]["description"] = "changed meaning"
    with pytest.raises(PermissionError, match="No current"):
        gate.resolve(envelope, graph, **params)


@pytest.mark.parametrize("operation", ["read", "record"])
@pytest.mark.parametrize("failure", ["tenant", "policy", "actor"])
def test_unauthorized_journal_access(operation, failure):
    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    if failure == "tenant":
        state["actor"] = ActorContext("reader", set(), "other")
    elif failure == "actor":
        state["actor"] = ActorContext("", set(), "tenant-a")
    else:
        state["allowed"] = False
    with pytest.raises(PermissionError):
        if operation == "read":
            store.lookup("tenant-a", state["review"].decision.subject_id)
        else:
            store.record(state["review"], expected_revision=0, attestation_id="test")
    assert not repo._events


def test_unverified_attestation_does_not_write():
    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    state["attested"] = False
    with pytest.raises(PermissionError, match="attestation"):
        store.record(state["review"], expected_revision=0, attestation_id="unverified")
    assert not repo._events


@pytest.mark.parametrize("failure", ["naive", "expired", "blank-attestation", "negative-revision"])
def test_invalid_review_does_not_write(failure):
    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    review = state["review"]
    if failure == "naive":
        review = replace(review, expires_at=NOW.replace(tzinfo=None))
    if failure == "expired":
        review = replace(review, expires_at=NOW - timedelta(seconds=1))
    with pytest.raises(ValueError):
        store.record(
            review,
            expected_revision=-1 if failure == "negative-revision" else 0,
            attestation_id="" if failure == "blank-attestation" else "test",
        )
    assert not repo._events


def test_stale_version_and_reused_decision_cannot_overwrite():
    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    review = state["review"]
    store.record(review, expected_revision=0, attestation_id="test")
    with pytest.raises(ReviewConflictError, match="revision changed"):
        store.record(revision(review, "new"), expected_revision=0, attestation_id="test")
    with pytest.raises(ReviewConflictError, match="decision ID"):
        store.record(review, expected_revision=1, attestation_id="test")
    assert len(repo._events) == 1


@pytest.mark.parametrize("failure", ["bad-event", "fork"])
def test_invalid_journal_history_fails_closed(failure):
    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    review = state["review"]
    store.record(review, expected_revision=0, attestation_id="test")
    if failure == "bad-event":
        repo._events[0].type = "Unknown"
    else:
        repo.append_event(repo._events[0].model_copy(deep=True))
    with pytest.raises(ReviewConflictError):
        store.lookup("tenant-a", review.decision.subject_id)


def test_journal_cannot_write_to_wrong_subject_type():
    from cepio.model import OntologyObject

    repo = InMemoryRepository()
    store, _, state, *_ = setup_store(repo)
    review = state["review"]
    repo.upsert_object(
        OntologyObject(
            id=store._stream("tenant-a", review.decision.subject_id),
            type="Other",
            name="Wrong subject",
        )
    )
    with pytest.raises(ReviewConflictError, match="subject type"):
        store.record(review, expected_revision=0, attestation_id="test")
    assert not repo._events
