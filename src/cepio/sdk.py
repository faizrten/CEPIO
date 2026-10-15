from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from .graph_analytics import BlastRadiusResult, CentralityResult, CommunityResult, GraphBackendInfo
from .model import ActionRequest, ActionResult, Decision, OntologyObject, OperationalEvent, Relationship
from .query import ObjectQuery, ObjectQueryResult


API_OPERATIONS: dict[str, tuple[str, str]] = {
    "getHealth": ("GET", "/api/v1/health"),
    "listObjects": ("GET", "/api/v1/objects"),
    "getObject": ("GET", "/api/v1/objects/{object_id}"),
    "upsertObject": ("PUT", "/api/v1/objects/{object_id}"),
    "queryObjects": ("POST", "/api/v1/query/objects"),
    "addRelationship": ("POST", "/api/v1/relationships"),
    "getNeighbors": ("GET", "/api/v1/objects/{object_id}/neighbors"),
    "getGraphBackend": ("GET", "/api/v1/graph/backend"),
    "getGraphCentrality": ("GET", "/api/v1/graph/centrality"),
    "getBlastRadius": ("GET", "/api/v1/graph/blast-radius/{object_id}"),
    "getGraphCommunities": ("GET", "/api/v1/graph/communities"),
    "recordEvent": ("POST", "/api/v1/events"),
    "listObjectEvents": ("GET", "/api/v1/objects/{object_id}/events"),
    "executeAction": ("POST", "/api/v1/actions"),
    "callFunction": ("POST", "/api/v1/functions/{name}"),
    "saveDecision": ("POST", "/api/v1/decisions"),
    "getDecision": ("GET", "/api/v1/decisions/{decision_id}"),
    "listAudit": ("GET", "/api/v1/audit"),
}


class CEPIOClient:
    """Thin typed client for the supported CEPIO `/api/v1` HTTP contract."""

    def __init__(
        self,
        base_url: str,
        *,
        access_token: str | None = None,
        dev_actor: str | None = None,
        dev_roles: set[str] | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if access_token and (dev_actor or dev_roles):
            raise ValueError("Use either an Entra access token or development identity headers, not both")
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if dev_actor:
            headers["X-CEPIO-Dev-Actor"] = dev_actor
        if dev_roles:
            headers["X-CEPIO-Dev-Roles"] = ",".join(sorted(dev_roles))
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CEPIOClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @staticmethod
    def _path(operation_id: str, **path_params: str) -> str:
        _, template = API_OPERATIONS[operation_id]
        escaped = {key: quote(str(value), safe="") for key, value in path_params.items()}
        return template.format(**escaped)

    def health(self) -> dict[str, Any]:
        response = self._client.get(self._path("getHealth"))
        response.raise_for_status()
        return response.json()

    def get_object(self, object_id: str) -> OntologyObject:
        obj, _ = self.get_object_with_etag(object_id)
        return obj

    def get_object_with_etag(self, object_id: str) -> tuple[OntologyObject, str | None]:
        response = self._client.get(self._path("getObject", object_id=object_id))
        response.raise_for_status()
        return OntologyObject.model_validate(response.json()), response.headers.get("ETag")

    def upsert_object(self, obj: OntologyObject, *, expected_version: int | None = None) -> OntologyObject:
        headers = {"If-Match": f'"{expected_version}"'} if expected_version is not None else None
        response = self._client.put(
            self._path("upsertObject", object_id=obj.id),
            headers=headers,
            json=obj.model_dump(mode="json"),
        )
        response.raise_for_status()
        return OntologyObject.model_validate(response.json())

    def list_objects(self, object_type: str | None = None) -> list[OntologyObject]:
        params = {"object_type": object_type} if object_type is not None else None
        response = self._client.get(self._path("listObjects"), params=params)
        response.raise_for_status()
        return [OntologyObject.model_validate(value) for value in response.json()]

    def query_objects(self, query: ObjectQuery) -> ObjectQueryResult:
        response = self._client.post(
            self._path("queryObjects"), json=query.model_dump(mode="json")
        )
        response.raise_for_status()
        return ObjectQueryResult.model_validate(response.json())

    def add_relationship(self, rel: Relationship) -> Relationship:
        response = self._client.post(
            self._path("addRelationship"), json=rel.model_dump(mode="json")
        )
        response.raise_for_status()
        return Relationship.model_validate(response.json())

    def neighbors(self, object_id: str, relationship_type: str | None = None) -> list[OntologyObject]:
        params = {"relationship_type": relationship_type} if relationship_type else None
        response = self._client.get(
            self._path("getNeighbors", object_id=object_id), params=params
        )
        response.raise_for_status()
        return [OntologyObject.model_validate(value) for value in response.json()]

    def graph_backend(self) -> GraphBackendInfo:
        response = self._client.get(self._path("getGraphBackend"))
        response.raise_for_status()
        return GraphBackendInfo.model_validate(response.json())

    def graph_centrality(
        self,
        algorithm: str = "pagerank",
        *,
        relationship_types: list[str] | None = None,
        object_types: list[str] | None = None,
        limit: int = 50,
        sample_size: int | None = None,
    ) -> CentralityResult:
        params: list[tuple[str, str | int]] = [("algorithm", algorithm), ("limit", limit)]
        if sample_size is not None:
            params.append(("sample_size", sample_size))
        params.extend(("relationship_type", value) for value in relationship_types or [])
        params.extend(("object_type", value) for value in object_types or [])
        response = self._client.get(self._path("getGraphCentrality"), params=params)
        response.raise_for_status()
        return CentralityResult.model_validate(response.json())

    def graph_blast_radius(
        self,
        object_id: str,
        *,
        max_hops: int = 3,
        direction: str = "out",
        relationship_types: list[str] | None = None,
        object_types: list[str] | None = None,
    ) -> BlastRadiusResult:
        params: list[tuple[str, str | int]] = [("max_hops", max_hops), ("direction", direction)]
        params.extend(("relationship_type", value) for value in relationship_types or [])
        params.extend(("object_type", value) for value in object_types or [])
        response = self._client.get(
            self._path("getBlastRadius", object_id=object_id), params=params
        )
        response.raise_for_status()
        return BlastRadiusResult.model_validate(response.json())

    def graph_communities(
        self,
        *,
        relationship_types: list[str] | None = None,
        object_types: list[str] | None = None,
    ) -> CommunityResult:
        params: list[tuple[str, str]] = []
        params.extend(("relationship_type", value) for value in relationship_types or [])
        params.extend(("object_type", value) for value in object_types or [])
        response = self._client.get(self._path("getGraphCommunities"), params=params)
        response.raise_for_status()
        return CommunityResult.model_validate(response.json())

    def record_event(self, event: OperationalEvent) -> OperationalEvent:
        response = self._client.post(
            self._path("recordEvent"), json=event.model_dump(mode="json")
        )
        response.raise_for_status()
        return OperationalEvent.model_validate(response.json())

    def events_for(self, object_id: str) -> list[OperationalEvent]:
        response = self._client.get(self._path("listObjectEvents", object_id=object_id))
        response.raise_for_status()
        return [OperationalEvent.model_validate(value) for value in response.json()]

    def execute_action(
        self,
        request: ActionRequest,
        *,
        idempotency_key: str | None = None,
    ) -> ActionResult:
        payload = {
            "action_type": request.action_type,
            "target": request.target.model_dump(mode="json"),
            "parameters": request.parameters,
            "correlation_id": request.correlation_id,
            "decision_id": request.decision_id,
        }
        effective_key = idempotency_key or request.idempotency_key
        headers = {"Idempotency-Key": effective_key} if effective_key else None
        response = self._client.post(
            self._path("executeAction"), headers=headers, json=payload
        )
        response.raise_for_status()
        return ActionResult.model_validate(response.json())

    def call_function(self, name: str, arguments: dict[str, Any]) -> Any:
        response = self._client.post(
            self._path("callFunction", name=name), json={"arguments": arguments}
        )
        response.raise_for_status()
        return response.json()["result"]

    def save_decision(self, decision: Decision) -> Decision:
        response = self._client.post(
            self._path("saveDecision"), json=decision.model_dump(mode="json")
        )
        response.raise_for_status()
        return Decision.model_validate(response.json())

    def get_decision(self, decision_id: str) -> Decision:
        response = self._client.get(
            self._path("getDecision", decision_id=decision_id)
        )
        response.raise_for_status()
        return Decision.model_validate(response.json())

    def audit(
        self,
        *,
        target_id: str | None = None,
        actor_id: str | None = None,
        from_time: datetime | None = None,
        until_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if target_id is not None:
            params["target_id"] = target_id
        if actor_id is not None:
            params["actor_id"] = actor_id
        if from_time is not None:
            params["from_time"] = from_time.isoformat()
        if until_time is not None:
            params["until_time"] = until_time.isoformat()
        response = self._client.get(self._path("listAudit"), params=params or None)
        response.raise_for_status()
        return response.json()
