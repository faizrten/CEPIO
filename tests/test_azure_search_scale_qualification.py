from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[1]


class HttpResponseError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


class ResourceNotFoundError(HttpResponseError):
    def __init__(self):
        super().__init__(404)


@pytest.fixture
def ensure_index(monkeypatch):
    modules = {
        "azure.core.exceptions": {
            "HttpResponseError": HttpResponseError,
            "ResourceNotFoundError": ResourceNotFoundError,
        },
        "azure.identity": {"DefaultAzureCredential": Mock()},
        "azure.search.documents": {"SearchClient": Mock()},
        "azure.search.documents.indexes": {"SearchIndexClient": Mock()},
        "azure.search.documents.indexes.models": {
            name: Mock()
            for name in (
                "SearchField",
                "SearchFieldDataType",
                "SearchIndex",
                "SearchableField",
                "SimpleField",
            )
        },
    }
    for name, attributes in modules.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    script = runpy.run_path(str(ROOT / "scripts" / "run_azure_search_scale_qualification.py"))
    return script["_ensure_index"]


@pytest.mark.parametrize("operation", ["delete_index", "create_or_update_index"])
def test_index_management_403_requires_administrator_repair(ensure_index, operation):
    client = Mock()
    error = HttpResponseError(403)
    getattr(client, operation).side_effect = error
    with pytest.raises(RuntimeError, match="administrator must provision") as raised:
        ensure_index(client, index_name="synthetic", reset=True)
    assert raised.value.__cause__ is error
    assert "Search Service Contributor" in str(raised.value)
    assert "Search Index Data Contributor" in str(raised.value)
    if operation == "delete_index":
        client.create_or_update_index.assert_not_called()


@pytest.mark.parametrize("status_code", [401, 429, 500])
def test_other_index_management_errors_propagate(ensure_index, status_code):
    client = Mock()
    error = HttpResponseError(status_code)
    client.delete_index.side_effect = error
    with pytest.raises(HttpResponseError) as raised:
        ensure_index(client, index_name="synthetic", reset=True)
    assert raised.value is error
    client.create_or_update_index.assert_not_called()


@pytest.mark.parametrize("reset", [False, True])
@pytest.mark.parametrize("missing", [False, True])
def test_index_management_success_and_missing_index(ensure_index, reset, missing):
    client = Mock()
    if missing:
        client.delete_index.side_effect = ResourceNotFoundError()
    ensure_index(client, index_name="synthetic", reset=reset)
    assert client.delete_index.call_count == int(reset)
    client.create_or_update_index.assert_called_once()
