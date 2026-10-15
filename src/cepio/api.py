from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ._version import __version__
from .bootstrap import build_runtime_from_settings
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

app = FastAPI(
    title="CEPIO Operational Ontology API",
    version=__version__,
    description=(
        "Semantic + kinetic runtime for Energy & Process Industry ontology applications. "
        "The stable public contract is exposed under /api/v1. Unversioned routes are "
        "retained temporarily for compatibility and are not the long-term public contract."
    ),
)
runtime = build_runtime_from_settings()


def _graph_analytics() -> GraphAnalyticsEngine:
    return GraphAnalyticsEngine(runtime.object_repository)


class FunctionBody(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.get("/health", include_in_schema=False)
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


@app.put("/objects/{object_id}", response_model=OntologyObject, include_in_schema=False)
def upsert_object(object_id: str, obj: OntologyObject, expected_version: int | None = Query(default=None, ge=0)) -> OntologyObject:
    if object_id != obj.id:
        raise HTTPException(status_code=400, detail="Path/object id mismatch")
    try:
        return runtime.upsert_object(obj, expected_version=expected_version)
    except ConcurrencyError as exc:
        raise HTTPException(status_code=409, detail={"code": "version_conflict", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}", response_model=OntologyObject, include_in_schema=False)
def get_object(object_id: str) -> OntologyObject:
    try:
        return runtime.get_object(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/objects", response_model=list[OntologyObject], include_in_schema=False)
def list_objects(object_type: str | None = None) -> list[OntologyObject]:
    return runtime.list_objects(object_type)


@app.post("/query/objects", response_model=ObjectQueryResult, include_in_schema=False)
def query_objects(query: ObjectQuery) -> ObjectQueryResult:
    try:
        method = getattr(runtime, "query_objects", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose the typed query contract")
        return method(query)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "query_validation", "message": str(exc)}) from exc


@app.post("/relationships", response_model=Relationship, include_in_schema=False)
def add_relationship(rel: Relationship) -> Relationship:
    try:
        return runtime.add_relationship(rel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "semantic_validation", "message": str(exc)}) from exc


@app.get("/objects/{object_id}/neighbors", response_model=list[OntologyObject], include_in_schema=False)
def neighbors(object_id: str, relationship_type: str | None = None) -> list[OntologyObject]:
    try:
        return runtime.neighbors(object_id, relationship_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/graph/backend", response_model=GraphBackendInfo, include_in_schema=False)
def graph_backend() -> GraphBackendInfo:
    return _graph_analytics().backend_info()


@app.get("/graph/centrality", response_model=CentralityResult, include_in_schema=False)
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


@app.get("/graph/blast-radius/{object_id}", response_model=BlastRadiusResult, include_in_schema=False)
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


@app.get("/graph/communities", response_model=CommunityResult, include_in_schema=False)
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


@app.post("/events", response_model=OperationalEvent, include_in_schema=False)
def record_event(event: OperationalEvent) -> OperationalEvent:
    try:
        return runtime.record_event(event)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/objects/{object_id}/events", response_model=list[OperationalEvent], include_in_schema=False)
def events_for(object_id: str) -> list[OperationalEvent]:
    try:
        return runtime.events_for(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/actions", include_in_schema=False)
def execute_action(request: ActionRequest):
    try:
        return runtime.execute_action(request)
    except AuthorizationError as exc:
        detail = exc.result.model_dump(mode="json") if exc.result else {"message": str(exc)}
        raise HTTPException(status_code=403, detail=detail) from exc


@app.post("/functions/{name}", include_in_schema=False)
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


@app.post("/decisions", response_model=Decision, include_in_schema=False)
def save_decision(decision: Decision) -> Decision:
    try:
        return runtime.save_decision(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/decisions/{decision_id}", response_model=Decision, include_in_schema=False)
def get_decision(decision_id: str) -> Decision:
    try:
        return runtime.get_decision(decision_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/audit", include_in_schema=False)
def audit() -> list[dict[str, Any]]:
    return [entry.model_dump(mode="json") for entry in runtime.all_audits()]


def _register_v1_routes() -> None:
    """Register the stable public API v1 surface over existing runtime operations.

    The unversioned routes remain callable as a temporary compatibility layer but are
    intentionally omitted from OpenAPI. API v1 is the only documented public surface.
    """

    routes = [
        ("/health", health, ["GET"], None, "getHealth", "system"),
        ("/objects/{object_id}", upsert_object, ["PUT"], OntologyObject, "upsertObject", "objects"),
        ("/objects/{object_id}", get_object, ["GET"], OntologyObject, "getObject", "objects"),
        ("/objects", list_objects, ["GET"], list[OntologyObject], "listObjects", "objects"),
        ("/query/objects", query_objects, ["POST"], ObjectQueryResult, "queryObjects", "query"),
        ("/relationships", add_relationship, ["POST"], Relationship, "addRelationship", "relationships"),
        ("/objects/{object_id}/neighbors", neighbors, ["GET"], list[OntologyObject], "getNeighbors", "relationships"),
        ("/graph/backend", graph_backend, ["GET"], GraphBackendInfo, "getGraphBackend", "graph"),
        ("/graph/centrality", graph_centrality, ["GET"], CentralityResult, "getGraphCentrality", "graph"),
        ("/graph/blast-radius/{object_id}", graph_blast_radius, ["GET"], BlastRadiusResult, "getBlastRadius", "graph"),
        ("/graph/communities", graph_communities, ["GET"], CommunityResult, "getGraphCommunities", "graph"),
        ("/events", record_event, ["POST"], OperationalEvent, "recordEvent", "events"),
        ("/objects/{object_id}/events", events_for, ["GET"], list[OperationalEvent], "listObjectEvents", "events"),
        ("/actions", execute_action, ["POST"], None, "executeAction", "actions"),
        ("/functions/{name}", call_function, ["POST"], dict[str, Any], "callFunction", "functions"),
        ("/decisions", save_decision, ["POST"], Decision, "saveDecision", "decisions"),
        ("/decisions/{decision_id}", get_decision, ["GET"], Decision, "getDecision", "decisions"),
        ("/audit", audit, ["GET"], list[dict[str, Any]], "listAudit", "audit"),
    ]
    for path, endpoint, methods, response_model, operation_id, tag in routes:
        app.add_api_route(
            f"/api/v1{path}",
            endpoint,
            methods=methods,
            response_model=response_model,
            operation_id=operation_id,
            tags=[tag],
        )


_register_v1_routes()
