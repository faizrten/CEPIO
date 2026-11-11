from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from cepio.auth import ActorContext
from cepio.capability_registry import HumanDecision
from cepio.domain_bindings import ExternalRecordReference
from cepio.platform_bindings import EvidenceEnvelope
from cepio.semantic_mapping_gate import (
    SemanticMappingGate,
    StoredMappingReview,
    mapping_review_key,
)
from cepio.semantic_reconciliation import propose_reconciliation


NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)
TARGET = "urn:test#Equipment"


def setup_gate():
    graph = Graph()
    graph.add((URIRef(TARGET), RDF.type, OWL.Class))
    envelope = EvidenceEnvelope(
        reference=ExternalRecordReference(
            source_system="test-catalog",
            record_kind="semantic-term",
            record_id="t1",
            partition="tenant-a",
        ),
        evidence={
            "term": {"id": "t1", "name": "Equipment"},
            "cepio_status": "proposal-only",
            "evidence_kind": "semantic-metadata",
        },
    )
    params = dict(method_id="test-method", method_version="1", use_context="test-only")
    key = mapping_review_key(
        propose_reconciliation(envelope, graph, tenant_id="tenant-a"), **params
    )
    # Isolated store fixture; no real human approval or production authority.
    record = StoredMappingReview(
        decision=HumanDecision(
            id="fixture-review",
            subject_id=key,
            decision="APPROVE",
            actor_role="test-reviewer",
            rationale="synthetic unit test",
        ),
        tenant_id="tenant-a",
        target_iri=TARGET,
        expires_at=NOW + timedelta(hours=1),
        active=True,
        qualifications=frozenset({"units", "context", "source-rights", "method-applicability"}),
    )
    state = {
        "actor": ActorContext("reader", set(), "tenant-a"),
        "allowed": True,
        "review": record,
        "now": NOW,
        "lookups": 0,
    }

    def lookup(tenant, requested):
        state["lookups"] += 1
        return state["review"] if requested == key else None

    gate = SemanticMappingGate(
        principal=lambda: state["actor"],
        authorize=lambda actor, requested: state["allowed"],
        lookup=lookup,
        clock=lambda: state["now"],
    )
    return gate, state, envelope, graph, params


def test_reviewed_mapping_then_revocation_without_cache():
    gate, state, envelope, graph, params = setup_gate()
    result = gate.resolve(envelope, graph, **params)
    assert result.target_iri == TARGET
    assert result.method_version == "1"
    assert envelope.evidence["cepio_status"] == "proposal-only"
    state["review"] = replace(state["review"], active=False)
    with pytest.raises(PermissionError, match="revoked"):
        gate.resolve(envelope, graph, **params)
    assert state["lookups"] == 2


@pytest.mark.parametrize(
    "change", ["ontology", "term", "method", "version", "context", "source", "dataset"]
)
def test_snapshot_or_scope_change_requires_new_review(change):
    gate, state, envelope, graph, params = setup_gate()
    if change == "ontology":
        graph.add((URIRef(TARGET), RDFS.comment, Literal("changed meaning")))
    elif change == "term":
        envelope.evidence["term"]["description"] = "changed definition"
    elif change == "dataset":
        envelope.reference = envelope.reference.model_copy(update={"dataset_id": "other-dataset"})
    elif change == "source":
        envelope.reference = envelope.reference.model_copy(update={"source_system": "other"})
    else:
        params[
            {"method": "method_id", "version": "method_version", "context": "use_context"}[change]
        ] = "changed"
    with pytest.raises(PermissionError, match="No current"):
        gate.resolve(envelope, graph, **params)


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "expired",
        "naive-expiry",
        "naive-clock",
        "tenant",
        "subject",
        "target",
        "rejected",
        "blank-id",
        "qualification",
    ],
)
def test_invalid_review_cannot_authorize(change):
    gate, state, envelope, graph, params = setup_gate()
    r = state["review"]
    if change == "missing":
        state["review"] = None
    elif change == "naive-clock":
        state["now"] = NOW.replace(tzinfo=None)
    elif change in ("rejected", "subject", "blank-id"):
        field, value = {
            "rejected": ("decision", "REJECT"),
            "subject": ("subject_id", "wrong"),
            "blank-id": ("id", ""),
        }[change]
        state["review"] = replace(
            r, decision=HumanDecision.model_validate({**r.decision.model_dump(), field: value})
        )
    else:
        changes = {
            "expired": {"expires_at": NOW},
            "naive-expiry": {"expires_at": NOW.replace(tzinfo=None)},
            "tenant": {"tenant_id": "other"},
            "target": {"target_iri": "urn:other"},
            "qualification": {"qualifications": frozenset({"units"})},
        }
        state["review"] = replace(r, **changes[change])
    with pytest.raises(PermissionError):
        gate.resolve(envelope, graph, **params)


@pytest.mark.parametrize(
    "actor",
    [
        ActorContext("", set(), "tenant-a"),
        ActorContext("a", set(), None),
        ActorContext("a", set(), "other"),
    ],
)
def test_wrong_or_missing_identity_never_reads_review(actor):
    gate, state, envelope, graph, params = setup_gate()
    state["actor"] = actor
    with pytest.raises(PermissionError):
        gate.resolve(envelope, graph, **params)
    assert state["lookups"] == 0


def test_policy_rechecked_before_review_lookup():
    gate, state, envelope, graph, params = setup_gate()
    gate.resolve(envelope, graph, **params)
    state["allowed"] = False
    with pytest.raises(PermissionError, match="host policy"):
        gate.resolve(envelope, graph, **params)
    assert state["lookups"] == 1


def test_ambiguous_and_unmatched_do_not_reach_review_store():
    gate, state, envelope, graph, params = setup_gate()
    graph.add((URIRef("urn:other#Equipment"), RDF.type, OWL.Class))
    with pytest.raises(PermissionError, match="unique"):
        gate.resolve(envelope, graph, **params)
    envelope.evidence["term"]["name"] = "unknown"
    with pytest.raises(PermissionError, match="unique"):
        gate.resolve(envelope, graph, **params)
    assert state["lookups"] == 0


@pytest.mark.parametrize("field", ["method_id", "method_version", "use_context"])
def test_empty_scope_rejected(field):
    gate, state, envelope, graph, params = setup_gate()
    params[field] = " "
    with pytest.raises(ValueError):
        gate.resolve(envelope, graph, **params)
