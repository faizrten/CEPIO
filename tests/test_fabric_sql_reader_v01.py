from __future__ import annotations

import pytest

from cepio.integrations.microsoft.fabric_sql import (
    FabricSqlConfigurationError,
    FabricSqlSettings,
    FabricSqlTableReader,
)


class FakeCursor:
    def __init__(self) -> None:
        self.description = (
            ("context_id",),
            ("activity_id",),
            ("is_productive",),
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
        schema_name="cepio_proof",
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


def test_reader_uses_allowlisted_parameterized_select_and_closes_resources():
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
        reader.read_rows("customer_secret_table", context_id="NPT-CONTEXT-001")
    assert calls == 0


def test_reader_rejects_unsafe_schema_or_table_identifiers():
    with pytest.raises(ValueError, match="schema_name"):
        FabricSqlSettings(
            server="proof.datawarehouse.fabric.microsoft.com",
            database="CEPIOProof",
            schema_name="dbo]; DROP TABLE x;--",
        )

    with pytest.raises(ValueError, match="simple identifiers"):
        FabricSqlTableReader(_settings(), allowed_tables={"x; DELETE FROM y"})
