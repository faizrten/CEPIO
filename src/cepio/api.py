from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ._version import __version__
from .auth import ActorContext, get_actor_context
from .bootstrap import build_runtime_from_settings
from .graph_analytics import (
    BlastRadiusResult,
    CentralityResult,
    CommunityResult,
    GraphAnalyticsEngine,
    GraphBackendInfo,
    GraphBackendUnavailable,
)
from .model import (
    ActionRequest,
    ActionStatus,
    AuditEntry,
    Decision,
    ObjectRef,
    OntologyObject,
    OperationalEvent,
    PolicyEffect,
    Relationship,
)
from .query import ObjectQuery, ObjectQueryResult
from .repositories import ConcurrencyError
from .runtime import AuthorizationError

app = FastAPI(
    title="CEPIO Operational Ontology API",
    version=__version__,
    description="Semantic + kinetic runtime for Energy & Process Industry ontology applications.",
)
runtime = build_runtime_from_settings()


def _graph_analytics() -> GraphAnalyticsEngine:
    return GraphAnalyticsEngine(runtime.object_repository)


class FunctionBody(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActionBody(BaseModel):
    action_type: str
    target: ObjectRef
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    correlation_id: str | None = None
    decision_id: str | None = None
    actor_id: str | None = Field(default=None, description="Deprecated; identity is derived from the access token")
    actor_roles: set[str] | None = Field(default=None, description="Deprecated; roles are derived from the access token")


def _require_any_role(actor: ActorContext, *roles: str) -> None:
    if not actor.roles.intersection(roles):
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": f"Required role: one of {sorted(roles)}"},
        )


def _visible_object(obj: OntologyObject, actor: ActorContext) -> OntologyObject | None:
    if not runtime.policy_engine.can_read_type(actor.roles, obj.type):
        return None
    return runtime.policy_engine.filter_properties(actor.roles, obj)


def _audit_spoof_attempt(body: ActionBody, actor: ActorContext) -> None:
    entry = AuditEntry(
        action_id=str(uuid4()),
        action_type=body.action_type,
        target=body.target,
        actor_id=actor.actor_id,
        actor_roles=actor.roles,
        status=ActionStatus.rejected,
        message="Request attempted to supply actor identity or roles inconsistent with authenticated identity",
        idempotency_key=body.idempotency_key,
        correlation_id=body.correlation_id,
        decision_id=body.decision_id,
        policy_effect=PolicyEffect.deny,
        policy_reasons=["REST actor identity and roles must be derived from the authenticated token"],
    )
    runtime.audit_repository.append_audit(entry)


@app.get("/health")
def health() -> dict:
    catalogue = getattr(runtime, "module_catalogue", None)
    module_versions = (
        {module_id: module.version for module_id, module in catalogue.modules.items()}
        if catalogue is not None
        else {}
    )
    return {
        "status": "ok",
        "version": __version__,
        "ontology_catalogue_schema": getattr(catalogue, "schema_version", None),
        "ontology_modules": module_versions,
        "profiles": getattr(runtime, "profile_versions", {}),
    }


@app.put("/objects/{object_id}", response_model=OntologyObject)
def upsert_object(
    object_id: str,
    obj: OntologyObject,
    expected_version: int | None = Query(default=None, ge=0),
    actor: ActorContext = Depends(get_actor_context),
) -> OntologyObject:
    _require_any_role(actor, "cepio_admin")
    if object_id != obj.id:
        raise HTTPException(status_code=400, detail="Path/object id mismatch")
    try:
        return runtime.upsert_object(obj, expected_version=expected_version)
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail={"code": "version_conflict", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}", response_model=OntologyObject)
def get_object(object_id: str, actor: ActorContext = Depends(get_actor_context)) -> OntologyObject:
    try:
        return runtime.read_object_for_actor(object_id, actor.roles)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc


@app.get("/objects", response_model=list[OntologyObject])
def list_objects(
    object_type: str | None = None,
    actor: ActorContext = Depends(get_actor_context),
) -> list[OntologyObject]:
    visible: list[OntologyObject] = []
    for obj in runtime.list_objects(object_type):
        filtered = _visible_object(obj, actor)
        if filtered is not None:
            visible.append(filtered)
    return visible


@app.post("/query/objects", response_model=ObjectQueryResult)
def query_objects(
    query: ObjectQuery,
    actor: ActorContext = Depends(get_actor_context),
) -> ObjectQueryResult:
    try:
        method = getattr(runtime, "query_objects_for_actor", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose actor-scoped typed queries")
        return method(query, actor.roles)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "query_validation", "message": str(exc)}) from exc


@app.post("/relationships", response_model=Relationship)
def add_relationship(
    rel: Relationship,
    actor: ActorContext = Depends(get_actor_context),
) -> Relationship:
    _require_any_role(actor, "cepio_admin")
    try:
        return runtime.add_relationship(rel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}/neighbors", response_model=list[OntologyObject])
def neighbors(
    object_id: str,
    relationship_type: str | None = None,
    direction: str = Query(default="out", pattern="^(out|in)$"),
    actor: ActorContext = Depends(get_actor_context),
) -> list[OntologyObject]:
    try:
        runtime.read_object_for_actor(object_id, actor.roles)
        related = (
            runtime.reverse_neighbors(object_id, relationship_type)
            if direction == "in"
            else runtime.neighbors(object_id, relationship_type)
        )
        visible: list[OntologyObject] = []
        for obj in related:
            filtered = _visible_object(obj, actor)
            if filtered is not None:
                visible.append(filtered)
        return visible
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc


@app.get("/graph/backend", response_model=GraphBackendInfo)
def graph_backend(actor: ActorContext = Depends(get_actor_context)) -> GraphBackendInfo:
    return _graph_analytics().backend_info()


@app.get("/graph/centrality", response_model=CentralityResult)
def graph_centrality(
    algorithm: str = "pagerank",
    relationship_type: list[str] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    sample_size: int | None = Query(default=None, ge=1),
    actor: ActorContext = Depends(get_actor_context),
) -> CentralityResult:
    _require_any_role(actor, "graph_analyst", "auditor", "cepio_admin")
    try:
        return _graph_analytics().centrality(
            algorithm,  # type: ignore[arg-type]
            relationship_types=relationship_type,
            object_types=object_type,
            limit=limit,
            sample_size=sample_size,
        )
    except GraphBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "graph_backend_unavailable", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "graph_analytics_validation", "message": str(exc)}) from exc


@app.get("/graph/blast-radius/{object_id}", response_model=BlastRadiusResult)
def graph_blast_radius(
    object_id: str,
    max_hops: int = Query(default=3, ge=1, le=20),
    direction: str = Query(default="out"),
    relationship_type: list[str] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    actor: ActorContext = Depends(get_actor_context),
) -> BlastRadiusResult:
    _require_any_role(actor, "graph_analyst", "auditor", "cepio_admin")
    try:
        runtime.read_object_for_actor(object_id, actor.roles)
        return _graph_analytics().blast_radius(
            object_id,
            max_hops=max_hops,
            direction=direction,  # type: ignore[arg-type]
            relationship_types=relationship_type,
            object_types=object_type,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc
    except GraphBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "graph_backend_unavailable", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "graph_analytics_validation", "message": str(exc)}) from exc


@app.get("/graph/communities", response_model=CommunityResult)
def graph_communities(
    relationship_type: list[str] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    actor: ActorContext = Depends(get_actor_context),
) -> CommunityResult:
    _require_any_role(actor, "graph_analyst", "auditor", "cepio_admin")
    try:
        return _graph_analytics().communities(
            relationship_types=relationship_type,
            object_types=object_type,
        )
    except GraphBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "graph_backend_unavailable", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "graph_analytics_validation", "message": str(exc)}) from exc


@app.post("/events", response_model=OperationalEvent)
def record_event(
    event: OperationalEvent,
    actor: ActorContext = Depends(get_actor_context),
) -> OperationalEvent:
    _require_any_role(actor, "cepio_admin", "operator")
    try:
        runtime.read_object_for_actor(event.subject.id, actor.roles)
        return runtime.record_event(event)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc


@app.get("/objects/{object_id}/events", response_model=list[OperationalEvent])
def events_for(
    object_id: str,
    actor: ActorContext = Depends(get_actor_context),
) -> list[OperationalEvent]:
    try:
        runtime.read_object_for_actor(object_id, actor.roles)
        return runtime.events_for(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc


@app.post("/actions")
def execute_action(
    body: ActionBody,
    actor: ActorContext = Depends(get_actor_context),
):
    spoofed_actor = body.actor_id is not None and body.actor_id != actor.actor_id
    spoofed_roles = body.actor_roles is not None and not body.actor_roles.issubset(actor.roles)
    if spoofed_actor or spoofed_roles:
        _audit_spoof_attempt(body, actor)
        raise HTTPException(
            status_code=403,
            detail={"code": "identity_spoof", "message": "Actor identity and roles are derived from the access token"},
        )

    request = ActionRequest(
        action_type=body.action_type,
        target=body.target,
        actor_id=actor.actor_id,
        actor_roles=actor.roles,
        parameters=body.parameters,
        idempotency_key=body.idempotency_key,
        correlation_id=body.correlation_id,
        decision_id=body.decision_id,
    )
    try:
        return runtime.execute_action(request)
    except AuthorizationError as exc:
        detail = exc.result.model_dump(mode="json") if exc.result else {"message": str(exc)}
        raise HTTPException(status_code=403, detail=detail) from exc


@app.post("/functions/{name}")
def call_function(
    name: str,
    body: FunctionBody,
    actor: ActorContext = Depends(get_actor_context),
) -> dict[str, Any]:
    if not runtime.policy_engine.can_call_function(actor.roles, name):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": f"Not authorized to call {name}"})
    try:
        value = runtime.call_function(name, **body.arguments)
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return {"result": value}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "function_validation", "message": str(exc)}) from exc


@app.post("/decisions", response_model=Decision)
def save_decision(
    decision: Decision,
    actor: ActorContext = Depends(get_actor_context),
) -> Decision:
    if decision.decision_type and not runtime.policy_engine.can_propose_decision(
        actor.roles, decision.decision_type
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden",
                "message": f"Not authorized to propose decision {decision.decision_type}",
            },
        )
    try:
        runtime.read_object_for_actor(decision.subject.id, actor.roles)
        stored = decision.model_copy(update={"created_by": actor.actor_id})
        return runtime.save_decision(stored)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "decision_validation", "message": str(exc)},
        ) from exc


@app.get("/decisions/{decision_id}", response_model=Decision)
def get_decision(
    decision_id: str,
    actor: ActorContext = Depends(get_actor_context),
) -> Decision:
    try:
        decision = runtime.get_decision(decision_id)
        runtime.read_object_for_actor(decision.subject.id, actor.roles)
        return decision
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc


@app.get("/audit")
def audit(
    target_id: str | None = None,
    actor_id: str | None = None,
    from_time: datetime | None = None,
    until_time: datetime | None = None,
    actor: ActorContext = Depends(get_actor_context),
) -> list[dict[str, Any]]:
    _require_any_role(actor, "auditor", "cepio_admin")
    entries = runtime.all_audits()
    if target_id is not None:
        entries = [entry for entry in entries if entry.target.id == target_id]
    if actor_id is not None:
        entries = [entry for entry in entries if entry.actor_id == actor_id]
    if from_time is not None:
        entries = [entry for entry in entries if entry.occurred_at >= from_time]
    if until_time is not None:
        entries = [entry for entry in entries if entry.occurred_at <= until_time]
    return [entry.model_dump(mode="json") for entry in entries]
