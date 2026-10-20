from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import ValidationError

from cepio.azure_search import (
    AzureSearchConfig,
    AzureSearchMemoryBackend,
    _indexing_succeeded,
    _search_in_expression,
    azure_search_index_schema,
    build_azure_search_filter,
    create_managed_identity_search_client,
    memory_to_search_document,
)
from cepio.memory import (
    MemoryKind,
    MemoryProvenance,
    MemoryRecord,
    MemoryReference,
    MemoryScope,
)
from cepio.retrieval_contracts import RetrievalBackendError, RetrievalStep, RetrievalStrategy


NOW = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)


def _record(
    memory_id: str = "m1",
    *,
    tenant_id: str | None = "tenant-a",
    scope: MemoryScope = MemoryScope.TENANT,
    expires_at: datetime | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind=MemoryKind.SEMANTIC,
        scope=scope,
        tenant_id=tenant_id,
        summary="compressor vibration condition evidence",
        provenance=MemoryProvenance(source_kind="synthetic"),
        reference=MemoryReference(
            source_system="fabric",
            resource_type="inspection",
            resource_id=memory_id,
        ),
        created_at=NOW - timedelta(days=1),
        expires_at=expires_at,
        capability_ids={"industrial.reliability.condition-work-context"},
        tags={"compressor", "condition"},
    )


class FakeSearchClient:
    def __init__(self) -> None:
        self.results: list[dict[str, object]] = []
        self.upload_results: list[object] = []
        self.delete_results: list[object] = []
        self.raise_search: Exception | None = None
        self.last_search: tuple[str, dict[str, object]] | None = None
        self.last_upload: list[dict[str, object]] = []
        self.last_delete: list[dict[str, object]] = []

    def search(self, search_text: str, **kwargs):
        if self.raise_search:
            raise self.raise_search
        self.last_search = (search_text, kwargs)
        return list(self.results)

    def upload_documents(self, documents):
        self.last_upload = list(documents)
        return list(self.upload_results)

    def delete_documents(self, documents):
        self.last_delete = list(documents)
        return list(self.delete_results)


def test_config_from_env_and_validation(monkeypatch):
    monkeypatch.setenv(
        "CEPIO_AZURE_SEARCH_ENDPOINT",
        "https://cepio-search-dev-31d48.search.windows.net/",
    )
    monkeypatch.setenv("CEPIO_AZURE_SEARCH_INDEX", "custom-index")
    config = AzureSearchConfig.from_env()
    assert config.endpoint == "https://cepio-search-dev-31d48.search.windows.net"
    assert config.index_name == "custom-index"

    monkeypatch.delenv("CEPIO_AZURE_SEARCH_INDEX")
    assert AzureSearchConfig.from_env().index_name == "cepio-memory-v1"

    monkeypatch.delenv("CEPIO_AZURE_SEARCH_ENDPOINT")
    with pytest.raises(RuntimeError):
        AzureSearchConfig.from_env()

    with pytest.raises(ValidationError):
        AzureSearchConfig(endpoint="http://search.local")
    with pytest.raises(ValidationError):
        AzureSearchConfig(endpoint="https://search.local/path")
    with pytest.raises(ValidationError):
        AzureSearchConfig(endpoint="https://search.local", index_name=" ")


def test_managed_identity_factory_requires_optional_dependencies(monkeypatch):
    import builtins

    original = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("azure."):
            raise ImportError("missing")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    config = AzureSearchConfig(endpoint="https://search.local")
    with pytest.raises(RuntimeError, match="optional 'azure-search'"):
        create_managed_identity_search_client(config)


def test_managed_identity_factory_builds_keyless_client(monkeypatch):
    azure = ModuleType("azure")
    azure.__path__ = []
    identity = ModuleType("azure.identity")
    search = ModuleType("azure.search")
    search.__path__ = []
    documents = ModuleType("azure.search.documents")
    captured: dict[str, object] = {}

    class FakeCredential:
        def __init__(self, **kwargs):
            captured["credential_kwargs"] = kwargs

    class FakeClient:
        def __init__(self, *, endpoint, index_name, credential):
            captured["endpoint"] = endpoint
            captured["index_name"] = index_name
            captured["credential"] = credential

    identity.DefaultAzureCredential = FakeCredential
    documents.SearchClient = FakeClient
    monkeypatch.setitem(sys.modules, "azure", azure)
    monkeypatch.setitem(sys.modules, "azure.identity", identity)
    monkeypatch.setitem(sys.modules, "azure.search", search)
    monkeypatch.setitem(sys.modules, "azure.search.documents", documents)

    client = create_managed_identity_search_client(
        AzureSearchConfig(endpoint="https://search.local", index_name="memory")
    )
    assert isinstance(client, FakeClient)
    assert captured["endpoint"] == "https://search.local"
    assert captured["index_name"] == "memory"
    assert captured["credential_kwargs"] == {"exclude_interactive_browser_credential": True}


def test_filter_and_document_projection():
    step = RetrievalStep(
        id="lexical",
        strategy=RetrievalStrategy.LEXICAL,
        query_text="compressor vibration",
        tenant_id="tenant'a",
        kinds={MemoryKind.SEMANTIC},
        tags={"compressor"},
        capability_ids={"cap-a", "cap-b"},
        limit=10,
        at=NOW,
    )
    value = build_azure_search_filter(step)
    assert "tenant''a" in value
    assert "scope eq 'GLOBAL'" in value
    assert "search.in(kind, 'SEMANTIC', '|')" in value
    assert "tags/any" in value
    assert "capability_ids/any" in value
    assert "expires_at gt 2026-10-20T10:00:00Z" in value

    global_step = step.model_copy(
        update={"tenant_id": None, "kinds": set(), "tags": set(), "capability_ids": set()}
    )
    global_filter = build_azure_search_filter(global_step)
    assert global_filter.startswith("scope eq 'GLOBAL'")
    assert "tags/any" not in global_filter
    assert "capability_ids/any" not in global_filter

    record = _record()
    document = memory_to_search_document(record)
    assert document["id"] == "m1"
    assert document["source_system"] == "fabric"
    assert document["capability_ids"] == ["industrial.reliability.condition-work-context"]
    assert document["expires_at"] is None

    expiring = _record("expiring", expires_at=NOW + timedelta(hours=1))
    assert memory_to_search_document(expiring)["expires_at"] is not None

    no_ref = record.model_copy(update={"reference": None})
    no_ref_doc = memory_to_search_document(no_ref)
    assert no_ref_doc["source_system"] is None
    assert no_ref_doc["resource_type"] is None


def test_search_in_fallback_and_empty():
    assert _search_in_expression("tags", set(), collection=True) is None
    normal = _search_in_expression("tags", {"a", "b"}, collection=True)
    assert normal == "tags/any(x: search.in(x, 'a|b', '|'))"
    fallback = _search_in_expression("tags", {"a|b", "c"}, collection=True)
    assert "x eq 'a|b'" in fallback
    scalar = _search_in_expression("kind", {"A|B", "C"}, collection=False)
    assert "kind eq 'A|B'" in scalar


def test_schema_is_stable():
    assert azure_search_index_schema()["name"] == "cepio-memory-v1"
    schema = azure_search_index_schema("custom")
    assert schema["name"] == "custom"
    fields = {item["name"]: item for item in schema["fields"]}
    assert fields["id"]["key"] is True
    assert fields["summary"]["searchable"] is True
    assert fields["capability_ids"]["filterable"] is True
    assert fields["record_json"]["retrievable"] is True


def test_indexing_result_shapes():
    assert _indexing_succeeded({"succeeded": True})
    assert _indexing_succeeded(SimpleNamespace(succeeded=True))
    assert not _indexing_succeeded({})
    assert not _indexing_succeeded(SimpleNamespace(succeeded=False))


def test_upsert_upload_many_and_remove():
    client = FakeSearchClient()
    config = AzureSearchConfig(endpoint="https://search.local")
    backend = AzureSearchMemoryBackend(client, config)
    record = _record()

    client.upload_results = [SimpleNamespace(succeeded=True)]
    backend.upsert(record)
    assert client.last_upload[0]["id"] == "m1"

    client.upload_results = [
        SimpleNamespace(succeeded=True),
        SimpleNamespace(succeeded=True),
    ]
    assert backend.upload_many([record, _record("m2")]) == 2
    assert backend.upload_many([]) == 0

    client.delete_results = [SimpleNamespace(succeeded=True)]
    assert backend.remove("m1") is True
    assert client.last_delete == [{"id": "m1"}]

    client.delete_results = []
    assert backend.remove("missing") is False

    client.upload_results = []
    with pytest.raises(RetrievalBackendError):
        backend.upsert(record)

    client.upload_results = [SimpleNamespace(succeeded=True)]
    with pytest.raises(RetrievalBackendError):
        backend.upload_many([record, _record("m2")])

    client.delete_results = [SimpleNamespace(succeeded=False)]
    with pytest.raises(RetrievalBackendError):
        backend.remove("m1")


def test_search_normalizes_scores_and_rechecks_boundary():
    client = FakeSearchClient()
    config = AzureSearchConfig(endpoint="https://search.local")
    backend = AzureSearchMemoryBackend(client, config)
    tenant = _record("tenant")
    global_record = _record("global", tenant_id=None, scope=MemoryScope.GLOBAL)
    foreign = _record("foreign", tenant_id="tenant-b")
    expired = _record("expired", expires_at=NOW - timedelta(hours=1))
    client.results = [
        {"record_json": tenant.model_dump_json(), "@search.score": 8.0},
        {"record_json": global_record.model_dump_json(), "@search.score": 4.0},
        {"record_json": foreign.model_dump_json(), "@search.score": 100.0},
        {"record_json": expired.model_dump_json(), "@search.score": 100.0},
    ]
    step = RetrievalStep(
        id="lexical",
        strategy=RetrievalStrategy.LEXICAL,
        query_text="compressor",
        tenant_id="tenant-a",
        limit=10,
        at=NOW,
    )
    hits = backend.search(step)
    assert [item.record.id for item in hits] == ["tenant", "global"]
    assert [item.score for item in hits] == [1.0, 0.5]
    assert client.last_search[0] == "compressor"
    assert client.last_search[1]["top"] == 10
    assert client.last_search[1]["select"] == ["record_json"]

    client.results = [{"record_json": tenant.model_dump_json(), "@search.score": None}]
    zero = backend.search(step)
    assert zero[0].score == 0.0

    star_step = step.model_copy(update={"query_text": ""})
    backend.search(star_step)
    assert client.last_search[0] == "*"


def test_search_failure_and_invalid_payloads():
    client = FakeSearchClient()
    config = AzureSearchConfig(endpoint="https://search.local")
    backend = AzureSearchMemoryBackend(client, config)
    step = RetrievalStep(
        id="lexical",
        strategy=RetrievalStrategy.LEXICAL,
        query_text="compressor",
        tenant_id="tenant-a",
        at=NOW,
    )

    client.raise_search = RuntimeError("boom")
    with pytest.raises(RetrievalBackendError, match="query failed"):
        backend.search(step)

    client.raise_search = None
    client.results = [{"@search.score": 1.0}]
    with pytest.raises(RetrievalBackendError, match="missing record_json"):
        backend.search(step)

    client.results = [{"record_json": "{bad json", "@search.score": 1.0}]
    with pytest.raises(RetrievalBackendError, match="invalid memory record"):
        backend.search(step)
