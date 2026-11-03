"""Read-only, actor-scoped Operational Object inspection (reference v0.1).

This is an application-layer composition over existing Core contracts. It is NOT a
second ontology, source adapter, live-state assessor, permission grant, or Action API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import (
    CEPIOApplicationService,
    ContextEnvelope,
    ContractMetadata,
    ExecutionContext,
)
from .model import ObjectRef
from .runtime import AuthorizationError


class VisibleOperationalLink(BaseModel):
    """Visible relationship metadata only; never copies raw link properties."""

    model_config = ConfigDict(frozen=True)

    relationship_type: str
    direction: Literal["out", "in"]
    related: ObjectRef


class OperationalObjectInspection(BaseModel):
    """A bounded, non-executing object context for a human or trusted agent host."""

    model_config = ConfigDict(frozen=True)

    context: ContextEnvelope
    links: list[VisibleOperationalLink] = Field(default_factory=list)
    evidence_qualification: Literal["not_attested"] = "not_attested"
    state_qualification: Literal["not_live_qualified"] = "not_live_qualified"
    action_qualification: Literal["not_evaluated"] = "not_evaluated"


def inspect_operational_object(
    service: CEPIOApplicationService,
    object_id: str,
    context: ExecutionContext,
    *,
    max_related: int = 25,
) -> OperationalObjectInspection:
    """Project one object and authorized first-hop links without changing state.

    Host-owned ExecutionContext is mandatory. A related object is exposed only after
    the same actor-scoped read used by the Application Contract. No raw repository
    object, events, provenance claim, policy decision, or action is materialized.

    This bounded reference uses the repository relationship contract. Before any
    remote API exposure, a production host must qualify tenancy, pagination, and
    relationship-level classification as well as live evidence/source freshness.
    """
    if not 1 <= max_related <= 50:
        raise ValueError("max_related must be between 1 and 50")

    subject = service.read_object(object_id, context)
    repository = service.runtime.object_repository
    candidates: list[tuple[str, str, ObjectRef]] = []

    for direction in ("out", "in"):
        for relationship in repository.get_relationships(object_id, direction=direction):
            local = relationship.source if direction == "out" else relationship.target
            other = relationship.target if direction == "out" else relationship.source
            if local.id != object_id or local.type != subject.type:
                raise ValueError("Inconsistent relationship identity or subject type")
            candidates.append((relationship.type, direction, other))

    related_by_id = {}
    visible_links: list[VisibleOperationalLink] = []
    seen: set[tuple[str, str, str]] = set()
    for relationship_type, direction, other_ref in sorted(
        candidates, key=lambda row: (row[0], row[1], row[2].id, row[2].type)
    ):
        key = (relationship_type, direction, other_ref.id)
        if key in seen:
            continue
        try:
            other = service.read_object(other_ref.id, context)
        except AuthorizationError:
            # Do not reveal existence, identities or counts of inaccessible neighbors.
            continue
        if other.type != other_ref.type:
            raise ValueError("Inconsistent related object type")
        seen.add(key)
        if other.id not in related_by_id and len(related_by_id) >= max_related:
            continue
        related_by_id[other.id] = other
        visible_links.append(
            VisibleOperationalLink(
                relationship_type=relationship_type,
                direction=direction,
                related=ObjectRef(id=other.id, type=other.type),
            )
        )

    return OperationalObjectInspection(
        context=ContextEnvelope(
            subject=subject,
            related_objects=list(related_by_id.values()),
            metadata=ContractMetadata(correlation_id=context.correlation_id),
        ),
        links=visible_links,
    )
