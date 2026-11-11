"""Host-only review journal using CEPIO's existing append-only event repository.

Use a dedicated host-controlled repository. Never bind this to agent-writable
events. The attestation callback must verify the actual reviewer and exact record
against authenticated host evidence; role strings are not identity proof.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from threading import RLock
from typing import Protocol

from .auth import ActorContext
from .capability_registry import HumanDecision
from .model import ObjectRef, OntologyObject, OperationalEvent
from .repositories import EventRepository, ObjectRepository
from .semantic_mapping_gate import StoredMappingReview


class ReviewConflictError(RuntimeError):
    """Stale or conflicting journal revision; no review may be consumed."""


class ReviewRepository(EventRepository, ObjectRepository, Protocol):
    """Existing CEPIO persistence interfaces required by a review journal."""


class EventMappingReviewStore:
    def __init__(
        self,
        repository: ReviewRepository,
        *,
        principal: Callable[[], ActorContext],
        authorize: Callable[[ActorContext, str, str], bool],
        attest: Callable[[ActorContext, StoredMappingReview, str], bool],
        clock: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._principal = principal
        self._authorize = authorize
        self._attest = attest
        self._clock = clock
        self._lock = RLock()

    @staticmethod
    def _stream(tenant: str, key: str) -> str:
        return "mapping-review:" + hashlib.sha256(json.dumps([tenant, key]).encode()).hexdigest()

    def _actor(self, tenant: str, key: str, operation: str) -> ActorContext:
        actor = self._principal()
        if not actor.actor_id or not tenant or actor.tenant_id != tenant:
            raise PermissionError("Review journal tenant/actor mismatch")
        if self._authorize(actor, operation, key) is not True:
            raise PermissionError("Review journal operation denied")
        return actor

    def history(self, tenant: str, key: str) -> tuple[OperationalEvent, ...]:
        self._actor(tenant, key, "read")
        events = self._repository.events_for(self._stream(tenant, key))
        for event in events:
            p = event.properties
            if (
                event.type != "SemanticMappingReviewRecorded"
                or p.get("tenant_id") != tenant
                or p.get("review_key") != key
                or type(p.get("revision")) is not int
            ):
                raise ReviewConflictError("Invalid review journal record")
        events.sort(key=lambda e: e.properties["revision"])
        if [e.properties["revision"] for e in events] != list(range(1, len(events) + 1)):
            raise ReviewConflictError("Review journal contains gaps or concurrent revisions")
        return tuple(event.model_copy(deep=True) for event in events)

    def lookup(self, tenant: str, key: str) -> StoredMappingReview | None:
        events = self.history(tenant, key)
        if not events:
            return None
        p = events[-1].properties
        return StoredMappingReview(
            decision=HumanDecision.model_validate(p["decision"]),
            tenant_id=tenant,
            target_iri=p["target_iri"],
            expires_at=datetime.fromisoformat(p["expires_at"]),
            active=p["active"],
            qualifications=frozenset(p["qualifications"]),
        )

    def record(
        self, review: StoredMappingReview, *, expected_revision: int, attestation_id: str
    ) -> int:
        """Append a separately attested decision, including revocation/restoration.

        Does not manufacture approval. Restoration requires a new decision and
        attestation. One host instance serializes writers; multiple host instances
        need host transaction coordination. Concurrent revision forks fail closed.
        """
        key = review.decision.subject_id
        actor = self._actor(review.tenant_id, key, "record")
        now = self._clock()
        decision = HumanDecision.model_validate(review.decision.model_dump())
        if (
            not key.strip()
            or not decision.id.strip()
            or not attestation_id.strip()
            or now.tzinfo is None
            or review.expires_at.tzinfo is None
            or type(review.active) is not bool
            or type(expected_revision) is not int
            or expected_revision < 0
        ):
            raise ValueError("Invalid review record or revision")
        if review.active and review.expires_at <= now:
            raise ValueError("Cannot activate an expired review")
        if self._attest(actor, review, attestation_id) is not True:
            raise PermissionError("Reviewer attestation was not verified")
        with self._lock:
            history = self.history(review.tenant_id, key)
            if len(history) != expected_revision:
                raise ReviewConflictError("Review revision changed")
            if any(e.properties["decision"]["id"] == decision.id for e in history):
                raise ReviewConflictError("A new decision ID is required for each revision")
            revision = expected_revision + 1
            stream = self._stream(review.tenant_id, key)
            subject = self._repository.get_object(stream)
            if subject is None:
                self._repository.upsert_object(
                    OntologyObject(
                        id=stream, type="SemanticMappingReview", name="Host review journal"
                    ),
                    expected_version=0,
                )
            elif subject.type != "SemanticMappingReview":
                raise ReviewConflictError("Review journal subject type mismatch")
            self._repository.append_event(
                OperationalEvent(
                    type="SemanticMappingReviewRecorded",
                    subject=ObjectRef(
                        id=self._stream(review.tenant_id, key), type="SemanticMappingReview"
                    ),
                    occurred_at=now,
                    source_system="cepio-host-review",
                    properties={
                        "tenant_id": review.tenant_id,
                        "review_key": key,
                        "revision": revision,
                        "decision": decision.model_dump(mode="json"),
                        "target_iri": review.target_iri,
                        "expires_at": review.expires_at.isoformat(),
                        "active": review.active,
                        "qualifications": sorted(review.qualifications),
                        "actor_id": actor.actor_id,
                        "attestation_id": attestation_id,
                    },
                )
            )
            return revision
