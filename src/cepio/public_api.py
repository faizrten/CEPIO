from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from . import api as legacy
from .application_contract import ExecutionContext, SkillEvaluation, SkillInvocation
from .application_runtime import build_application_service
from .auth import ActorContext, get_actor_context
from .graph_analytics import BlastRadiusResult, CentralityResult, CommunityResult, GraphBackendInfo
from .model import Decision, ErrorEnvelope, OntologyObject, OperationalEvent, Relationship
from .query import InvalidQueryCursor, ObjectQuery, ObjectQueryResult, QueryBudgetExceeded
from .runtime import AuthorizationError


app: FastAPI = legacy.app
app.description = (
    "Semantic + kinetic runtime for Energy & Process Industry ontology applications. "
    "The supported public REST contract is exposed under /api/v1. Unversioned routes "
    "remain temporarily for compatibility but are excluded from the public OpenAPI contract."
)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4()))


def _error_payload(request: Request, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return ErrorEnvelope(
        code=code,
        message=message,
        requestId=_request_id(request),
        details=details or {},
    ).model_dump(mode="json", by_alias=True)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(HTTPException)
async def public_http_error(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/v1/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or f"http_{exc.status_code}")
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        details = {key: value for key, value in detail.items() if key not in {"code", "message"}}
    else:
        code_by_status = {
            400: "bad_request",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            409: "version_conflict",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_error",
            502: "bad_gateway",
            503: "service_unavailable",
        }
        code = code_by_status.get(exc.status_code, f"http_{exc.status_code}")
        message = str(detail)
        details = {}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(request, code, message, details),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def public_validation_error(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/v1/"):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            request,
            "request_validation",
            "Request validation failed",
            {"errors": exc.errors()},
        ),
    )


def _etag(version: int) -> str:
    return f'"{version}"'


def _parse_if_match(value: str | None) -> int | None:
    if value is None:
        return None
    token = value.strip()
    if token.startswith("W/"):
        token = token[2:].strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    if not token.isdigit():
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_if_match", "message": "If-Match must contain an object version ETag"},
        )
    return int(token)


def v1_get_object(
    object_id: str,
    response: Response,
    actor: ActorContext = Depends(get_actor_context),
) -> OntologyObject:
    obj = legacy.get_object(object_id, actor)
    response.headers["ETag"] = _etag(obj.version)
    return obj


def v1_upsert_object(
    object_id: str,
    obj: OntologyObject,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    actor: ActorContext = Depends(get_actor_context),
) -> OntologyObject:
    stored = legacy.upsert_object(object_id, obj, _parse_if_match(if_match), actor)
    response.headers["ETag"] = _etag(stored.version)
    return stored


def v1_query_objects(
    query: ObjectQuery,
    actor: ActorContext = Depends(get_actor_context),
) -> ObjectQueryResult:
    try:
        method = getattr(legacy.runtime, "query_objects_for_actor", None)
        if method is None:
            raise RuntimeError("Configured CEPIO runtime does not expose actor-scoped typed queries")
        return method(query, actor.roles)
    except QueryBudgetExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail={"code": QueryBudgetExceeded.code, "message": str(exc)},
        ) from exc
    except InvalidQueryCursor as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": InvalidQueryCursor.code, "message": str(exc)},
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "query_validation", "message": str(exc)},
        ) from exc


def v1_evaluate_skill(
    invocation: SkillInvocation,
    request: Request,
    actor: ActorContext = Depends(get_actor_context),
) -> SkillEvaluation:
    service = build_application_service(legacy.runtime)
    context = ExecutionContext.from_principal(
        actor,
        correlation_id=_request_id(request),
    )
    try:
        return service.evaluate_skill(invocation, context)
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "skill_authorization", "message": str(exc)},
        ) from exc


def v1_execute_action(
    body: legacy.ActionBody,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: ActorContext = Depends(get_actor_context),
):
    if body.idempotency_key and idempotency_key and body.idempotency_key != idempotency_key:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "idempotency_key_conflict",
                "message": "Idempotency-Key header conflicts with deprecated body idempotency_key",
            },
        )
    effective = idempotency_key or body.idempotency_key
    normalized = body.model_copy(update={"idempotency_key": effective})
    return legacy.execute_action(normalized, actor)


V1_ROUTES: tuple[tuple[str, Any, list[str], Any, str, str], ...] = (
    ("/health", legacy.health, ["GET"], None, "getHealth", "system"),
    ("/objects/{object_id}", v1_upsert_object, ["PUT"], OntologyObject, "upsertObject", "objects"),
    ("/objects/{object_id}", v1_get_object, ["GET"], OntologyObject, "getObject", "objects"),
    ("/objects", legacy.list_objects, ["GET"], list[OntologyObject], "listObjects", "objects"),
    ("/query/objects", v1_query_objects, ["POST"], ObjectQueryResult, "queryObjects", "query"),
    ("/relationships", legacy.add_relationship, ["POST"], Relationship, "addRelationship", "relationships"),
    ("/objects/{object_id}/neighbors", legacy.neighbors, ["GET"], list[OntologyObject], "getNeighbors", "relationships"),
    ("/graph/backend", legacy.graph_backend, ["GET"], GraphBackendInfo, "getGraphBackend", "graph"),
    ("/graph/centrality", legacy.graph_centrality, ["GET"], CentralityResult, "getGraphCentrality", "graph"),
    ("/graph/blast-radius/{object_id}", legacy.graph_blast_radius, ["GET"], BlastRadiusResult, "getBlastRadius", "graph"),
    ("/graph/communities", legacy.graph_communities, ["GET"], CommunityResult, "getGraphCommunities", "graph"),
    ("/events", legacy.record_event, ["POST"], OperationalEvent, "recordEvent", "events"),
    ("/objects/{object_id}/events", legacy.events_for, ["GET"], list[OperationalEvent], "listObjectEvents", "events"),
    ("/skills/evaluate", v1_evaluate_skill, ["POST"], SkillEvaluation, "evaluateSkill", "skills"),
    ("/actions", v1_execute_action, ["POST"], None, "executeAction", "actions"),
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
