"""Host-only consumption of reviewed semantic mappings; no approval writer.

The host authenticates the caller and retrieves review records from its governed
store. Callers cannot supply a review record or promote a proposal through this API.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime

from rdflib import Graph

from .auth import ActorContext
from .capability_registry import HumanDecision, PromotionDecisionValue
from .platform_bindings import EvidenceEnvelope
from .semantic_reconciliation import ReconciliationProposal, propose_reconciliation


def mapping_review_key(
    proposal: ReconciliationProposal, *, method_id: str, method_version: str, use_context: str
) -> str:
    """Pin semantic snapshots and the exact method/application context reviewed."""
    if any(not value.strip() for value in (method_id, method_version, use_context)):
        raise ValueError("Method identity, version and use context are required")
    payload = {
        "proposal": asdict(proposal),
        "method_id": method_id,
        "method_version": method_version,
        "use_context": use_context,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class StoredMappingReview:
    """Trusted host-store projection, never deserialized from agent arguments.

    HumanDecision is an existing CEPIO review contract, not proof of identity.
    The store must independently attest human identity and reviewer authority.
    """

    decision: HumanDecision
    tenant_id: str
    target_iri: str
    expires_at: datetime
    active: bool
    qualifications: frozenset[str]


@dataclass(frozen=True)
class ReviewedMapping:
    review_key: str
    decision_id: str
    target_iri: str
    tenant_id: str
    method_id: str
    method_version: str
    use_context: str


class SemanticMappingGate:
    """Recheck policy and the current review store on every mapping use.

    No cache, mutation, promotion, review creation or generic execution framework.
    Call immediately before applying a mapping; returned values are not reusable
    authorization tokens. Store/policy callbacks are trusted host dependencies.
    """

    def __init__(
        self,
        *,
        principal: Callable[[], ActorContext],
        authorize: Callable[[ActorContext, str], bool],
        lookup: Callable[[str, str], StoredMappingReview | None],
        clock: Callable[[], datetime],
    ) -> None:
        self._principal = principal
        self._authorize = authorize
        self._lookup = lookup
        self._clock = clock

    def resolve(
        self,
        envelope: EvidenceEnvelope,
        graph: Graph,
        *,
        method_id: str,
        method_version: str,
        use_context: str,
    ) -> ReviewedMapping:
        actor = self._principal()
        if not actor.actor_id or not actor.tenant_id:
            raise PermissionError("Authenticated actor and tenant required")
        proposal = propose_reconciliation(envelope, graph, tenant_id=actor.tenant_id)
        if proposal.disposition != "existing-candidate":
            raise PermissionError("Mapping requires a unique existing candidate")
        key = mapping_review_key(
            proposal, method_id=method_id, method_version=method_version, use_context=use_context
        )
        if self._authorize(actor, key) is not True:
            raise PermissionError("Mapping use denied by host policy")
        review = self._lookup(actor.tenant_id, key)
        if review is None:
            raise PermissionError("No current governed review for mapping snapshot")
        now = self._clock()
        if now.tzinfo is None or review.expires_at.tzinfo is None:
            raise PermissionError("Review validity requires timezone-aware timestamps")
        if review.active is not True or now >= review.expires_at:
            raise PermissionError("Mapping review revoked or expired")
        if (
            review.tenant_id != actor.tenant_id
            or review.decision.subject_id != key
            or review.target_iri != proposal.candidates[0]
        ):
            raise PermissionError("Mapping review scope mismatch")
        decision = HumanDecision.model_validate(review.decision.model_dump())
        if decision.decision != PromotionDecisionValue.APPROVE or not decision.id.strip():
            raise PermissionError("Mapping has no approval decision")
        required = {"units", "context", "source-rights", "method-applicability"}
        if not required.issubset(review.qualifications):
            raise PermissionError("Mapping review qualification incomplete")
        return ReviewedMapping(
            key,
            decision.id,
            review.target_iri,
            actor.tenant_id,
            method_id,
            method_version,
            use_context,
        )
