from __future__ import annotations

import builtins
import sys
from types import SimpleNamespace

import pytest

from cepio.integrations.microsoft.fabric_sql import (
    FabricSqlConfigurationError,
    FabricSqlSettings,
    FabricSqlTableReader,
    _mssql_connect,
)


class FakeCursor:
    def __init__(self, *, with_description: bool = True) -> None:
        self.description = (
            (
                ("context_id",),
                ("activity_id",),
                ("is_productive",),
            )
            if with_description
            else None
        )
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False

    def execute(self, statement: str, parameters: tuple[object, ...]) -> None:
        self.executed.append((statement, parameters))

    def fetchall(self):
        return [
            ("NPT-CONTEXT-001", "ACT-NPT", False),
            ("NPT-CONTEXT-001", "ACT-PROD", True),
        ]

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


def _settings() -> FabricSqlSettings:
    return FabricSqlSettings(
        server="proof.datawarehouse.fabric.microsoft.com",
        database="CEPIOProof",
        authentication="ActiveDirectoryDefault",
    )


def test_settings_build_secretless_entra_connection_string():
    value = _settings().connection_string
    assert "Authentication=ActiveDirectoryDefault" in value
    assert "Encrypt=yes" in value
    assert "TrustServerCertificate=no" in value
    assert "PWD=" not in value
    assert "Password=" not in value


def test_settings_from_env_fails_closed_when_endpoint_is_missing(monkeypatch):
    monkeypatch.delenv("CEPIO_FABRIC_SQL_SERVER", raising=False)
    monkeypatch.delenv("CEPIO_FABRIC_SQL_DATABASE", raising=False)
    with pytest.raises(FabricSqlConfigurationError, match="CEPIO_FABRIC_SQL_SERVER"):
        FabricSqlSettings.from_env()


def test_settings_from_env_reads_secretless_entra_configuration(monkeypatch):
    monkeypatch.setenv("CEPIO_FABRIC_SQL_SERVER", "proof.datawarehouse.fabric.microsoft.com")
    monkeypatch.setenv("CEPIO_FABRIC_SQL_DATABASE", "CEPIOProof")
    monkeypatch.setenv("CEPIO_FABRIC_SQL_AUTH", "ActiveDirectoryMSI")
    monkeypatch.setenv("CEPIO_FABRIC_SQL_CONNECTION_TIMEOUT", "45")

    settings = FabricSqlSettings.from_env()

    assert settings.server == "proof.datawarehouse.fabric.microsoft.com"
    assert settings.database == "CEPIOProof"
    assert settings.authentication == "ActiveDirectoryMSI"
    assert settings.connection_timeout_seconds == 45


def test_settings_from_env_rejects_non_integer_timeout(monkeypatch):
    monkeypatch.setenv("CEPIO_FABRIC_SQL_SERVER", "proof.datawarehouse.fabric.microsoft.com")
    monkeypatch.setenv("CEPIO_FABRIC_SQL_DATABASE", "CEPIOProof")
    monkeypatch.setenv("CEPIO_FABRIC_SQL_CONNECTION_TIMEOUT", "not-an-integer")

    with pytest.raises(FabricSqlConfigurationError, match="must be an integer"):
        FabricSqlSettings.from_env()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("server", "", "server must be non-empty"),
        ("server", "safe;Server=evil", "server must be non-empty"),
        ("database", "", "database must be non-empty"),
        ("database", "safe;Database=evil", "database must be non-empty"),
    ],
)
def test_settings_reject_unsafe_connection_identity(field: str, value: str, message: str):
    values = {
        "server": "proof.datawarehouse.fabric.microsoft.com",
        "database": "CEPIOProof",
    }
    values[field] = value
    with pytest.raises(ValueError, match=message):
        FabricSqlSettings(**values)


def test_reader_uses_fixed_parameterized_select_and_closes_resources():
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    seen_connection_strings: list[str] = []

    def connect(connection_string: str) -> FakeConnection:
        seen_connection_strings.append(connection_string)
        return connection

    reader = FabricSqlTableReader(
        _settings(),
        allowed_tables={"cepio_drilling_activity_interval"},
        connect=connect,
    )
    rows = reader.read_rows(
        "cepio_drilling_activity_interval",
        context_id="NPT-CONTEXT-001",
    )

    assert rows == [
        {"context_id": "NPT-CONTEXT-001", "activity_id": "ACT-NPT", "is_productive": False},
        {"context_id": "NPT-CONTEXT-001", "activity_id": "ACT-PROD", "is_productive": True},
    ]
    assert seen_connection_strings == [_settings().connection_string]
    assert cursor.executed == [
        (
            "SELECT * FROM [cepio_proof].[cepio_drilling_activity_interval] "
            "WHERE [context_id] = ?",
            ("NPT-CONTEXT-001",),
        )
    ]
    assert cursor.closed is True
    assert connection.closed is True


def test_reader_requires_at_least_one_supported_table():
    with pytest.raises(ValueError, match="at least one"):
        FabricSqlTableReader(_settings(), allowed_tables=set())


def test_reader_rejects_unsupported_table_at_construction():
    with pytest.raises(ValueError, match="not a supported proof table"):
        FabricSqlTableReader(_settings(), allowed_tables={"customer_secret_table"})


def test_reader_rejects_non_allowlisted_table_before_connecting():
    calls = 0

    def connect(connection_string: str):
        nonlocal calls
        calls += 1
        raise AssertionError(connection_string)

    reader = FabricSqlTableReader(
        _settings(),
        allowed_tables={"cepio_drilling_npt_context"},
        connect=connect,
    )
    with pytest.raises(ValueError, match="not allow-listed"):
        reader.read_rows("cepio_drilling_activity_interval", context_id="NPT-CONTEXT-001")
    assert calls == 0


def test_reader_rejects_blank_context_before_connecting():
    calls = 0

    def connect(connection_string: str):
        nonlocal calls
        calls += 1
        raise AssertionError(connection_string)

    reader = FabricSqlTableReader(
        _settings(),
        allowed_tables={"cepio_drilling_npt_context"},
        connect=connect,
    )
    with pytest.raises(ValueError, match="context_id"):
        reader.read_rows("cepio_drilling_npt_context", context_id="   ")
    assert calls == 0


def test_reader_closes_resources_when_result_metadata_is_missing():
    cursor = FakeCursor(with_description=False)
    connection = FakeConnection(cursor)
    reader = FabricSqlTableReader(
        _settings(),
        allowed_tables={"cepio_drilling_npt_context"},
        connect=lambda _: connection,
    )

    with pytest.raises(RuntimeError, match="no result metadata"):
        reader.read_rows("cepio_drilling_npt_context", context_id="NPT-CONTEXT-001")

    assert cursor.closed is True
    assert connection.closed is True


def test_default_connector_fails_closed_when_optional_driver_is_missing(monkeypatch):
    real_import = builtins.__import__

    def import_without_driver(name, *args, **kwargs):
        if name == "mssql_python":
            raise ImportError("missing for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_driver)
    with pytest.raises(FabricSqlConfigurationError, match="fabric-sql"):
        _mssql_connect(_settings().connection_string)


def test_default_connector_delegates_to_optional_driver(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    seen: list[str] = []

    def connect(connection_string: str) -> FakeConnection:
        seen.append(connection_string)
        return connection

    monkeypatch.setitem(sys.modules, "mssql_python", SimpleNamespace(connect=connect))

    result = _mssql_connect(_settings().connection_string)

    assert result is connection
    assert seen == [_settings().connection_string]
