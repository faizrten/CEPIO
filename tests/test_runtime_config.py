from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import cepio.api as api_module
from cepio import __version__
from cepio.bootstrap import build_runtime_from_settings
from cepio.config import RuntimeSettings
from cepio.resource_paths import resolve_resource_root


def test_production_requires_explicit_persistence(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.delenv("CEPIO_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="CEPIO_DB_URL is required"):
        RuntimeSettings.from_env()


def test_development_defaults_to_memory(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "development")
    monkeypatch.delenv("CEPIO_DB_URL", raising=False)
    settings = RuntimeSettings.from_env()
    assert settings.db_url == "memory://"
    assert settings.sqlite_path() is None


def test_invalid_persistence_fails_fast(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "production")
    monkeypatch.setenv("CEPIO_DB_URL", "postgresql://unsupported")
    settings = RuntimeSettings.from_env()
    with pytest.raises(RuntimeError, match="Unsupported CEPIO_DB_URL"):
        settings.sqlite_path()


@pytest.mark.parametrize("url", [
    "postgresql://migration-user:secret-password@private-host/db?token=secret-token",
    "postgres://migration-user:secret-password@private-host/db",
    "invalid://secret-token",
])
def test_unsupported_database_url_never_appears_in_error(monkeypatch, url):
    monkeypatch.setenv("CEPIO_DB_URL", url)
    settings = RuntimeSettings.from_env()
    with pytest.raises(RuntimeError, match="Unsupported CEPIO_DB_URL") as error:
        settings.sqlite_path()
    for secret in (url, "secret-password", "secret-token", "private-host", "migration-user"):
        assert secret not in str(error.value)


def test_resource_root_and_runtime_metadata_are_available(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_DB_URL", "memory://")
    root = resolve_resource_root()
    assert (root / "ontology-modules.yaml").exists()
    runtime = build_runtime_from_settings()
    assert runtime.module_catalogue.modules
    assert runtime.resource_root == root


def test_health_uses_single_package_version_and_catalogue_metadata(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_DB_URL", "memory://")
    api_module.runtime = build_runtime_from_settings()
    client = TestClient(api_module.app)
    payload = client.get("/health").json()
    assert payload["version"] == __version__
    assert payload["ontology_catalogue_schema"] is not None
    assert payload["ontology_modules"]
    assert payload["profiles"] == {}
