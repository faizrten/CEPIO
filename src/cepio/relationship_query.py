"""Host-local, fail-closed relationship paging over the existing SQLite repository.

Not registered with REST, SDK or MCP. Binding writers and identity/grant callbacks
belong to trusted host composition, never tool arguments or ordinary object writes.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import CEPIOApplicationService, ExecutionContext
from .model import ObjectRef, OntologyObject
from .policy import RolePolicyEngine
from .repositories import SQLiteRepository
from .runtime import AuthorizationError


class RelationshipQueryUnavailable(RuntimeError):
    """Unsupported or invalidated host-local query; contains no graph details."""


class RelationshipPageQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    asset_id: str = Field(min_length=1, max_length=512)
    direction: Literal["out", "in"] = "out"
    limit: int = Field(default=25, ge=1, le=50)
    cursor: str | None = Field(default=None, max_length=128)


class RelationshipVisibility(BaseModel):
    """Explicit grants resolved by host policy, not declarations from a caller."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    relationship_types: frozenset[str]
    classifications: frozenset[str]
    source_uses: frozenset[str]
    policy_version: str = Field(min_length=1)


class RelationshipSourceAccess(BaseModel):
    """Current rights resolved by the host authority, never by a query caller.

    This is an adapter result, not a second sovereignty/consent registry. The
    resolver must authorize every source and its derivative ancestry for the fixed
    operational-inspection purpose using its current authorization clock.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    actor_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    actor_roles: frozenset[str]
    source_ids: frozenset[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        max_length=256
    )
    rights_version: str = Field(min_length=1)
    purpose: Literal["operational_inspection"] = "operational_inspection"
    expires_at: datetime


_SOURCE_SQL = """
AND EXISTS (SELECT 1 FROM relationship_object_sources x
  WHERE x.id=s.id AND x.version=s.version AND json_array_length(x.sources)>0
  AND NOT EXISTS (SELECT 1 FROM json_each(x.sources) q
    WHERE q.value NOT IN (SELECT value FROM json_each(:authorized_sources))))
AND EXISTS (SELECT 1 FROM relationship_object_sources x
  WHERE x.id=t.id AND x.version=t.version AND json_array_length(x.sources)>0
  AND NOT EXISTS (SELECT 1 FROM json_each(x.sources) q
    WHERE q.value NOT IN (SELECT value FROM json_each(:authorized_sources))))
AND EXISTS (SELECT 1 FROM relationship_edge_sources x
  WHERE x.id=r.id AND x.payload=r.payload AND json_array_length(x.sources)>0
  AND NOT EXISTS (SELECT 1 FROM json_each(x.sources) q
    WHERE q.value NOT IN (SELECT value FROM json_each(:authorized_sources))))
"""


class VisibleRelationship(BaseModel):
    model_config = ConfigDict(frozen=True)

    relationship_type: str
    direction: Literal["out", "in"]
    related: ObjectRef


class RelationshipPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: OntologyObject
    links: list[VisibleRelationship]
    related_objects: list[OntologyObject]
    next_cursor: str | None = None
    qualification: Literal["host_local_reference_only"] = "host_local_reference_only"


# All caller values are bound parameters. Both directions use the same indexed
# outgoing query by swapping the subject/neighbor aliases, never SQL identifiers.
_PAGE_SQL = """
SELECT r.id, r.type, s.payload AS subject, t.payload AS neighbor
FROM relationships r INDEXED BY idx_rel_page_source
JOIN relationship_visibility v ON v.id=r.id AND v.payload=r.payload
JOIN objects s ON s.id=r.source_id
JOIN objects t ON t.id=r.target_id
JOIN object_tenancy a ON a.id=s.id AND a.version=s.version
JOIN object_tenancy b ON b.id=t.id AND b.version=t.version
WHERE r.source_id=:asset AND r.id>:after
AND a.tenant=:tenant AND b.tenant=:tenant AND v.tenant=:tenant
AND s.type=json_extract(r.payload,'$.source.type')
AND t.type=json_extract(r.payload,'$.target.type')
AND r.source_id=json_extract(r.payload,'$.source.id')
AND r.target_id=json_extract(r.payload,'$.target.id')
AND r.type IN (SELECT value FROM json_each(:relations))
AND r.type=json_extract(r.payload,'$.type')
AND r.id=json_extract(r.payload,'$.id')
AND s.id=json_extract(s.payload,'$.id') AND t.id=json_extract(t.payload,'$.id')
AND s.type=json_extract(s.payload,'$.type') AND t.type=json_extract(t.payload,'$.type')
AND s.version=json_extract(s.payload,'$.version') AND t.version=json_extract(t.payload,'$.version')
AND v.classification IN (SELECT value FROM json_each(:classifications))
AND v.source_use IN (SELECT value FROM json_each(:uses))
AND (s.type IN (SELECT value FROM json_each(:types)) OR :all_types)
AND (t.type IN (SELECT value FROM json_each(:types)) OR :all_types)
AND (
  COALESCE(json_type(s.payload,'$.properties.sharingScope'),
           json_type(s.payload,'$.properties.sharing_scope'),'null')='null'
  OR :all_scopes
  OR EXISTS (SELECT 1 FROM json_each(CASE
    WHEN COALESCE(json_type(s.payload,'$.properties.sharingScope'),
                 json_type(s.payload,'$.properties.sharing_scope'))='array'
    THEN COALESCE(json_extract(s.payload,'$.properties.sharingScope'),
                  json_extract(s.payload,'$.properties.sharing_scope'))
    ELSE json_array(COALESCE(json_extract(s.payload,'$.properties.sharingScope'),
                             json_extract(s.payload,'$.properties.sharing_scope'))) END) q
    WHERE CAST(q.value AS TEXT) IN (SELECT value FROM json_each(:scopes)))
)
AND (
  COALESCE(json_type(t.payload,'$.properties.sharingScope'),
           json_type(t.payload,'$.properties.sharing_scope'),'null')='null'
  OR :all_scopes
  OR EXISTS (SELECT 1 FROM json_each(CASE
    WHEN COALESCE(json_type(t.payload,'$.properties.sharingScope'),
                 json_type(t.payload,'$.properties.sharing_scope'))='array'
    THEN COALESCE(json_extract(t.payload,'$.properties.sharingScope'),
                  json_extract(t.payload,'$.properties.sharing_scope'))
    ELSE json_array(COALESCE(json_extract(t.payload,'$.properties.sharingScope'),
                             json_extract(t.payload,'$.properties.sharing_scope'))) END) q
    WHERE CAST(q.value AS TEXT) IN (SELECT value FROM json_each(:scopes)))
)
ORDER BY r.id LIMIT :limit
"""
_IN_PAGE_SQL = (
    _PAGE_SQL.replace("idx_rel_page_source", "idx_rel_page_target")
    .replace("s.id=r.source_id", "s.id=r.target_id")
    .replace("t.id=r.target_id", "t.id=r.source_id")
    .replace("r.source_id=:asset", "r.target_id=:asset")
    .replace(
        "s.type=json_extract(r.payload,'$.source.type')",
        "s.type=json_extract(r.payload,'$.target.type')",
    )
    .replace(
        "t.type=json_extract(r.payload,'$.target.type')",
        "t.type=json_extract(r.payload,'$.source.type')",
    )
)


class SQLiteRelationshipPageAdapter:
    """Additive adapter: existing SQLite objects/relationships, no graph copy.

    Legacy rows have no host security bindings and are invisible. Object mutation
    revokes its tenant binding until explicitly rebound by the trusted importer.
    Relationship mutation similarly invalidates the exact-payload binding.
    """

    def __init__(self, repository: SQLiteRepository) -> None:
        if not isinstance(repository, SQLiteRepository):
            raise RelationshipQueryUnavailable("Relationship paging is unavailable")
        self.repository = repository
        self.last_vm_steps = 0
        with repository._lock:
            repository._conn.executescript("""
            CREATE TABLE IF NOT EXISTS object_tenancy (
              id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS relationship_visibility (
              id TEXT PRIMARY KEY, payload TEXT NOT NULL, tenant TEXT NOT NULL,
              classification TEXT NOT NULL, source_use TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS relationship_query_revision (
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL);
            INSERT OR IGNORE INTO relationship_query_revision VALUES(1,0);
            CREATE INDEX IF NOT EXISTS idx_rel_page_source ON relationships(source_id,id);
            CREATE INDEX IF NOT EXISTS idx_rel_page_target ON relationships(target_id,id);
            CREATE TRIGGER IF NOT EXISTS rq_object_revoke_update AFTER UPDATE ON objects
              BEGIN DELETE FROM object_tenancy WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_revoke_delete AFTER DELETE ON objects
              BEGIN DELETE FROM object_tenancy WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationship_revoke_update AFTER UPDATE ON relationships
              BEGIN DELETE FROM relationship_visibility WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationship_revoke_delete AFTER DELETE ON relationships
              BEGIN DELETE FROM relationship_visibility WHERE id=OLD.id; END;
            """)
            repository._conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS rq_objects_INSERT AFTER INSERT ON objects
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_objects_UPDATE AFTER UPDATE ON objects
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_objects_DELETE AFTER DELETE ON objects
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationships_INSERT AFTER INSERT ON relationships
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationships_UPDATE AFTER UPDATE ON relationships
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationships_DELETE AFTER DELETE ON relationships
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_tenancy_INSERT AFTER INSERT ON object_tenancy
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_tenancy_UPDATE AFTER UPDATE ON object_tenancy
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_tenancy_DELETE AFTER DELETE ON object_tenancy
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationship_visibility_INSERT AFTER INSERT ON relationship_visibility
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationship_visibility_UPDATE AFTER UPDATE ON relationship_visibility
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_relationship_visibility_DELETE AFTER DELETE ON relationship_visibility
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            """)
            repository._conn.commit()

            repository._conn.executescript("""
            CREATE TABLE IF NOT EXISTS relationship_object_sources (
              id TEXT PRIMARY KEY, version INTEGER NOT NULL, sources TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS relationship_edge_sources (
              id TEXT PRIMARY KEY, payload TEXT NOT NULL, sources TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS rq_sources_object_update AFTER UPDATE ON objects
              BEGIN DELETE FROM relationship_object_sources WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_sources_object_delete AFTER DELETE ON objects
              BEGIN DELETE FROM relationship_object_sources WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_sources_edge_update AFTER UPDATE ON relationships
              BEGIN DELETE FROM relationship_edge_sources WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_sources_edge_delete AFTER DELETE ON relationships
              BEGIN DELETE FROM relationship_edge_sources WHERE id=OLD.id; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_sources_insert AFTER INSERT ON relationship_object_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_sources_update AFTER UPDATE ON relationship_object_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_object_sources_delete AFTER DELETE ON relationship_object_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_edge_sources_insert AFTER INSERT ON relationship_edge_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_edge_sources_update AFTER UPDATE ON relationship_edge_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            CREATE TRIGGER IF NOT EXISTS rq_edge_sources_delete AFTER DELETE ON relationship_edge_sources
              BEGIN UPDATE relationship_query_revision SET revision=revision+1 WHERE singleton=1; END;
            """)

    @staticmethod
    def _sources(source_ids: frozenset[str]) -> str:
        if (
            type(source_ids) is not frozenset
            or not 1 <= len(source_ids) <= 32
            or any(
                type(value) is not str or not value.strip() or len(value) > 512
                for value in source_ids
            )
        ):
            raise ValueError("Explicit bounded source references are required")
        return json.dumps(sorted(source_ids))

    def bind_object_sources(self, object_id: str, source_ids: frozenset[str]) -> None:
        """Trusted importer declares ALL contributing sources, not permissions."""
        sources = self._sources(source_ids)
        with self.repository._lock:
            obj = self.repository.get_object(object_id)
            if obj is None or obj.id != object_id:
                raise ValueError("Cannot bind missing object")
            self.repository._conn.execute(
                "INSERT OR REPLACE INTO relationship_object_sources VALUES(?,?,?)",
                (obj.id, obj.version, sources),
            )
            self.repository._conn.commit()

    def bind_relationship_sources(self, relationship_id: str, source_ids: frozenset[str]) -> None:
        sources = self._sources(source_ids)
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT payload FROM relationships WHERE id=?", (relationship_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Cannot bind missing relationship")
            self.repository._conn.execute(
                "INSERT OR REPLACE INTO relationship_edge_sources VALUES(?,?,?)",
                (relationship_id, row["payload"], sources),
            )
            self.repository._conn.commit()

    def bind_object(self, object_id: str, *, tenant_id: str) -> None:
        """Trusted importer only; not exposed through runtime or tool contracts."""
        if not tenant_id:
            raise ValueError("A tenant binding is required")
        with self.repository._lock:
            obj = self.repository.get_object(object_id)
            if obj is None:
                raise ValueError("Cannot bind missing object")
            self.repository._conn.execute(
                "INSERT OR REPLACE INTO object_tenancy(id,version,tenant) VALUES(?,?,?)",
                (obj.id, obj.version, tenant_id),
            )
            self.repository._conn.commit()

    def bind_relationship(
        self, relationship_id: str, *, tenant_id: str, classification: str, source_use: str
    ) -> None:
        if not all((tenant_id, classification, source_use)):
            raise ValueError("Explicit relationship security binding is required")
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT payload FROM relationships WHERE id=?", (relationship_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Cannot bind missing relationship")
            self.repository._conn.execute(
                "INSERT OR REPLACE INTO relationship_visibility "
                "(id,payload,tenant,classification,source_use) VALUES(?,?,?,?,?)",
                (relationship_id, row["payload"], tenant_id, classification, source_use),
            )
            self.repository._conn.commit()

    def revision(self) -> tuple[int, int]:
        conn = self.repository._conn
        return (
            conn.execute("SELECT revision FROM relationship_query_revision").fetchone()[0],
            conn.execute("PRAGMA data_version").fetchone()[0],
        )

    def page(self, parameters: dict, direction: str) -> list[sqlite3.Row]:
        """Bound materialization and SQLite VM work, including denied neighbors."""
        self.last_vm_steps = 0

        def progress() -> int:
            self.last_vm_steps += 100
            return int(self.last_vm_steps >= 200_000)

        conn = self.repository._conn
        conn.set_progress_handler(progress, 100)
        try:
            sql = _PAGE_SQL if direction == "out" else _IN_PAGE_SQL
            if "authorized_sources" in parameters:
                sql = sql.replace("ORDER BY r.id", _SOURCE_SQL + "\nORDER BY r.id")
            return conn.execute(sql, parameters).fetchall()
        except sqlite3.OperationalError as exc:
            raise RelationshipQueryUnavailable("Relationship paging is unavailable") from exc
        finally:
            conn.set_progress_handler(None, 0)


class HostRelationshipReader:
    """Host creates this reader with authenticated identity and grant resolvers.

    Python callers holding host composition authority are trusted. This is not an
    authentication mechanism and must not be reconstructed from a tool payload.
    """

    def __init__(
        self,
        service: CEPIOApplicationService,
        adapter: SQLiteRelationshipPageAdapter,
        identity: Callable[[], ExecutionContext],
        visibility: Callable[[ExecutionContext], RelationshipVisibility],
        *,
        source_access: Callable[[ExecutionContext], RelationshipSourceAccess] | None = None,
    ) -> None:
        if service.runtime.object_repository is not adapter.repository:
            raise RelationshipQueryUnavailable("Relationship paging is unavailable")
        self.service, self.adapter = service, adapter
        self._identity, self._visibility = identity, visibility
        self._source_access = source_access
        self._cursors: OrderedDict[str, tuple[float, str, tuple[int, int], str]] = OrderedDict()

    def read(self, query: RelationshipPageQuery) -> RelationshipPage:
        context = self._identity()
        if type(context) is not ExecutionContext or not context.actor_id or not context.tenant_id:
            raise AuthorizationError("Authenticated actor and tenant are required")
        grants = self._visibility(context)
        access = None
        if self._source_access is not None:
            # Revalidate even frozen/model_copy objects from the trusted adapter.
            access = RelationshipSourceAccess.model_validate(
                self._source_access(context).model_dump()
            )
            if (
                access.actor_id != context.actor_id
                or access.tenant_id != context.tenant_id
                or access.actor_roles != context.actor_roles
                or access.expires_at.tzinfo is None
                or access.expires_at.utcoffset() is None
                or datetime.now(timezone.utc) >= access.expires_at
            ):
                raise AuthorizationError("Source access is unavailable")
        policy = self.service.runtime.policy_engine
        # Arbitrary policy engines cannot safely be translated into SQL here.
        if type(policy) is not RolePolicyEngine:
            raise RelationshipQueryUnavailable("Relationship paging is unavailable")
        # Freeze the policy evaluation snapshot for this single page. Host policy
        # replacement between calls is reflected in the continuation fingerprint.
        policy = deepcopy(policy)
        roles = set(context.actor_roles)
        types, scopes = set(), set()
        for role in roles:
            rule = policy.policies.get(role, {})
            types.update(rule.get("read_types", []))
            scopes.update(rule.get("read_scopes", []))
        if not policy.policies:
            types.add("*")
        registry = policy.type_registry
        if registry:
            candidates = registry.object_type_ids | set(registry.type_aliases)
            types.update(t for t in candidates if policy.can_read_type(roles, t))
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "actor": context.actor_id,
                    "roles": sorted(roles),
                    "tenant": context.tenant_id,
                    "query": query.model_dump(exclude={"cursor"}),
                    "grants": grants.model_dump(mode="json"),
                    "policy": policy.policies,
                    "types": sorted(types),
                    "scopes": sorted(scopes),
                    "registry": asdict(registry) if registry else None,
                    "source_access": access.model_dump(mode="json") if access else None,
                },
                sort_keys=True,
                default=lambda v: sorted(v),
            ).encode()
        ).hexdigest()
        repo = self.adapter.repository
        with repo._lock:
            repo._conn.execute("BEGIN")
            try:
                revision = self.adapter.revision()
                after = ""
                if query.cursor is not None:
                    state = self._cursors.get(query.cursor)
                    if (
                        state is None
                        or time.monotonic() - state[0] > 600
                        or state[1:3] != (fingerprint, revision)
                    ):
                        raise RelationshipQueryUnavailable("Invalid or stale relationship cursor")
                    after = state[3]
                subject = repo.get_object(query.asset_id)
                bound = repo._conn.execute(
                    "SELECT 1 FROM object_tenancy WHERE id=? AND version=? AND tenant=?",
                    (query.asset_id, subject.version if subject else -1, context.tenant_id),
                ).fetchone()
                if (
                    subject is None
                    or subject.id != query.asset_id
                    or not bound
                    or not policy.can_read_object(roles, subject)
                ):
                    raise AuthorizationError("Object is unavailable")
                if access is not None:
                    source_row = repo._conn.execute(
                        "SELECT sources FROM relationship_object_sources WHERE id=? AND version=?",
                        (query.asset_id, subject.version),
                    ).fetchone()
                    if (
                        source_row is None
                        or not json.loads(source_row["sources"])
                        or not set(json.loads(source_row["sources"])).issubset(access.source_ids)
                    ):
                        raise AuthorizationError("Object is unavailable")
                parameters = (
                    {"authorized_sources": json.dumps(sorted(access.source_ids))} if access else {}
                )
                rows = self.adapter.page(
                    {
                        **parameters,
                        "asset": query.asset_id,
                        "tenant": context.tenant_id,
                        "after": after,
                        "relations": json.dumps(sorted(grants.relationship_types)),
                        "classifications": json.dumps(sorted(grants.classifications)),
                        "uses": json.dumps(sorted(grants.source_uses)),
                        "types": json.dumps(sorted(types)),
                        "all_types": "*" in types,
                        "scopes": json.dumps(sorted(scopes)),
                        "all_scopes": "*" in scopes,
                        "limit": query.limit + 1,
                    },
                    query.direction,
                )
                links, neighbors = [], []
                for row in rows[: query.limit]:
                    neighbor = OntologyObject.model_validate_json(row["neighbor"])
                    if not policy.can_read_object(roles, neighbor):
                        raise RelationshipQueryUnavailable("Relationship paging is unavailable")
                    links.append(
                        VisibleRelationship(
                            relationship_type=row["type"],
                            direction=query.direction,
                            related=ObjectRef(id=neighbor.id, type=neighbor.type),
                        )
                    )
                    neighbors.append(policy.filter_properties(roles, neighbor))
                token = None
                # Rights may expire during database work or property projection.
                if access is not None and datetime.now(timezone.utc) >= access.expires_at:
                    raise AuthorizationError("Source access is unavailable")
                if len(rows) > query.limit:
                    token = secrets.token_urlsafe(32)
                    self._cursors[token] = (
                        time.monotonic(),
                        fingerprint,
                        revision,
                        rows[query.limit - 1]["id"],
                    )
                    while len(self._cursors) > 1024:
                        self._cursors.popitem(last=False)
                return RelationshipPage(
                    subject=policy.filter_properties(roles, subject),
                    links=links,
                    related_objects=neighbors,
                    next_cursor=token,
                )
            finally:
                repo._conn.rollback()
