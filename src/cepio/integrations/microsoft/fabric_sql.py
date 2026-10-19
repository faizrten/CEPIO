"""Microsoft Fabric SQL transport for provider-neutral CEPIO evidence bindings.

This module deliberately owns only transport/configuration concerns. Domain semantics stay
in CEPIO Industry IQ and provider-neutral binding modules.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator


FabricSqlAuthentication = Literal[
    "ActiveDirectoryDefault",
    "ActiveDirectoryMSI",
    "ActiveDirectoryInteractive",
    "ActiveDirectoryDeviceCode",
]

_PROOF_SELECT_STATEMENTS = {
    "cepio_drilling_npt_context": (
        "SELECT * FROM [cepio_proof].[cepio_drilling_npt_context] WHERE [context_id] = ?"
    ),
    "cepio_drilling_activity_interval": (
        "SELECT * FROM [cepio_proof].[cepio_drilling_activity_interval] WHERE [context_id] = ?"
    ),
    "cepio_drilling_activity_classification": (
        "SELECT * FROM [cepio_proof].[cepio_drilling_activity_classification] "
        "WHERE [context_id] = ?"
    ),
}


class FabricSqlConfigurationError(RuntimeError):
    """Raised when live Fabric SQL configuration is missing or unsafe."""


class FabricSqlSettings(BaseModel):
    """Secretless connection settings for a Fabric SQL analytics/Warehouse endpoint."""

    model_config = ConfigDict(frozen=True)

    server: str
    database: str
    authentication: FabricSqlAuthentication = "ActiveDirectoryDefault"
    connection_timeout_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def validate_connection_identity(self) -> "FabricSqlSettings":
        if not self.server.strip() or ";" in self.server:
            raise ValueError("Fabric SQL server must be non-empty and must not contain ';'")
        if not self.database.strip() or ";" in self.database:
            raise ValueError("Fabric SQL database must be non-empty and must not contain ';'")
        return self

    @classmethod
    def from_env(cls) -> "FabricSqlSettings":
        server = os.getenv("CEPIO_FABRIC_SQL_SERVER", "").strip()
        database = os.getenv("CEPIO_FABRIC_SQL_DATABASE", "").strip()
        missing = [
            name
            for name, value in (
                ("CEPIO_FABRIC_SQL_SERVER", server),
                ("CEPIO_FABRIC_SQL_DATABASE", database),
            )
            if not value
        ]
        if missing:
            raise FabricSqlConfigurationError(
                "Live Fabric proof is not configured; missing " + ", ".join(missing)
            )

        raw_timeout = os.getenv("CEPIO_FABRIC_SQL_CONNECTION_TIMEOUT", "30")
        try:
            timeout = int(raw_timeout)
        except ValueError as exc:
            raise FabricSqlConfigurationError(
                "CEPIO_FABRIC_SQL_CONNECTION_TIMEOUT must be an integer"
            ) from exc

        return cls(
            server=server,
            database=database,
            authentication=cast(
                FabricSqlAuthentication,
                os.getenv("CEPIO_FABRIC_SQL_AUTH", "ActiveDirectoryDefault").strip(),
            ),
            connection_timeout_seconds=timeout,
        )

    @property
    def connection_string(self) -> str:
        """Return a secretless Microsoft Entra connection string."""

        return (
            f"Server={self.server};"
            f"Database={self.database};"
            f"Authentication={self.authentication};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            f"Connection Timeout={self.connection_timeout_seconds};"
        )


class _Cursor(Protocol):
    description: Sequence[Sequence[Any]] | None

    def execute(self, statement: str, parameters: Sequence[object]) -> Any: ...

    def fetchall(self) -> Sequence[Sequence[Any]]: ...

    def close(self) -> None: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...

    def close(self) -> None: ...


ConnectFactory = Callable[[str], _Connection]


def _mssql_connect(connection_string: str) -> _Connection:
    try:
        import mssql_python
    except ImportError as exc:
        raise FabricSqlConfigurationError(
            "Live Fabric SQL transport requires the optional 'fabric-sql' dependency: "
            "python -m pip install -e '.[fabric-sql]'"
        ) from exc
    return cast(_Connection, mssql_python.connect(connection_string))


class FabricSqlTableReader:
    """Read allow-listed CEPIO proof tables through Fabric SQL.

    v0.1 deliberately maps only fixed, reviewed proof-table names to fixed SQL statements.
    The only runtime value passed to SQL is the parameterized ``context_id``. The reader
    exposes no mutation method.
    """

    def __init__(
        self,
        settings: FabricSqlSettings,
        *,
        allowed_tables: Iterable[str],
        connect: ConnectFactory | None = None,
    ) -> None:
        allowed = frozenset(allowed_tables)
        if not allowed:
            raise ValueError("Fabric SQL reader requires at least one allowed table")
        unsupported = sorted(allowed.difference(_PROOF_SELECT_STATEMENTS))
        if unsupported:
            raise ValueError(f"Fabric SQL table is not a supported proof table: {unsupported}")
        self.settings = settings
        self.allowed_tables = allowed
        self._connect = connect or _mssql_connect

    def read_rows(self, table_name: str, *, context_id: str) -> list[dict[str, Any]]:
        if table_name not in self.allowed_tables:
            raise ValueError(f"Fabric SQL table is not allow-listed: {table_name!r}")
        if not context_id.strip():
            raise ValueError("context_id must be non-empty")

        statement = _PROOF_SELECT_STATEMENTS[table_name]
        connection = self._connect(self.settings.connection_string)
        cursor = connection.cursor()
        try:
            cursor.execute(statement, (context_id,))
            if cursor.description is None:
                raise RuntimeError(
                    f"Fabric SQL query returned no result metadata for {table_name!r}"
                )
            columns = [str(column[0]) for column in cursor.description]
            return [
                {column: value for column, value in zip(columns, row, strict=True)}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()
