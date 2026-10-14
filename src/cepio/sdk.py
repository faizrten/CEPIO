from __future__ import annotations

from typing import Any

import httpx

from .graph_analytics import BlastRadiusResult, CentralityResult, CommunityResult, GraphBackendInfo
from .model import ActionRequest, ActionResult, OntologyObject, Relationship
from .query import ObjectQuery, ObjectQueryResult


class CEPIOClient:
    """Thin typed Python client for the CEPIO HTTP API."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def get_object(self, object_id: str) -> OntologyObject:
        response = self._client.get(f"/objects/{object_id}")
        response.raise_for_status()
        return OntologyObject.model_validate(response.json())

    def upsert_object(self, obj: OntologyObject, *, expected_version: int | None = None) -> OntologyObject:
        params = {"expected_version": expected_version} if expected_version is not None else None
        response = self._client.put(f"/objects/{obj.id}", params=params, json=obj.model_dump(mode="json"))
        response.raise_for_status()
        return OntologyObject.model_validate(response.json())

    def query_objects(self, query: ObjectQuery) -> ObjectQueryResult:
        response = self._client.post("/query/objects", json=query.model_dump(mode="json"))
        response.raise_for_status()
        return ObjectQueryResult.model_validate(response.json())

    def add_relationship(self, rel: Relationship) -> Relationship:
        response = self._client.post("/relationships", json=rel.model_dump(mode="json"))
        response.raise_for_status()
        return Relationship.model_validate(response.json())

    def graph_backend(self) -> GraphBackendInfo:
        response = self._client.get("/graph/backend")
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
        response = self._client.get("/graph/centrality", params=params)
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
        response = self._client.get(f"/graph/blast-radius/{object_id}", params=params)
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
        response = self._client.get("/graph/communities", params=params)
        response.raise_for_status()
        return CommunityResult.model_validate(response.json())

    def execute_action(self, request: ActionRequest) -> ActionResult:
        response = self._client.post("/actions", json=request.model_dump(mode="json"))
        response.raise_for_status()
        return ActionResult.model_validate(response.json())

    def call_function(self, name: str, arguments: dict[str, Any]) -> Any:
        response = self._client.post(f"/functions/{name}", json={"arguments": arguments})
        response.raise_for_status()
        return response.json()["result"]
