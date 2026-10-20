"""Azure AI Search physical adapter for CEPIO Retrieval & Indexing v0.1."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import timezone
from typing import Any, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, model_validator

from .memory import MemoryRecord
from .retrieval_contracts import (
    BackendHit,
    RetrievalBackendError,
    RetrievalStep,
    RetrievalStrategy,
)


class AzureSearchClientProtocol(Protocol):
    def search(self, search_text: str, **kwargs: Any) -> Iterable[Mapping[str, Any]]: ...

    def upload_documents(self, documents: Sequence[Mapping[str, Any]]) -> Sequence[Any]: ...

    def delete_documents(self, documents: Sequence[Mapping[str, Any]]) -> Sequence[Any]: ...


class AzureSearchConfig(BaseModel):
    endpoint: str
    index_name: str = "cepio-memory-v1"
    search_fields: tuple[str, ...] = ("summary", "tags", "source_system", "resource_type")

    @model_validator(mode="after")
    def validate_endpoint(self) -> "AzureSearchConfig":
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
            raise ValueError("Azure AI Search endpoint must be an HTTPS service root")
        if not self.index_name.strip():
            raise ValueError("Azure AI Search index_name cannot be empty")
        self.endpoint = self.endpoint.rstrip("/")
        return self

    @classmethod
    def from_env(cls) -> "AzureSearchConfig":
        endpoint = os.getenv("CEPIO_AZURE_SEARCH_ENDPOINT", "").strip()
        if not endpoint:
            raise RuntimeError("CEPIO_AZURE_SEARCH_ENDPOINT is required")
        index_name = os.getenv("CEPIO_AZURE_SEARCH_INDEX", "cepio-memory-v1").strip()
        return cls(endpoint=endpoint, index_name=index_name)


def create_managed_identity_search_client(
    config: AzureSearchConfig,
) -> AzureSearchClientProtocol:
    """Create the real SDK client lazily so CEPIO Core stays importable without Azure extras."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.search.documents import SearchClient
    except ImportError as exc:
        raise RuntimeError(
            "Azure AI Search adapter requires the optional 'azure-search' dependency set"
        ) from exc

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return SearchClient(
        endpoint=config.endpoint,
        index_name=config.index_name,
        credential=credential,
    )


def _odata_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _search_in_expression(field: str, values: set[str], *, collection: bool) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if all("|" not in item for item in ordered):
        payload = "|".join(ordered)
        if collection:
            return f"{field}/any(x: search.in(x, {_odata_quote(payload)}, '|'))"
        return f"search.in({field}, {_odata_quote(payload)}, '|')"

    comparisons = " or ".join(f"x eq {_odata_quote(item)}" for item in ordered)
    return (
        f"{field}/any(x: {comparisons})"
        if collection
        else " or ".join(f"{field} eq {_odata_quote(item)}" for item in ordered)
    )


def build_azure_search_filter(step: RetrievalStep) -> str:
    """Translate CEPIO's governed retrieval selectors into a bounded OData filter."""
    clauses: list[str] = []
    if step.tenant_id is None:
        clauses.append("scope eq 'GLOBAL'")
    else:
        clauses.append(f"(scope eq 'GLOBAL' or tenant_id eq {_odata_quote(step.tenant_id)})")

    at = step.at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    clauses.append(f"(expires_at eq null or expires_at gt {at})")

    kind_values = {item.value for item in step.kinds}
    kind_filter = _search_in_expression("kind", kind_values, collection=False)
    if kind_filter:
        clauses.append(f"({kind_filter})")

    tag_filter = _search_in_expression("tags", step.tags, collection=True)
    if tag_filter:
        clauses.append(tag_filter)

    capability_filter = _search_in_expression(
        "capability_ids", step.capability_ids, collection=True
    )
    if capability_filter:
        clauses.append(capability_filter)

    return " and ".join(clauses)


def memory_to_search_document(record: MemoryRecord) -> dict[str, Any]:
    reference = record.reference
    return {
        "id": record.id,
        "summary": record.summary,
        "tenant_id": record.tenant_id,
        "scope": record.scope.value,
        "kind": record.kind.value,
        "capability_ids": sorted(record.capability_ids),
        "tags": sorted(record.tags),
        "source_system": reference.source_system if reference else None,
        "resource_type": reference.resource_type if reference else None,
        "created_at": record.created_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "record_json": record.model_dump_json(),
    }


def azure_search_index_schema(index_name: str = "cepio-memory-v1") -> dict[str, Any]:
    """Portable schema specification; deployment tooling may translate it to SDK/REST models."""
    return {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "summary", "type": "Edm.String", "searchable": True},
            {"name": "tenant_id", "type": "Edm.String", "filterable": True},
            {"name": "scope", "type": "Edm.String", "filterable": True},
            {"name": "kind", "type": "Edm.String", "filterable": True},
            {
                "name": "capability_ids",
                "type": "Collection(Edm.String)",
                "filterable": True,
            },
            {
                "name": "tags",
                "type": "Collection(Edm.String)",
                "searchable": True,
                "filterable": True,
            },
            {
                "name": "source_system",
                "type": "Edm.String",
                "searchable": True,
                "filterable": True,
            },
            {
                "name": "resource_type",
                "type": "Edm.String",
                "searchable": True,
                "filterable": True,
            },
            {
                "name": "created_at",
                "type": "Edm.DateTimeOffset",
                "filterable": True,
                "sortable": True,
            },
            {"name": "expires_at", "type": "Edm.DateTimeOffset", "filterable": True},
            {"name": "record_json", "type": "Edm.String", "retrievable": True},
        ],
    }


def _indexing_succeeded(result: Any) -> bool:
    if isinstance(result, Mapping):
        return bool(result.get("succeeded"))
    return bool(getattr(result, "succeeded", False))


class AzureSearchMemoryBackend:
    """Azure AI Search lexical backend and rebuildable memory-index projection."""

    strategy = RetrievalStrategy.LEXICAL

    def __init__(
        self,
        client: AzureSearchClientProtocol,
        config: AzureSearchConfig,
    ) -> None:
        self.client = client
        self.config = config

    def upsert(self, record: MemoryRecord) -> None:
        results = self.client.upload_documents([memory_to_search_document(record)])
        if not results or not all(_indexing_succeeded(item) for item in results):
            raise RetrievalBackendError(f"Azure AI Search failed to index memory {record.id}")

    def upload_many(self, records: Sequence[MemoryRecord]) -> int:
        if not records:
            return 0
        documents = [memory_to_search_document(item) for item in records]
        results = self.client.upload_documents(documents)
        if len(results) != len(documents) or not all(_indexing_succeeded(item) for item in results):
            raise RetrievalBackendError("Azure AI Search batch indexing did not fully succeed")
        return len(documents)

    def remove(self, memory_id: str) -> bool:
        results = self.client.delete_documents([{"id": memory_id}])
        if not results:
            return False
        if not all(_indexing_succeeded(item) for item in results):
            raise RetrievalBackendError(f"Azure AI Search failed to delete memory {memory_id}")
        return True

    def search(self, step: RetrievalStep) -> list[BackendHit]:
        search_text = step.query_text.strip() or "*"
        try:
            raw_results = list(
                self.client.search(
                    search_text,
                    filter=build_azure_search_filter(step),
                    search_fields=list(self.config.search_fields),
                    select=["record_json"],
                    top=step.limit,
                )
            )
        except Exception as exc:
            raise RetrievalBackendError(f"Azure AI Search query failed: {exc}") from exc

        parsed: list[tuple[MemoryRecord, float]] = []
        for item in raw_results:
            payload = item.get("record_json")
            if not isinstance(payload, str):
                raise RetrievalBackendError("Azure AI Search hit is missing record_json")
            try:
                record = MemoryRecord.model_validate_json(payload)
            except Exception as exc:
                raise RetrievalBackendError(
                    "Azure AI Search returned an invalid memory record"
                ) from exc
            if not record.visible_to(step.tenant_id) or record.expired_at(step.at):
                continue
            score = item.get("@search.score", 0.0)
            parsed.append((record, float(score or 0.0)))

        max_score = max((score for _record, score in parsed), default=0.0)
        hits: list[BackendHit] = []
        for rank, (record, score) in enumerate(parsed[: step.limit], start=1):
            normalized = score / max_score if max_score > 0.0 else 0.0
            hits.append(
                BackendHit(
                    record=record,
                    strategy=self.strategy,
                    score=min(1.0, max(0.0, normalized)),
                    rank=rank,
                    reasons=["Azure AI Search lexical match"],
                )
            )
        return hits
