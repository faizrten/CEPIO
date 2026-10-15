from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

from .model import OntologyObject, Relationship

if TYPE_CHECKING:
    from .runtime import CEPIORuntime


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
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class ObjectQueryResult(BaseModel):
    items: list[OntologyObject]
    total: int
    offset: int
    limit: int


class QueryEngine:
    """Repository-neutral CEPIO object-set query evaluator.

    The reference engine keeps query semantics backend-neutral while enforcing actor
    visibility before predicates, result counts, sorting and pagination. Production
    repositories can push this contract down to SQL/KQL/Graph without changing
    application semantics.
    """

    def __init__(self, runtime: "CEPIORuntime") -> None:
        self.runtime = runtime

    def execute(self, query: ObjectQuery, *, actor_roles: set[str] | None = None) -> ObjectQueryResult:
        candidates = self._candidate_objects(query, actor_roles)
        if actor_roles is not None:
            candidates = [
                self.runtime.policy_engine.filter_properties(actor_roles, obj)
                for obj in candidates
            ]
        filtered = [obj for obj in candidates if self._matches(obj, query, actor_roles)]
        ordered = self._sort(filtered, query.sort)
        total = len(ordered)
        items = ordered[query.offset : query.offset + query.limit]
        return ObjectQueryResult(items=items, total=total, offset=query.offset, limit=query.limit)

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
        if name in {"id", "type", "name", "version", "created_at", "updated_at"}:
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
        ordered = sorted(objects, key=lambda obj: obj.id)
        for spec in reversed(fields):
            reverse = spec.direction == "desc"
            ordered.sort(key=lambda obj: self._sort_value(obj, spec.field), reverse=reverse)
        return ordered

    def _sort_value(self, obj: OntologyObject, field: str) -> tuple[int, str, Any]:
        exists, value = self._property_value(obj, field)
        if not exists or value is None:
            return (1, "", "")
        return (0, type(value).__name__, value)
