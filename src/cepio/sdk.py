from __future__ import annotations

from typing import Any

import httpx

from .model import ActionRequest, ActionResult, OntologyObject, Relationship


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

    def add_relationship(self, rel: Relationship) -> Relationship:
        response = self._client.post("/relationships", json=rel.model_dump(mode="json"))
        response.raise_for_status()
        return Relationship.model_validate(response.json())

    def execute_action(self, request: ActionRequest) -> ActionResult:
        response = self._client.post("/actions", json=request.model_dump(mode="json"))
        response.raise_for_status()
        return ActionResult.model_validate(response.json())

    def call_function(self, name: str, arguments: dict[str, Any]) -> Any:
        response = self._client.post(f"/functions/{name}", json=arguments)
        response.raise_for_status()
        return response.json()["result"]
