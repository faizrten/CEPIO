"""Fixed offline tenant partitions, never mounted by the production host."""

from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .application_contract import CEPIOApplicationService, ExecutionContext
from .relationship_qualification import (
    RelationshipQualificationBoundary,
    RelationshipQualificationUnavailable,
)
from .relationship_query import (
    RelationshipPage,
    RelationshipPageQuery,
    RelationshipSourceAccess,
    RelationshipVisibility,
    SQLiteRelationshipPageAdapter,
)


@dataclass(frozen=True)
class RelationshipQualificationPartition:
    """Host-owned existing repository and authorities, never caller parameters."""

    service: CEPIOApplicationService
    adapter: SQLiteRelationshipPageAdapter
    visibility: Callable[[ExecutionContext], RelationshipVisibility]
    source_access: Callable[[ExecutionContext], RelationshipSourceAccess]


class RelationshipQualificationPartitions:
    """Offline, statically allocated tenant bulkheads over existing repositories.

    No provisioning, replication, dynamic tenant creation or production routing.
    Separate SQLite files/connections prevent shared revision, lock and cursor
    state in this composition. CPU, disk and native memory still share a process.
    Trusted importers must keep each repository dedicated to its configured tenant.
    """

    def __init__(
        self,
        identity: Callable[[], ExecutionContext],
        partitions: Mapping[str, RelationshipQualificationPartition],
    ) -> None:
        if not 1 <= len(partitions) <= 16:
            raise ValueError("Configure one to sixteen dedicated tenant partitions")
        self._identity = identity
        self._context: ContextVar[ExecutionContext] = ContextVar("partition_qualification_actor")
        self._boundaries: dict[str, RelationshipQualificationBoundary] = {}
        connections: set[int] = set()
        files: list[Path] = []
        for tenant, partition in partitions.items():
            if type(tenant) is not str or not tenant.strip() or len(tenant) > 512:
                raise ValueError("Explicit bounded tenant identifiers are required")
            repo = partition.adapter.repository
            with repo._lock:
                # Read SQLite's opened path, not a caller's relative path alias.
                filename = repo._conn.execute("PRAGMA database_list").fetchone()[2]
                if id(repo._conn) in connections:
                    raise ValueError("Tenant partitions require separate repositories")
                connections.add(id(repo._conn))
                if filename:
                    path = Path(filename).resolve(strict=True)
                    if any(path.samefile(other) for other in files):
                        raise ValueError("Tenant partitions cannot share a database file")
                    files.append(path)
                if repo._conn.execute(
                    "SELECT 1 FROM object_tenancy WHERE tenant<>? "
                    "UNION ALL SELECT 1 FROM relationship_visibility WHERE tenant<>? LIMIT 1",
                    (tenant, tenant),
                ).fetchone():
                    raise ValueError("A partition contains foreign tenant bindings")
            self._boundaries[tenant] = RelationshipQualificationBoundary(
                partition.service,
                partition.adapter,
                self._context.get,
                partition.visibility,
                partition.source_access,
            )

    def read(self, query: RelationshipPageQuery | dict[str, Any]) -> RelationshipPage:
        try:
            context = self._identity()
            if type(context) is not ExecutionContext or context.tenant_id not in self._boundaries:
                raise RelationshipQualificationUnavailable()
            token = self._context.set(context)
            try:
                return self._boundaries[context.tenant_id].read(query)
            finally:
                self._context.reset(token)
        except Exception:
            raise RelationshipQualificationUnavailable() from None
