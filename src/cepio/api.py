from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .bootstrap import build_runtime
from .graph_analytics import (
    BlastRadiusResult,
    CentralityResult,
    CommunityResult,
    GraphAnalyticsEngine,
    GraphBackendInfo,
    GraphBackendUnavailable,
)
from .model import ActionRequest, Decision, OntologyObject, OperationalEvent, Relationship
from .query import ObjectQuery, ObjectQueryResult
from .repositories import ConcurrencyError
from .runtime import AuthorizationError

app = FastAPI(title="CEPIO Operational Ontology API", version="0.3.0", description="Semantic + kinetic runtime for Energy & Process Industry ontology applications.")
runtime = build_runtime()


def _graph_analytics() -> GraphAnalyticsEngine:
    # Resolve lazily so runtime/repository swaps (tests, tenants, deployments) do not
    # leave graph analytics bound to stale state.
    return GraphAnalyticsEngine(runtime.object_repository)


class FunctionBody(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.3.0"}


@app.put("/objects/{object_id}", response_model=OntologyObject)
def upsert_object(object_id: str, obj: OntologyObject, expected_version: int | None = Query(default=None, ge=0)) -> OntologyObject:
    if object_id != obj.id:
        raise HTTPException(status_code=400, detail="Path/object id mismatch")
    try:
        return runtime.upsert_object(obj, expected_version=expected_version)
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail={"code": "version_conflict", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}", response_model=OntologyObject)
def get_object(object_id: str) -> OntologyObject:
    try:
        return runtime.get_object(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/objects", response_model=list[OntologyObject])
def list_objects(object_type: str | None = None) -> list[OntologyObject]:
    return runtime.list_objects(object_type)


@app.post("/query/objects", response_model=ObjectQueryResult)
def query_objects(query: ObjectQuery) -> ObjectQueryResult:
    try:
        method = getattr(runtime, "query_objects", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose the typed query contract")
        return method(query)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "query_validation", "message": str(exc)}) from exc


@app.post("/relationships", response_model=Relationship)
def add_relationship(rel: Relationship) -> Relationship:
    try:
        return runtime.add_relationship(rel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}/neighbors", response_model=list[OntologyObject])
def neighbors(object_id: str, relationship_type: str | None = None) -> list[OntologyObject]:
    try:
        return runtime.neighbors(object_id, relationship_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/graph/backend", response_model=GraphBackendInfo)
def graph_backend() -> GraphBackendInfo:
    return _graph_analytics().backend_info()


@app.get("/graph/centrality", response_model=CentralityResult)
def graph_centrality(
    algorithm: str = "pagerank",
    relationship_type: list[str] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    sample_size: int | None = Query(default=None, ge=1),
) -> CentralityResult:
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
) -> BlastRadiusResult:
    try:
        return _graph_analytics().blast_radius(
            object_id,
            max_hops=max_hops,
            direction=direction,  # type: ignore[arg-type]
            relationship_types=relationship_type,
            object_types=object_type,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GraphBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "graph_backend_unavailable", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "graph_analytics_validation", "message": str(exc)}) from exc


@app.get("/graph/communities", response_model=CommunityResult)
def graph_communities(
    relationship_type: list[str] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
) -> CommunityResult:
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
def record_event(event: OperationalEvent) -> OperationalEvent:
    try:
        return runtime.record_event(event)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/objects/{object_id}/events", response_model=list[OperationalEvent])
def events_for(object_id: str) -> list[OperationalEvent]:
    try:
        return runtime.events_for(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/actions")
def execute_action(request: ActionRequest):
    try:
        return runtime.execute_action(request)
    except AuthorizationError as exc:
        detail = exc.result.model_dump(mode="json") if exc.result else {"message": str(exc)}
        raise HTTPException(status_code=403, detail=detail) from exc


@app.post("/functions/{name}")
def call_function(name: str, body: FunctionBody) -> dict[str, Any]:
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
def save_decision(decision: Decision) -> Decision:
    try:
        return runtime.save_decision(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/decisions/{decision_id}", response_model=Decision)
def get_decision(decision_id: str) -> Decision:
    try:
        return runtime.get_decision(decision_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/audit")
def audit() -> list[dict[str, Any]]:
    return [entry.model_dump(mode="json") for entry in runtime.all_audits()]
