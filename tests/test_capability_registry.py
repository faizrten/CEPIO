from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cepio.capability_registry import (
    CapabilityEvidenceRef,
    CapabilityLayer,
    CapabilityPromotionPolicy,
    CapabilityRecord,
    CapabilityRegistry,
    EvidenceScope,
    HumanDecision,
    PromotionCandidate,
    PromotionEvaluation,
    PromotionWorkflowContract,
    PromotionWorkflowState,
    apply_promotion,
    evaluate_promotion,
    load_capability_registry,
    load_promotion_policy,
    load_promotion_workflow,
    registry_metrics,
    stable_hash,
)


def evidence(**overrides: object) -> CapabilityEvidenceRef:
    value: dict[str, object] = {
        "id": "ev-1",
        "domain": "refinery",
        "kind": "competency",
        "artifact": "generalization/competency/refinery.yaml",
        "scope": "DOMAIN",
        "customer_specific": False,
    }
    value.update(overrides)
    return CapabilityEvidenceRef.model_validate(value)


def record(**overrides: object) -> CapabilityRecord:
    value: dict[str, object] = {
        "id": "industrial.reliability.condition-work",
        "version": "0.1.0",
        "title": "Condition work",
        "description": "test",
        "layer": "COMMON",
        "maturity": "QUALIFIED",
        "semantic_terms": {"urn:Condition", "urn:Work"},
        "semantic_relationships": {"urn:hasWork"},
        "competencies": {"refinery:R1", "drilling:D1"},
        "validated_domains": {"refinery", "drilling"},
        "evidence": [evidence()],
        "provenance": {"mode": "qualified-backfill"},
    }
    value.update(overrides)
    return CapabilityRecord.model_validate(value)


def policy(**overrides: object) -> CapabilityPromotionPolicy:
    value: dict[str, object] = {
        "id": "promotion-policy",
        "version": "0.1",
        "minimum_independent_domains": 2,
        "allowed_target_layers": ["CORE", "COMMON"],
        "minimum_regression_survival_rate": 1.0,
        "require_human_approval": True,
        "forbid_customer_specific_evidence": True,
    }
    value.update(overrides)
    return CapabilityPromotionPolicy.model_validate(value)


def candidate(**overrides: object) -> PromotionCandidate:
    value: dict[str, object] = {
        "id": "promote-condition-work",
        "proposed": record(),
        "source_domains": {"refinery", "drilling"},
        "rationale": "independent domains",
        "source_gap_ids": {"GAP-1"},
    }
    value.update(overrides)
    return PromotionCandidate.model_validate(value)


def decision(
    value: str = "APPROVE",
    subject: str = "promote-condition-work",
    role: str = "industry-architect",
) -> HumanDecision:
    return HumanDecision.model_validate(
        {
            "id": "decision-1",
            "subject_id": subject,
            "decision": value,
            "actor_role": role,
            "rationale": "reviewed",
        }
    )


def test_registry_load_get_hash_and_metrics(tmp_path: Path):
    payload = {
        "id": "registry",
        "version": "0.1",
        "capabilities": [record().model_dump(mode="json")],
    }
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    registry = load_capability_registry(path)
    assert registry.get("industrial.reliability.condition-work") is not None
    assert registry.get("missing") is None
    metrics = registry_metrics(registry)
    assert metrics["capability_count"] == 1
    assert metrics["reusable_capability_count"] == 1
    assert metrics["cross_domain_capability_count"] == 1
    assert metrics["average_validated_domains_per_capability"] == 2.0
    assert metrics["qualified_or_better_count"] == 1
    assert metrics["registry_hash"] == stable_hash(
        registry.model_dump(mode="json")
    )
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_empty_registry_metrics():
    metrics = registry_metrics(CapabilityRegistry(id="empty", version="0.1"))
    assert metrics["capability_count"] == 0
    assert metrics["average_validated_domains_per_capability"] == 0.0


def test_registry_rejects_duplicate_capabilities():
    with pytest.raises(ValidationError, match="duplicate capability IDs"):
        CapabilityRegistry(
            id="bad", version="0.1", capabilities=[record(), record()]
        )


@pytest.mark.parametrize(
    "bad_evidence",
    [evidence(customer_specific=True), evidence(scope=EvidenceScope.PROFILE)],
)
def test_global_record_rejects_customer_specific_evidence(
    bad_evidence: CapabilityEvidenceRef,
):
    with pytest.raises(
        ValidationError, match="cannot embed customer-specific evidence"
    ):
        record(evidence=[bad_evidence])


def test_global_record_rejects_customer_profile_path():
    with pytest.raises(
        ValidationError, match="cannot reference customer profile artifacts"
    ):
        record(
            evidence=[
                evidence(artifact="generalization/customers/acme/profile.yaml")
            ]
        )


def test_profile_record_can_reference_customer_evidence():
    item = record(
        layer=CapabilityLayer.PROFILE,
        evidence=[
            evidence(
                artifact="generalization/customers/acme/profile.yaml",
                scope=EvidenceScope.PROFILE,
                customer_specific=True,
            )
        ],
    )
    assert item.layer == CapabilityLayer.PROFILE


def test_human_decision_rejects_agent_roles():
    with pytest.raises(
        ValidationError, match="cannot grant architecture approval"
    ):
        decision(role="ai_agent")
    assert decision().decision.value == "APPROVE"


def test_policy_and_workflow_loaders(tmp_path: Path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(policy().model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    assert load_promotion_policy(policy_path).minimum_independent_domains == 2

    workflow_payload = {
        "id": "workflow.capability-promotion.v1",
        "version": "0.1",
        "initial_state": "CANDIDATE",
        "states": ["CANDIDATE", "EVIDENCE_COLLECTED", "BLOCKED"],
        "transitions": [
            {
                "source": "CANDIDATE",
                "target": "EVIDENCE_COLLECTED",
                "gate": "evidence",
            }
        ],
    }
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        yaml.safe_dump(workflow_payload), encoding="utf-8"
    )
    loaded = load_promotion_workflow(workflow_path)
    assert loaded.initial_state == PromotionWorkflowState.CANDIDATE


def test_yaml_loader_rejects_non_mapping(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_capability_registry(path)


def test_promotion_workflow_rejects_bad_initial_and_transition():
    with pytest.raises(ValidationError, match="initial_state must be declared"):
        PromotionWorkflowContract.model_validate(
            {
                "id": "bad",
                "version": "0.1",
                "initial_state": "CANDIDATE",
                "states": ["BLOCKED"],
                "transitions": [],
            }
        )
    with pytest.raises(
        ValidationError, match="transition references undeclared state"
    ):
        PromotionWorkflowContract.model_validate(
            {
                "id": "bad",
                "version": "0.1",
                "initial_state": "CANDIDATE",
                "states": ["CANDIDATE", "BLOCKED"],
                "transitions": [
                    {
                        "source": "CANDIDATE",
                        "target": "PROMOTED",
                        "gate": "bad",
                    }
                ],
            }
        )


def test_promotion_ready_approved_and_rejected():
    item = candidate()
    ready = evaluate_promotion(
        item, decision=None, regression_survival_rate=1.0, policy=policy()
    )
    assert ready.status == "READY_FOR_HUMAN_REVIEW"
    approved = evaluate_promotion(
        item,
        decision=decision(),
        regression_survival_rate=1.0,
        policy=policy(),
    )
    assert approved.status == "APPROVED"
    rejected = evaluate_promotion(
        item,
        decision=decision("REJECT"),
        regression_survival_rate=1.0,
        policy=policy(),
    )
    assert rejected.status == "REJECTED"


def test_promotion_policy_blockers_are_accumulated():
    proposed = record(layer="DOMAIN", validated_domains={"refinery"})
    item = candidate(proposed=proposed, source_domains={"refinery"})
    result = evaluate_promotion(
        item, decision=None, regression_survival_rate=0.5, policy=policy()
    )
    assert result.status == "BLOCKED"
    assert any("target layer DOMAIN" in blocker for blocker in result.blockers)
    assert any("independent domains 1" in blocker for blocker in result.blockers)
    assert any(
        "regression survival rate" in blocker for blocker in result.blockers
    )


def test_promotion_rejects_source_domain_mismatch():
    item = candidate(proposed=record(validated_domains={"refinery"}))
    result = evaluate_promotion(
        item,
        decision=decision(),
        regression_survival_rate=1.0,
        policy=policy(),
    )
    assert result.status == "BLOCKED"
    assert "candidate source domains must be present" in result.blockers[0]


def test_promotion_rejects_customer_specific_evidence_when_policy_requests_it():
    proposed = record(
        layer="PROFILE",
        evidence=[
            evidence(scope="PROFILE", customer_specific=True),
        ],
    )
    item = candidate(proposed=proposed)
    result = evaluate_promotion(
        item,
        decision=None,
        regression_survival_rate=1.0,
        policy=policy(
            allowed_target_layers=["PROFILE"],
            forbid_customer_specific_evidence=True,
        ),
    )
    assert result.status == "BLOCKED"
    assert any(
        "customer-specific evidence" in blocker for blocker in result.blockers
    )


def test_promotion_rejects_wrong_decision_subject():
    result = evaluate_promotion(
        candidate(),
        decision=decision(subject="other"),
        regression_survival_rate=1.0,
        policy=policy(),
    )
    assert result.status == "BLOCKED"
    assert result.blockers == [
        "approval subject does not match promotion candidate"
    ]


def test_policy_can_disable_human_approval():
    result = evaluate_promotion(
        candidate(),
        decision=None,
        regression_survival_rate=1.0,
        policy=policy(require_human_approval=False),
    )
    assert result.status == "APPROVED"


def test_apply_promotion_add_replace_and_refuse():
    empty = CapabilityRegistry(id="registry", version="0.1")
    item = candidate()
    approved = PromotionEvaluation(candidate_id=item.id, status="APPROVED")
    added = apply_promotion(empty, item, approved)
    added_record = added.get(item.proposed.id)
    assert added_record is not None
    assert added_record.version == "0.1.0"

    replacement = item.model_copy(
        update={
            "proposed": item.proposed.model_copy(update={"version": "0.2.0"})
        }
    )
    replaced = apply_promotion(
        added,
        replacement,
        PromotionEvaluation(candidate_id=replacement.id, status="APPROVED"),
    )
    replaced_record = replaced.get(item.proposed.id)
    assert replaced_record is not None
    assert replaced_record.version == "0.2.0"

    with pytest.raises(
        ValueError, match="must pass policy evaluation"
    ):
        apply_promotion(
            empty,
            item,
            PromotionEvaluation(
                candidate_id=item.id, status="BLOCKED", blockers=["no"]
            ),
        )
    with pytest.raises(
        ValueError, match="must pass policy evaluation"
    ):
        apply_promotion(
            empty,
            item,
            PromotionEvaluation(candidate_id="other", status="APPROVED"),
        )
