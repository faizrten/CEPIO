"""Adversarial contract tests for the first sovereignty enforcement slice.

Synthetic identifiers only: no customer data, industrial heuristics or hidden Labs cases.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.capability_registry import (
    CapabilityEvidenceRef,
    CapabilityPromotionPolicy,
    CapabilityRecord,
    CapabilityRegistry,
    HumanDecision,
    PromotionCandidate,
    evaluate_promotion,
    evaluate_promotion_with_rights,
)
from cepio.memory import MemoryKind, MemoryRecord, MemoryScope
from cepio.retrieval import (
    BackendHit,
    CapabilityRouter,
    RetrievalEngine,
    RetrievalIntent,
    RetrievalPlanner,
    RetrievalStatus,
    RetrievalStrategy,
)
from cepio.sovereignty import (
    IntelligenceSovereigntyContract,
    PermittedUse,
    SovereigntyDenied,
    SourceClass,
    authorize_source_use,
)


AT = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
CAPABILITY = "industrial.test.source-neutral"


def grant(
    source_id="public-proof",
    *,
    source_class=SourceClass.CEPIO,
    tenant_id=None,
    uses=None,
    parents=None,
    reviewer="human-review-001",
    expires_at=None,
    revoked_at=None,
):
    return IntelligenceSovereigntyContract(
        source_id=source_id,
        owner_id="synthetic-owner",
        source_class=source_class,
        tenant_id=tenant_id,
        rights_basis_ref="synthetic-rights-review",
        permitted_uses=uses
        if uses is not None
        else {
            PermittedUse.GLOBAL_LEARNING,
            PermittedUse.SHARED_RETRIEVAL,
        },
        parent_source_ids=parents or set(),
        reviewer_ref=reviewer,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def capability(source_id="public-proof"):
    return CapabilityRecord(
        id=CAPABILITY,
        version="0.1",
        title="Source-neutral test contract",
        description="Synthetic qualification fixture",
        layer="COMMON",
        maturity="QUALIFIED",
        validated_domains={"refinery", "drilling"},
        evidence=[
            CapabilityEvidenceRef(
                id="qualified-example",
                domain="refinery",
                kind="competency",
                artifact="generalization/competency/example.yaml",
                sovereignty_source_id=source_id,
            )
        ],
        provenance={"mode": "synthetic-test", "source_ids": [source_id]},
    )


def test_version_scope_time_and_derivative_contract_validation():
    with pytest.raises(ValidationError, match="unsupported sovereignty contract version"):
        IntelligenceSovereigntyContract.model_validate({**grant().model_dump(), "version": "1"})
    with pytest.raises(ValidationError, match="requires tenant_id"):
        grant(source_class=SourceClass.CUSTOMER)
    with pytest.raises(ValidationError, match="requires parent lineage"):
        grant(source_class=SourceClass.CUSTOMER_DERIVED, tenant_id="alpha")
    with pytest.raises(ValidationError, match="timezone-aware"):
        grant(expires_at=datetime(2027, 1, 1))


@pytest.mark.parametrize(
    "records,use",
    [
        ({}, PermittedUse.GLOBAL_LEARNING),
        (
            {"public-proof": grant(uses={PermittedUse.SHARED_RETRIEVAL})},
            PermittedUse.GLOBAL_LEARNING,
        ),
        ({"public-proof": grant(expires_at=AT)}, PermittedUse.GLOBAL_LEARNING),
        ({"public-proof": grant(revoked_at=AT)}, PermittedUse.GLOBAL_LEARNING),
        ({"public-proof": grant(reviewer=None)}, PermittedUse.GLOBAL_LEARNING),
    ],
)
def test_missing_unapproved_expired_revoked_source_rights_fail_closed(records, use):
    with pytest.raises(SovereigntyDenied):
        authorize_source_use("public-proof", records=records, use=use, tenant_id=None, at=AT)


def test_unknown_lineage_cycle_and_restriction_propagation():
    child = grant("child", parents={"parent"})
    with pytest.raises(SovereigntyDenied, match="missing source"):
        authorize_source_use(
            "child",
            records={"child": child},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )
    parent = grant("parent", parents={"child"})
    with pytest.raises(SovereigntyDenied, match="cyclic"):
        authorize_source_use(
            "child",
            records={"child": child, "parent": parent},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )
    restricted = grant("parent", uses={PermittedUse.TENANT_INFERENCE})
    with pytest.raises(SovereigntyDenied, match="not permitted"):
        authorize_source_use(
            "child",
            records={"child": child, "parent": restricted},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )


def test_customer_synthetic_derivative_cannot_launder_source_rights():
    customer = grant(
        "customer-source",
        source_class=SourceClass.CUSTOMER,
        tenant_id="alpha",
        uses={PermittedUse.TENANT_INFERENCE, PermittedUse.GLOBAL_LEARNING},
    )
    analogue = grant(
        "renamed-synthetic",
        source_class=SourceClass.CUSTOMER_DERIVED,
        tenant_id="alpha",
        parents={"customer-source"},
        uses={PermittedUse.TENANT_INFERENCE, PermittedUse.GLOBAL_LEARNING},
    )
    records = {customer.source_id: customer, analogue.source_id: analogue}
    authorize_source_use(
        "renamed-synthetic",
        records=records,
        use=PermittedUse.TENANT_INFERENCE,
        tenant_id="alpha",
        at=AT,
    )
    for tenant in ("beta", None):
        with pytest.raises(SovereigntyDenied):
            authorize_source_use(
                "renamed-synthetic",
                records=records,
                use=PermittedUse.TENANT_INFERENCE,
                tenant_id=tenant,
                at=AT,
            )
    with pytest.raises(SovereigntyDenied):
        authorize_source_use(
            "renamed-synthetic",
            records=records,
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )


def test_promotion_keeps_existing_human_and_regression_gates():
    item = PromotionCandidate(
        id="promotion-1",
        proposed=capability(),
        source_domains={"refinery", "drilling"},
        rationale="independent synthetic coverage",
    )
    policy = CapabilityPromotionPolicy(id="policy", version="0.1")
    human = HumanDecision(
        id="review",
        subject_id=item.id,
        decision="APPROVE",
        actor_role="human-industry-architect",
        rationale="reviewed",
    )
    missing = evaluate_promotion(item, decision=human, regression_survival_rate=1, policy=policy)
    assert missing.status == "BLOCKED"
    assert any("global learning permission" in reason for reason in missing.blockers)

    rights = {"public-proof": grant()}
    pending = evaluate_promotion_with_rights(
        item,
        decision=None,
        regression_survival_rate=1,
        policy=policy,
        sovereignty_records=rights,
    )
    assert pending.status == "READY_FOR_HUMAN_REVIEW"
    failed = evaluate_promotion_with_rights(
        item,
        decision=human,
        regression_survival_rate=0.99,
        policy=policy,
        sovereignty_records=rights,
    )
    assert failed.status == "BLOCKED"
    approved = evaluate_promotion_with_rights(
        item,
        decision=human,
        regression_survival_rate=1,
        policy=policy,
        sovereignty_records=rights,
    )
    assert approved.status == "APPROVED"
    with pytest.raises(ValidationError, match="cannot grant architecture approval"):
        HumanDecision(
            id="forged",
            subject_id=item.id,
            decision="APPROVE",
            actor_role="ai_agent",
            rationale="not human",
        )

    derived = item.model_copy(update={"proposed": capability("customer-derived")})
    customer_rights = {
        "customer-derived": grant(
            "customer-derived",
            source_class=SourceClass.CUSTOMER_DERIVED,
            tenant_id="alpha",
            parents={"parent-customer"},
        ),
        "parent-customer": grant(
            "parent-customer",
            source_class=SourceClass.CUSTOMER,
            tenant_id="alpha",
        ),
    }
    blocked = evaluate_promotion_with_rights(
        derived,
        decision=human,
        regression_survival_rate=1,
        policy=policy,
        sovereignty_records=customer_rights,
    )
    assert blocked.status == "BLOCKED"


class OneHitBackend:
    strategy = RetrievalStrategy.STRUCTURED

    def __init__(self, record):
        self.record = record

    def search(self, step):
        return [BackendHit(record=self.record, rank=1, score=1.0, strategy=self.strategy)]


def test_retrieval_checks_source_rights_after_backend_returns_hit():
    record = MemoryRecord(
        id="sensitive-1",
        kind=MemoryKind.SEMANTIC,
        scope=MemoryScope.TENANT,
        tenant_id="alpha",
        summary="synthetic tenant-only memory",
        provenance={"source_kind": "synthetic", "source_ids": ["customer-source"]},
        sovereignty_source_id="customer-source",
        created_at=AT - timedelta(days=1),
    )
    registry = CapabilityRegistry(id="registry", version="0.1")

    def run(tenant, rights):
        engine = RetrievalEngine(
            CapabilityRouter(registry),
            RetrievalPlanner(),
            [OneHitBackend(record)],
        )
        engine.configure_source_rights(rights)
        return engine.retrieve(
            RetrievalIntent(
                tenant_id=tenant,
                kinds={MemoryKind.SEMANTIC},
                at=AT,
            )
        )

    allowed_right = grant(
        "customer-source",
        source_class=SourceClass.CUSTOMER,
        tenant_id="alpha",
        uses={PermittedUse.TENANT_INFERENCE},
    )
    allowed = run("alpha", {"customer-source": allowed_right})
    assert allowed.status == RetrievalStatus.READY
    assert [hit.record.id for hit in allowed.candidates] == ["sensitive-1"]
    assert run("beta", {"customer-source": allowed_right}).candidates == []
    denied = run("alpha", {})
    assert denied.candidates == []
    assert denied.metrics.dropped_boundary_hits == 1
    # Query-time (historical) must never replace the current authorization clock.
    once_allowed = grant(
        "customer-source",
        source_class=SourceClass.CUSTOMER,
        tenant_id="alpha",
        uses={PermittedUse.TENANT_INFERENCE},
        expires_at=AT + timedelta(hours=1),
    )
    assert run("alpha", {"customer-source": once_allowed}).candidates == []
    global_copy = record.model_copy(
        update={"scope": MemoryScope.GLOBAL, "tenant_id": None},
    )
    engine = RetrievalEngine(
        CapabilityRouter(registry),
        RetrievalPlanner(),
        [OneHitBackend(global_copy)],
    )
    engine.configure_source_rights({"customer-source": allowed_right})
    assert engine.retrieve(RetrievalIntent(kinds={MemoryKind.SEMANTIC}, at=AT)).candidates == []


def test_strict_mode_rejects_missing_source_tag_and_secondary_provenance():
    record = MemoryRecord(
        id="tenant-sample",
        kind=MemoryKind.SEMANTIC,
        scope=MemoryScope.TENANT,
        tenant_id="alpha",
        summary="synthetic record",
        provenance={
            "source_kind": "synthetic",
            "source_ids": ["tenant-source", "restricted-source"],
        },
    )
    registry = CapabilityRegistry(id="test", version="0.1")
    engine = RetrievalEngine(
        CapabilityRouter(registry), RetrievalPlanner(), [OneHitBackend(record)]
    )
    engine.configure_source_rights(
        {
            "tenant-source": grant(
                "tenant-source",
                source_class=SourceClass.CUSTOMER,
                tenant_id="alpha",
                uses={PermittedUse.TENANT_INFERENCE},
            )
        },
        require_source_tags=True,
    )
    intent = RetrievalIntent(tenant_id="alpha", kinds={MemoryKind.SEMANTIC}, at=AT)
    assert engine.retrieve(intent).candidates == []
    tagged = record.model_copy(update={"sovereignty_source_id": "tenant-source"})
    engine.backends[RetrievalStrategy.STRUCTURED] = OneHitBackend(tagged)
    assert engine.retrieve(intent).candidates == []


def test_promotion_rejects_ungranted_additional_provenance_source():
    proposed = capability()
    modified = proposed.model_copy(
        update={
            "provenance": proposed.provenance.model_copy(
                update={"source_ids": ["public-proof", "unknown-origin"]}
            )
        }
    )
    candidate = PromotionCandidate(
        id="promotion-1",
        proposed=modified,
        source_domains={"refinery", "drilling"},
        rationale="synthetic regression",
    )
    result = evaluate_promotion_with_rights(
        candidate,
        decision=HumanDecision(
            id="human",
            subject_id="promotion-1",
            decision="APPROVE",
            actor_role="industry-architect",
            rationale="reviewed",
        ),
        regression_survival_rate=1.0,
        policy=CapabilityPromotionPolicy(id="policy", version="0.1"),
        sovereignty_records={"public-proof": grant()},
    )
    assert result.status == "BLOCKED"
    assert any("provenance" in reason for reason in result.blockers)


def test_unverified_mutated_rights_contract_is_rejected():
    modified = grant().model_copy(update={"source_class": "INVALID"})
    with pytest.raises(SovereigntyDenied, match="invalid source rights"):
        authorize_source_use(
            "public-proof",
            records={"public-proof": modified},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )


def test_governed_promotion_rejects_untagged_and_empty_evidence():
    policy = CapabilityPromotionPolicy(id="policy", version="0.1")
    tagged = capability()
    untagged_evidence = tagged.evidence[0].model_copy(update={"sovereignty_source_id": None})
    for evidence in ([untagged_evidence], []):
        proposed = tagged.model_copy(update={"evidence": evidence})
        candidate = PromotionCandidate(
            id="promotion-1",
            proposed=proposed,
            source_domains={"refinery", "drilling"},
            rationale="synthetic negative test",
        )
        result = evaluate_promotion_with_rights(
            candidate,
            decision=None,
            regression_survival_rate=1.0,
            policy=policy,
            sovereignty_records={"public-proof": grant()},
        )
        assert result.status == "BLOCKED"
        assert "source-tagged evidence" in result.blockers[0]


def test_governed_promotion_rejects_missing_provenance():
    candidate = PromotionCandidate(
        id="promotion-1",
        proposed=capability(),
        source_domains={"refinery", "drilling"},
        rationale="synthetic negative test",
    )
    # Exercise defensive evaluation if provenance is mutated after admission.
    candidate.proposed.provenance.source_ids.clear()
    result = evaluate_promotion_with_rights(
        candidate,
        decision=None,
        regression_survival_rate=1.0,
        policy=CapabilityPromotionPolicy(id="policy", version="0.1"),
        sovereignty_records={"public-proof": grant()},
    )
    assert result.status == "BLOCKED"
    assert "complete source provenance" in result.blockers[0]


def test_capability_registry_rejects_tagged_source_missing_from_provenance():
    invalid = capability().model_dump(mode="python")
    invalid["provenance"]["source_ids"] = []
    with pytest.raises(ValidationError, match="tagged evidence must appear"):
        CapabilityRecord.model_validate(invalid)


def test_memory_rejects_blank_sovereignty_source_identity():
    with pytest.raises(ValidationError, match="sovereignty_source_id must be nonblank"):
        MemoryRecord(
            id="blank-source",
            kind=MemoryKind.SEMANTIC,
            scope=MemoryScope.TENANT,
            tenant_id="alpha",
            summary="synthetic fixture",
            provenance={"source_kind": "synthetic"},
            sovereignty_source_id=" ",
        )


def test_strict_retrieval_rejects_source_tag_without_provenance():
    record = MemoryRecord(
        id="unknown-lineage",
        kind=MemoryKind.SEMANTIC,
        scope=MemoryScope.TENANT,
        tenant_id="alpha",
        summary="synthetic test memory",
        provenance={"source_kind": "synthetic", "source_ids": []},
        sovereignty_source_id="tenant-source",
    )
    engine = RetrievalEngine(
        CapabilityRouter(CapabilityRegistry(id="test", version="0.1")),
        RetrievalPlanner(),
        [OneHitBackend(record)],
    )
    engine.configure_source_rights(
        {
            "tenant-source": grant(
                "tenant-source",
                source_class=SourceClass.CUSTOMER,
                tenant_id="alpha",
                uses={PermittedUse.TENANT_INFERENCE},
            )
        },
        require_source_tags=True,
    )
    result = engine.retrieve(RetrievalIntent(tenant_id="alpha", kinds={MemoryKind.SEMANTIC}, at=AT))
    assert result.candidates == []
    assert result.metrics.dropped_boundary_hits == 1


def test_source_authorization_rejects_self_parent_invalid_clock_and_alias():
    with pytest.raises(ValidationError, match="source cannot derive from itself"):
        grant("loop", parents={"loop"})
    with pytest.raises(SovereigntyDenied, match="invalid authorization time"):
        authorize_source_use(
            "public-proof",
            records={"public-proof": grant()},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=datetime(2026, 10, 26),
        )
    with pytest.raises(SovereigntyDenied, match="mismatched source permission"):
        authorize_source_use(
            "renamed",
            records={"renamed": grant("public-proof")},
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )


def test_source_authorization_bounds_deep_ancestry_without_release():
    chain = {
        f"parent-{i}": grant(
            f"parent-{i}",
            parents={f"parent-{i + 1}"} if i < 129 else set(),
        )
        for i in range(130)
    }
    with pytest.raises(SovereigntyDenied, match="lineage depth exceeded"):
        authorize_source_use(
            "parent-0",
            records=chain,
            use=PermittedUse.GLOBAL_LEARNING,
            tenant_id=None,
            at=AT,
        )
