"""Evidence-backed CEPIO capability registry and governed promotion contracts."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from typing import Mapping

import yaml
from pydantic import BaseModel, Field, model_validator

from .sovereignty import (
    IntelligenceSovereigntyContract,
    PermittedUse,
    SovereigntyDenied,
    authorize_source_use,
)


class CapabilityLayer(str, Enum):
    CORE = "CORE"
    COMMON = "COMMON"
    DOMAIN = "DOMAIN"
    PROFILE = "PROFILE"


class CapabilityMaturity(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    PREVIEW = "PREVIEW"
    QUALIFIED = "QUALIFIED"
    PRODUCTION = "PRODUCTION"


class EvidenceScope(str, Enum):
    DOMAIN = "DOMAIN"
    COMMON = "COMMON"
    PROFILE = "PROFILE"


class CapabilityEvidenceRef(BaseModel):
    id: str
    domain: str
    kind: str
    artifact: str
    question_ids: set[str] = Field(default_factory=set)
    scope: EvidenceScope = EvidenceScope.DOMAIN
    customer_specific: bool = False
    sovereignty_source_id: str | None = None


class CapabilityProvenance(BaseModel):
    mode: str
    source_ids: list[str] = Field(default_factory=list)
    decision_id: str | None = None


class CapabilityRecord(BaseModel):
    id: str
    version: str
    title: str
    description: str
    layer: CapabilityLayer
    maturity: CapabilityMaturity
    semantic_terms: set[str] = Field(default_factory=set)
    semantic_relationships: set[str] = Field(default_factory=set)
    personas: set[str] = Field(default_factory=set)
    competencies: set[str] = Field(default_factory=set)
    evidence_requirements: set[str] = Field(default_factory=set)
    reasoning_patterns: set[str] = Field(default_factory=set)
    skills: set[str] = Field(default_factory=set)
    decisions: set[str] = Field(default_factory=set)
    authority_requirements: set[str] = Field(default_factory=set)
    policy_requirements: set[str] = Field(default_factory=set)
    industry_iq_packs: set[str] = Field(default_factory=set)
    runtime_bindings: set[str] = Field(default_factory=set)
    uncertainty_models: set[str] = Field(default_factory=set)
    validated_domains: set[str] = Field(default_factory=set)
    evidence: list[CapabilityEvidenceRef] = Field(default_factory=list)
    profile_validation_count: int = Field(default=0, ge=0)
    provenance: CapabilityProvenance

    @model_validator(mode="after")
    def protect_global_knowledge_boundary(self) -> "CapabilityRecord":
        # Compiled IQ hashes provenance.source_ids in the protected compiler.
        # Force every tagged source into that digest so changing a rights tag
        # cannot silently reuse a bundle compiled for a different source.
        tagged = {
            item.sovereignty_source_id
            for item in self.evidence
            if item.sovereignty_source_id is not None
        }
        if not tagged.issubset(set(self.provenance.source_ids)):
            raise ValueError("tagged evidence must appear in capability provenance source_ids")
        if self.layer != CapabilityLayer.PROFILE:
            violating = [
                item.id
                for item in self.evidence
                if item.customer_specific or item.scope == EvidenceScope.PROFILE
            ]
            if violating:
                raise ValueError(
                    "global capability records cannot embed customer-specific evidence: "
                    + ", ".join(sorted(violating))
                )
            customer_paths = [
                item.artifact for item in self.evidence if "/customers/" in item.artifact
            ]
            if customer_paths:
                raise ValueError(
                    "global capability evidence cannot reference customer profile artifacts"
                )
        return self


class CapabilityRegistry(BaseModel):
    id: str
    version: str
    capabilities: list[CapabilityRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_capabilities(self) -> "CapabilityRegistry":
        ids = [item.id for item in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("capability registry contains duplicate capability IDs")
        return self

    def get(self, capability_id: str) -> CapabilityRecord | None:
        return next((item for item in self.capabilities if item.id == capability_id), None)


class PromotionDecisionValue(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class PromotionCandidate(BaseModel):
    id: str
    proposed: CapabilityRecord
    source_domains: set[str] = Field(min_length=1)
    rationale: str
    source_gap_ids: set[str] = Field(default_factory=set)


class HumanDecision(BaseModel):
    id: str
    subject_id: str
    decision: PromotionDecisionValue
    actor_role: str
    rationale: str

    @model_validator(mode="after")
    def reject_agent_approval(self) -> "HumanDecision":
        lowered = self.actor_role.lower()
        if "agent" in lowered or lowered.startswith("ai") or " ai" in lowered:
            raise ValueError("AI/agent roles cannot grant architecture approval")
        return self


class CapabilityPromotionPolicy(BaseModel):
    id: str
    version: str
    minimum_independent_domains: int = Field(default=2, ge=2)
    allowed_target_layers: set[CapabilityLayer] = Field(
        default_factory=lambda: {CapabilityLayer.CORE, CapabilityLayer.COMMON}
    )
    minimum_regression_survival_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    require_human_approval: bool = True
    forbid_customer_specific_evidence: bool = True


class PromotionEvaluation(BaseModel):
    candidate_id: str
    status: str
    blockers: list[str] = Field(default_factory=list)


class PromotionWorkflowState(str, Enum):
    CANDIDATE = "CANDIDATE"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    CROSS_DOMAIN_TESTED = "CROSS_DOMAIN_TESTED"
    ARCHITECTURE_REVIEW = "ARCHITECTURE_REVIEW"
    APPROVED = "APPROVED"
    PROMOTED = "PROMOTED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class PromotionWorkflowTransition(BaseModel):
    source: PromotionWorkflowState
    target: PromotionWorkflowState
    gate: str


class PromotionWorkflowContract(BaseModel):
    id: str
    version: str
    initial_state: PromotionWorkflowState
    states: list[PromotionWorkflowState]
    transitions: list[PromotionWorkflowTransition]

    @model_validator(mode="after")
    def validate_contract(self) -> "PromotionWorkflowContract":
        states = set(self.states)
        if self.initial_state not in states:
            raise ValueError("promotion workflow initial_state must be declared")
        if any(item.source not in states or item.target not in states for item in self.transitions):
            raise ValueError("promotion workflow transition references undeclared state")
        return self


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_capability_registry(path: Path) -> CapabilityRegistry:
    return CapabilityRegistry.model_validate(_load_yaml(path))


def load_promotion_policy(path: Path) -> CapabilityPromotionPolicy:
    return CapabilityPromotionPolicy.model_validate(_load_yaml(path))


def load_promotion_workflow(path: Path) -> PromotionWorkflowContract:
    return PromotionWorkflowContract.model_validate(_load_yaml(path))


def evaluate_promotion(
    candidate: PromotionCandidate,
    *,
    decision: HumanDecision | None,
    regression_survival_rate: float,
    policy: CapabilityPromotionPolicy,
) -> PromotionEvaluation:
    """Legacy-compatible entry: tagged source evidence is never implicitly approved."""

    return _evaluate_promotion(
        candidate,
        decision=decision,
        regression_survival_rate=regression_survival_rate,
        policy=policy,
        sovereignty_records=None,
    )


def evaluate_promotion_with_rights(
    candidate: PromotionCandidate,
    *,
    decision: HumanDecision | None,
    regression_survival_rate: float,
    policy: CapabilityPromotionPolicy,
    sovereignty_records: Mapping[str, IntelligenceSovereigntyContract],
) -> PromotionEvaluation:
    """Opt-in governed path; all evidence must carry explicit source identity."""

    if not candidate.proposed.evidence or any(
        not item.sovereignty_source_id for item in candidate.proposed.evidence
    ):
        return PromotionEvaluation(
            candidate_id=candidate.id,
            status="BLOCKED",
            blockers=["governed promotion requires source-tagged evidence"],
        )
    if not candidate.proposed.provenance.source_ids:
        return PromotionEvaluation(
            candidate_id=candidate.id,
            status="BLOCKED",
            blockers=["governed promotion requires complete source provenance"],
        )

    return _evaluate_promotion(
        candidate,
        decision=decision,
        regression_survival_rate=regression_survival_rate,
        policy=policy,
        sovereignty_records=sovereignty_records,
    )


def _evaluate_promotion(
    candidate: PromotionCandidate,
    *,
    decision: HumanDecision | None,
    regression_survival_rate: float,
    policy: CapabilityPromotionPolicy,
    sovereignty_records: Mapping[str, IntelligenceSovereigntyContract] | None,
) -> PromotionEvaluation:
    blockers: list[str] = []
    proposed = candidate.proposed
    if proposed.layer not in policy.allowed_target_layers:
        blockers.append(f"target layer {proposed.layer.value} is not promotable by this policy")
    if len(candidate.source_domains) < policy.minimum_independent_domains:
        blockers.append(
            f"independent domains {len(candidate.source_domains)} "
            f"< {policy.minimum_independent_domains}"
        )
    if not candidate.source_domains.issubset(proposed.validated_domains):
        blockers.append("candidate source domains must be present in proposed validated_domains")
    if policy.forbid_customer_specific_evidence and any(
        item.customer_specific or item.scope == EvidenceScope.PROFILE for item in proposed.evidence
    ):
        blockers.append("customer-specific evidence cannot justify global capability promotion")
    # Rights are independent of the candidate. Authorize the complete source
    # set, not just those whose evidence item happens to carry a tag.
    tagged_sources = {
        evidence.sovereignty_source_id
        for evidence in proposed.evidence
        if evidence.sovereignty_source_id is not None
    }
    if tagged_sources:
        all_sources = set(proposed.provenance.source_ids) | tagged_sources
        for source_id in sorted(all_sources):
            try:
                authorize_source_use(
                    source_id,
                    records=sovereignty_records or {},
                    use=PermittedUse.GLOBAL_LEARNING,
                    tenant_id=None,
                    at=datetime.now(timezone.utc),
                )
            except SovereigntyDenied:
                blockers.append("capability provenance lacks verified global learning permission")
                break
    if regression_survival_rate < policy.minimum_regression_survival_rate:
        blockers.append(
            "regression survival rate "
            f"{regression_survival_rate:.3f} "
            f"< {policy.minimum_regression_survival_rate:.3f}"
        )
    if blockers:
        return PromotionEvaluation(candidate_id=candidate.id, status="BLOCKED", blockers=blockers)
    if policy.require_human_approval and decision is None:
        return PromotionEvaluation(candidate_id=candidate.id, status="READY_FOR_HUMAN_REVIEW")
    if decision is not None and decision.subject_id != candidate.id:
        return PromotionEvaluation(
            candidate_id=candidate.id,
            status="BLOCKED",
            blockers=["approval subject does not match promotion candidate"],
        )
    if decision is not None and decision.decision == PromotionDecisionValue.REJECT:
        return PromotionEvaluation(candidate_id=candidate.id, status="REJECTED")
    return PromotionEvaluation(candidate_id=candidate.id, status="APPROVED")


def apply_promotion(
    registry: CapabilityRegistry,
    candidate: PromotionCandidate,
    evaluation: PromotionEvaluation,
) -> CapabilityRegistry:
    if evaluation.status != "APPROVED" or evaluation.candidate_id != candidate.id:
        raise ValueError("promotion candidate must pass policy evaluation before registry mutation")
    capabilities = list(registry.capabilities)
    existing = registry.get(candidate.proposed.id)
    if existing is None:
        capabilities.append(candidate.proposed)
    else:
        index = next(i for i, item in enumerate(capabilities) if item.id == candidate.proposed.id)
        capabilities[index] = candidate.proposed
    return CapabilityRegistry(
        id=registry.id,
        version=registry.version,
        capabilities=sorted(capabilities, key=lambda item: item.id),
    )


def registry_metrics(registry: CapabilityRegistry) -> dict[str, Any]:
    count = len(registry.capabilities)
    reusable = [
        item
        for item in registry.capabilities
        if item.layer in {CapabilityLayer.CORE, CapabilityLayer.COMMON}
    ]
    cross_domain = [item for item in registry.capabilities if len(item.validated_domains) >= 2]
    domain_proofs = sum(len(item.validated_domains) for item in registry.capabilities)
    return {
        "capability_count": count,
        "reusable_capability_count": len(reusable),
        "cross_domain_capability_count": len(cross_domain),
        "average_validated_domains_per_capability": (domain_proofs / count if count else 0.0),
        "qualified_or_better_count": sum(
            item.maturity in {CapabilityMaturity.QUALIFIED, CapabilityMaturity.PRODUCTION}
            for item in registry.capabilities
        ),
        "registry_hash": stable_hash(registry.model_dump(mode="json")),
    }
