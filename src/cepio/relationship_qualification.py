"""Offline host/protocol qualification boundary; NOT mounted by the CEPIO host.

This adapter cannot qualify denied-fanout noninterference, a production repository,
or real source authority. Its inclusion never enables a remote endpoint.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import BoundedSemaphore, Lock
import time
from typing import Any

from .application_contract import CEPIOApplicationService, ExecutionContext
from .relationship_query import (
    HostRelationshipReader,
    RelationshipPage,
    RelationshipPageQuery,
    RelationshipSourceAccess,
    RelationshipVisibility,
    SQLiteRelationshipPageAdapter,
)


class RelationshipQualificationUnavailable(RuntimeError):
    """Uniform boundary error: never includes graph/source/cursor internals."""

    def __init__(self) -> None:
        super().__init__("Relationship query unavailable")


class RelationshipQualificationBoundary:
    """Qualify injected host identity and source-aware reads, with bounded load.

    Authenticate outside this adapter using the existing REST/MCP host contracts.
    The identity provider is request-local, never a shared mutable last-user slot.
    It must return the authenticated principal, not a query-selected identity.
    Fixed process-local admission limits are a defense, not a distributed limiter.
    """

    def __init__(
        self,
        service: CEPIOApplicationService,
        adapter: SQLiteRelationshipPageAdapter,
        identity: Callable[[], ExecutionContext],
        visibility: Callable[[ExecutionContext], RelationshipVisibility],
        source_access: Callable[[ExecutionContext], RelationshipSourceAccess],
    ) -> None:
        if not callable(source_access):
            raise ValueError("Current source authorization is required")
        self._identity = identity
        self._slots = BoundedSemaphore(4)
        self._lock = Lock()
        self._window = time.monotonic()
        self._counts: dict[tuple[str, str], int] = {}
        self._total = 0
        # Read captures one request-local context before entering the reader.
        from contextvars import ContextVar

        self._context: ContextVar[ExecutionContext] = ContextVar("relationship_qualification_actor")
        self._reader = HostRelationshipReader(service, adapter, self._context.get, visibility)
        self._reader.configure_source_access(source_access)

    def _admit(self, context: ExecutionContext) -> None:
        if (
            type(context) is not ExecutionContext
            or not context.actor_id
            or not context.tenant_id
            or not context.actor_roles
            or len(context.actor_id) > 512
            or len(context.tenant_id) > 512
            or len(context.actor_roles) > 32
            or any(len(role) > 128 for role in context.actor_roles)
        ):
            raise RelationshipQualificationUnavailable()
        key = (context.tenant_id, context.actor_id)
        with self._lock:
            now = time.monotonic()
            if now - self._window >= 60:
                self._counts.clear()
                self._total = 0
                self._window = now
            count = self._counts.get(key, 0)
            if self._total >= 120 or count >= 30:
                raise RelationshipQualificationUnavailable()
            self._counts[key] = count + 1
            self._total += 1

    def read(self, query: RelationshipPageQuery | dict[str, Any]) -> RelationshipPage:
        if not self._slots.acquire(blocking=False):
            raise RelationshipQualificationUnavailable()
        try:
            context = self._identity()
            self._admit(context)
            validated = RelationshipPageQuery.model_validate(
                query.model_dump() if isinstance(query, RelationshipPageQuery) else query
            )
            token = self._context.set(context)
            try:
                return self._reader.read(validated)
            finally:
                self._context.reset(token)
        except Exception:
            # Deliberately normalize host-resolver and repository errors. Neither
            # HTTP nor MCP qualification clients receive exception causes/details.
            raise RelationshipQualificationUnavailable() from None
        finally:
            self._slots.release()
