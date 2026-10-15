from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from . import api as legacy
from .graph_analytics import BlastRadiusResult, CentralityResult, CommunityResult, GraphBackendInfo
from .model import Decision, OntologyObject, OperationalEvent, Relationship
from .query import ObjectQueryResult


app: FastAPI = legacy.app
app.description = (
    "Semantic + kinetic runtime for Energy & Process Industry ontology applications. "
    "The supported public REST contract is exposed under /api/v1. Unversioned routes "
    "remain temporarily for compatibility but are excluded from the public OpenAPI contract."
)


V1_ROUTES: tuple[tuple[str, Any, list[str], Any, str, str], ...] = (
    ("/health", legacy.health, ["GET"], None, "getHealth", "system"),
    ("/objects/{object_id}", legacy.upsert_object, ["PUT"], OntologyObject, "upsertObject", "objects"),
    ("/objects/{object_id}", legacy.get_object, ["GET"], OntologyObject, "getObject", "objects"),
    ("/objects", legacy.list_objects, ["GET"], list[OntologyObject], "listObjects", "objects"),
    ("/query/objects", legacy.query_objects, ["POST"], ObjectQueryResult, "queryObjects", "query"),
    ("/relationships", legacy.add_relationship, ["POST"], Relationship, "addRelationship", "relationships"),
    ("/objects/{object_id}/neighbors", legacy.neighbors, ["GET"], list[OntologyObject], "getNeighbors", "relationships"),
    ("/graph/backend", legacy.graph_backend, ["GET"], GraphBackendInfo, "getGraphBackend", "graph"),
    ("/graph/centrality", legacy.graph_centrality, ["GET"], CentralityResult, "getGraphCentrality", "graph"),
    ("/graph/blast-radius/{object_id}", legacy.graph_blast_radius, ["GET"], BlastRadiusResult, "getBlastRadius", "graph"),
    ("/graph/communities", legacy.graph_communities, ["GET"], CommunityResult, "getGraphCommunities", "graph"),
    ("/events", legacy.record_event, ["POST"], OperationalEvent, "recordEvent", "events"),
    ("/objects/{object_id}/events", legacy.events_for, ["GET"], list[OperationalEvent], "listObjectEvents", "events"),
    ("/actions", legacy.execute_action, ["POST"], None, "executeAction", "actions"),
    ("/functions/{name}", legacy.call_function, ["POST"], dict[str, Any], "callFunction", "functions"),
    ("/decisions", legacy.save_decision, ["POST"], Decision, "saveDecision", "decisions"),
    ("/decisions/{decision_id}", legacy.get_decision, ["GET"], Decision, "getDecision", "decisions"),
    ("/audit", legacy.audit, ["GET"], list[dict[str, Any]], "listAudit", "audit"),
)


def _install_v1_routes() -> None:
    existing = {(route.path, frozenset(route.methods or set())) for route in app.routes if hasattr(route, "methods")}
    for path, endpoint, methods, response_model, operation_id, tag in V1_ROUTES:
        full_path = f"/api/v1{path}"
        signature = (full_path, frozenset(methods))
        if signature in existing:
            continue
        app.add_api_route(
            full_path,
            endpoint,
            methods=methods,
            response_model=response_model,
            operation_id=operation_id,
            tags=[tag],
        )


def _public_openapi() -> dict[str, Any]:
    if app.openapi_schema is not None:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["paths"] = {
        path: item
        for path, item in schema.get("paths", {}).items()
        if path.startswith("/api/v1/")
    }
    app.openapi_schema = schema
    return schema


_install_v1_routes()
app.openapi_schema = None
app.openapi = _public_openapi  # type: ignore[method-assign]
