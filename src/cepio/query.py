from __future__ import annotations

import base64
import hashlib
import json
import time
from datetime import datetime
from enum import Enum
from functools import cmp_to_key
from typing import TYPE_CHECKING, Any, Iterable, Literal

from pydantic import BaseModel, Field, model_validator

from .model import OntologyObject, Relationship
from .query_backend import sqlite_query_backend

if TYPE_CHECKING:
    from .runtime import CEPIORuntime


_BUILTIN_FIELDS = {"id", "type", "name", "version", "created_at", "updated_at"}


class QueryOperator(str, Enum):
    eq = "eq"
    ne = "ne"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    in_ = "in"
    contains = "contains"
    exists = "exists"


class PropertyPredicate(BaseModel):
    property: str
    operator: QueryOperator = QueryOperator.eq
    value: Any | None = None

    @model_validator(mode="after")
    def validate_value(self) -> "PropertyPredicate":
        if self.operator == QueryOperator.in_ and not isinstance(self.value, (list, tuple, set)):
            raise ValueError("'in' predicate requires an array-like value")
        if self.operator == QueryOperator.exists and self.value is not None and not isinstance(self.value, bool):
            raise ValueError("'exists' predicate value must be boolean when supplied")
        return self


class RelationshipPredicate(BaseModel):
    relationship_type: str | None = None
    direction: Literal["out", "in"] = "out"
    other_id: str | None = None
    other_type: str | None = None

    @model_validator(mode="after")
    def require_constraint(self) -> "RelationshipPredicate":
        if not any((self.relationship_type, self.other_id, self.other_type)):
            raise ValueError("Relationship predicate requires relationship_type, other_id, or other_type")
        return self


class SortField(BaseModel):
    field: str
    direction: Literal["asc", "desc"] = "asc"


class ObjectQuery(BaseModel):
    object_type: str | None = None
    include_subtypes: bool = True
    predicates: list[PropertyPredicate] = Field(default_factory=list)
    relationships: list[RelationshipPredicate] = Field(default_factory=list)
    valid_at: datetime | None = None
    as_of_transaction: datetime | None = None
    sort: list[SortField] = Field(default_factory=list)
    offset: int = Field(default=0, ge=0, description="Legacy compatibility pagination. Prefer cursor for API v1.")
    limit: int = Field(default=100, ge=1, le=1000)
    cursor: str | None = Field(default=None, description="Opaque continuation cursor returned by a previous query page.")
    include_total: bool = Field(default=True, description="When false, CEPIO may stop scanning after the requested page.")

    @model_validator(mode="after")
    def validate_pagination(self) -> "ObjectQuery":
        if self.cursor and self.offset:
            raise ValueError("cursor and offset pagination cannot be combined")
        return self


class ObjectQueryResult(BaseModel):
    items: list[OntologyObject]
    total: int | None
    offset: int
    limit: int
    next_cursor: str | None = None
    has_more: bool = False


class QueryBudget(BaseModel):
    max_page_size: int = 200
    max_property_predicates: int = 32
    max_relationship_predicates: int = 8
    max_candidate_rows: int = 10000
    max_execution_ms: int = 5000


class QueryBudgetExceeded(RuntimeError):
    code = "query_budget_exceeded"


class InvalidQueryCursor(ValueError):
    code = "invalid_query_cursor"


class _CursorState(BaseModel):
    fingerprint: str
    object_id: str


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


class QueryEngine:
    """Repository-neutral CEPIO object-set query evaluator.

    In-memory execution remains the semantic oracle. Current-state SQLite queries may
    push type/property/relationship filtering into SQL, but every candidate is still
    checked through CEPIO semantics and actor policy. Actor-scoped result ordering is
    finalized only after property filtering so a hidden property cannot influence an
    observable cursor/page order.
    """

    def __init__(self, runtime: "CEPIORuntime", *, budget: QueryBudget | None = None) -> None:
        self.runtime = runtime
        self.budget = budget or QueryBudget()

    def execute(self, query: ObjectQuery, *, actor_roles: set[str] | None = None) -> ObjectQueryResult:
        started = time.monotonic()
        self._enforce_static_budget(query)
        fingerprint = self._fingerprint(query)
        cursor_state = self._decode_cursor(query.cursor, fingerprint) if query.cursor else None

        backend = None if (query.valid_at is not None or query.as_of_transaction is not None) else sqlite_query_backend(self.runtime.object_repository)
        if backend is not None:
            candidates: Iterable[OntologyObject] = backend.iter_candidates(
                query,
                allowed_types=self._pushdown_types(query),
                property_keys=self._pushdown_property_keys(query),
            )
            # Anonymous/internal queries can trust backend ordering. Actor-scoped queries
            # are re-sorted after property filtering to avoid hidden-property ordering leaks.
            presorted = actor_roles is None
        else:
            candidates = self._candidate_objects(query, actor_roles)
            presorted = False

        if not presorted:
            materialized: list[OntologyObject] = []
            scanned = 0
            for raw in candidates:
                scanned += 1
                self._enforce_dynamic_budget(scanned, started)
                if actor_roles is not None:
                    if not self.runtime.policy_engine.can_read_object(actor_roles, raw):
                        continue
                    obj = self.runtime.policy_engine.filter_properties(actor_roles, raw)
                else:
                    obj = raw
                if self._matches(obj, query, actor_roles):
                    materialized.append(obj)
            candidates = self._sort(materialized, query.sort)
            scanned = 0
        else:
            scanned = 0

        page: list[OntologyObject] = []
        authorized_total = 0
        page_position = 0
        after_cursor = cursor_state is None
        cursor_found = cursor_state is None
        has_more = False

        for raw in candidates:
            scanned += 1
            self._enforce_dynamic_budget(scanned, started)

            if presorted:
                if actor_roles is not None:
                    if not self.runtime.policy_engine.can_read_object(actor_roles, raw):
                        continue
                    obj = self.runtime.policy_engine.filter_properties(actor_roles, raw)
                else:
                    obj = raw
                if not self._matches(obj, query, actor_roles):
                    continue
            else:
                obj = raw

            authorized_total += 1

            if not after_cursor:
                assert cursor_state is not None
                if obj.id == cursor_state.object_id:
                    after_cursor = True
                    cursor_found = True
                continue

            page_position += 1
            if query.offset and page_position <= query.offset:
                continue
            if len(page) < query.limit:
                page.append(obj)
            else:
                has_more = True
                if not query.include_total:
                    break

        if not cursor_found:
            raise InvalidQueryCursor("Cursor no longer resolves within the authorized query result set")

        total: int | None = authorized_total if query.include_total else None
        next_cursor = self._encode_cursor(fingerprint, page[-1].id) if has_more and page else None

        return ObjectQueryResult(
            items=page,
            total=total,
            offset=query.offset,
            limit=query.limit,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _enforce_static_budget(self, query: ObjectQuery) -> None:
        if query.limit > self.budget.max_page_size:
            raise QueryBudgetExceeded(
                f"Requested page size {query.limit} exceeds maximum {self.budget.max_page_size}"
            )
        if len(query.predicates) > self.budget.max_property_predicates:
            raise QueryBudgetExceeded("Too many property predicates")
        if len(query.relationships) > self.budget.max_relationship_predicates:
            raise QueryBudgetExceeded("Relationship traversal budget exceeded")

    def _enforce_dynamic_budget(self, scanned: int, started: float) -> None:
        if scanned > self.budget.max_candidate_rows:
            raise QueryBudgetExceeded(
                f"Query candidate scan exceeded {self.budget.max_candidate_rows} rows"
            )
        elapsed_ms = (time.monotonic() - started) * 1000
        if elapsed_ms > self.budget.max_execution_ms:
            raise QueryBudgetExceeded(
                f"Query execution exceeded {self.budget.max_execution_ms} ms"
            )

    @staticmethod
    def _fingerprint(query: ObjectQuery) -> str:
        payload = query.model_dump(mode="json")
        for key in ("cursor", "offset", "limit", "include_total"):
            payload.pop(key, None)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _encode_cursor(fingerprint: str, object_id: str) -> str:
        payload = _CursorState(fingerprint=fingerprint, object_id=object_id).model_dump_json().encode("utf-8")
        return _b64encode(payload)

    @staticmethod
    def _decode_cursor(cursor: str, fingerprint: str) -> _CursorState:
        try:
            state = _CursorState.model_validate_json(_b64decode(cursor))
        except Exception as exc:
            raise InvalidQueryCursor("Malformed query cursor") from exc
        if state.fingerprint != fingerprint:
            raise InvalidQueryCursor("Cursor does not belong to this query contract")
        return state

    def _pushdown_types(self, query: ObjectQuery) -> set[str] | None:
        if not query.object_type:
            return None
        registry = self.runtime.type_registry
        if registry is None:
            return {query.object_type}

        expected = registry.resolve_type(query.object_type)
        canonical_types = {expected}
        if query.include_subtypes:
            for candidate in registry.object_type_ids:
                try:
                    if registry.is_a(candidate, expected):
                        canonical_types.add(candidate)
                except ValueError:
                    continue

        result: set[str] = set()
        for canonical in canonical_types:
            result.add(canonical)
            result.update(registry.aliases_for_type(canonical))
        result.add(query.object_type)
        return result

    def _pushdown_property_keys(self, query: ObjectQuery) -> dict[str, tuple[str, ...]]:
        names = {predicate.property for predicate in query.predicates}
        names.update(spec.field for spec in query.sort if spec.field not in _BUILTIN_FIELDS)
        result: dict[str, tuple[str, ...]] = {}
        registry = getattr(self.runtime, "property_registry", None)
        for name in names:
            keys: list[str] = [name]
            if registry is not None:
                try:
                    definition = registry.resolve(name)
                except (KeyError, ValueError):
                    definition = None
                if definition is not None:
                    for candidate in (definition.iri, definition.qname, definition.local_name):
                        if candidate and candidate not in keys:
                            keys.append(candidate)
            result[name] = tuple(keys)
        return result

    def _candidate_objects(self, query: ObjectQuery, actor_roles: set[str] | None) -> list[OntologyObject]:
        current = self.runtime.list_objects()
        result: list[OntologyObject] = []
        for obj in current:
            historical = self._object_in_context(obj.id, query)
            if historical is None:
                continue
            if actor_roles is not None and not self.runtime.policy_engine.can_read_object(actor_roles, historical):
                continue
            result.append(historical)
        return result

    def _object_in_context(self, object_id: str, query: ObjectQuery) -> OntologyObject | None:
        try:
            if query.valid_at is not None:
                method = getattr(self.runtime, "get_object_valid_at", None)
                if method is None:
                    raise RuntimeError("Configured CEPIO runtime does not support valid-time queries")
                return method(
                    object_id,
                    query.valid_at,
                    as_of_transaction=query.as_of_transaction,
                )
            if query.as_of_transaction is not None:
                method = getattr(self.runtime, "get_object_at", None)
                if method is None:
                    raise RuntimeError("Configured CEPIO runtime does not support transaction-time queries")
                return method(object_id, query.as_of_transaction)
            return self.runtime.get_object(object_id)
        except KeyError:
            return None

    def _matches(self, obj: OntologyObject, query: ObjectQuery, actor_roles: set[str] | None) -> bool:
        if query.object_type and not self._type_matches(obj.type, query.object_type, query.include_subtypes):
            return False
        if not all(self._matches_property(obj, predicate) for predicate in query.predicates):
            return False
        if not all(self._matches_relationship(obj, predicate, query, actor_roles) for predicate in query.relationships):
            return False
        return True

    def _type_matches(self, actual: str, expected: str, include_subtypes: bool) -> bool:
        registry = self.runtime.type_registry
        if registry is None:
            return actual == expected
        return registry.is_a(actual, expected) if include_subtypes else registry.same_type(actual, expected)

    def _property_value(self, obj: OntologyObject, name: str) -> tuple[bool, Any]:
        if name in _BUILTIN_FIELDS:
            return True, getattr(obj, name)
        if name in obj.properties:
            return True, obj.properties[name]

        registry = getattr(self.runtime, "property_registry", None)
        if registry is not None:
            try:
                definition = registry.resolve(name)
            except (KeyError, ValueError):
                definition = None
            if definition is not None:
                for candidate in (definition.iri, definition.qname, definition.local_name):
                    if candidate in obj.properties:
                        return True, obj.properties[candidate]
        return False, None

    def _matches_property(self, obj: OntologyObject, predicate: PropertyPredicate) -> bool:
        exists, actual = self._property_value(obj, predicate.property)
        operator = predicate.operator
        expected = predicate.value

        if operator == QueryOperator.exists:
            return exists if expected is not False else not exists
        if not exists:
            return False
        if operator == QueryOperator.eq:
            return actual == expected
        if operator == QueryOperator.ne:
            return actual != expected
        if operator == QueryOperator.gt:
            return actual > expected
        if operator == QueryOperator.gte:
            return actual >= expected
        if operator == QueryOperator.lt:
            return actual < expected
        if operator == QueryOperator.lte:
            return actual <= expected
        if operator == QueryOperator.in_:
            return actual in expected
        if operator == QueryOperator.contains:
            try:
                return expected in actual
            except TypeError:
                return False
        raise ValueError(f"Unsupported query operator: {operator}")

    def _relationships_for(self, obj: OntologyObject, predicate: RelationshipPredicate, query: ObjectQuery) -> list[Relationship]:
        if query.valid_at is not None or query.as_of_transaction is not None:
            method = getattr(self.runtime, "relationships_at", None)
            if method is None:
                raise RuntimeError("Configured CEPIO runtime does not support temporal relationship history")
            valid_time = query.valid_at or query.as_of_transaction
            assert valid_time is not None
            return method(
                obj.id,
                valid_time,
                direction=predicate.direction,
                as_of_transaction=query.as_of_transaction,
            )
        return self.runtime.object_repository.get_relationships(obj.id, direction=predicate.direction)

    def _relationship_type_matches(self, actual: str, expected: str) -> bool:
        registry = self.runtime.type_registry
        if registry is None:
            return actual == expected
        return registry.same_relationship(actual, expected)

    def _matches_relationship(
        self,
        obj: OntologyObject,
        predicate: RelationshipPredicate,
        query: ObjectQuery,
        actor_roles: set[str] | None,
    ) -> bool:
        for rel in self._relationships_for(obj, predicate, query):
            if predicate.relationship_type and not self._relationship_type_matches(rel.type, predicate.relationship_type):
                continue
            other_ref = rel.target if predicate.direction == "out" else rel.source
            other = self._object_in_context(other_ref.id, query)
            if other is None:
                continue
            if actor_roles is not None and not self.runtime.policy_engine.can_read_object(actor_roles, other):
                continue
            if predicate.other_id and other_ref.id != predicate.other_id:
                continue
            if predicate.other_type and not self._type_matches(other.type, predicate.other_type, include_subtypes=True):
                continue
            return True
        return False

    def _sort(self, objects: list[OntologyObject], fields: list[SortField]) -> list[OntologyObject]:
        def compare(left: OntologyObject, right: OntologyObject) -> int:
            for spec in fields:
                left_exists, left_value = self._property_value(left, spec.field)
                right_exists, right_value = self._property_value(right, spec.field)
                left_missing = not left_exists or left_value is None
                right_missing = not right_exists or right_value is None
                if left_missing != right_missing:
                    return 1 if left_missing else -1
                if left_missing:
                    continue
                try:
                    delta = (left_value > right_value) - (left_value < right_value)
                except TypeError:
                    left_key = (type(left_value).__name__, str(left_value))
                    right_key = (type(right_value).__name__, str(right_value))
                    delta = (left_key > right_key) - (left_key < right_key)
                if delta:
                    return -delta if spec.direction == "desc" else delta
            return (left.id > right.id) - (left.id < right.id)

        return sorted(objects, key=cmp_to_key(compare))
