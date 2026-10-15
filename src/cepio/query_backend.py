from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .model import OntologyObject

if TYPE_CHECKING:
    from .query import ObjectQuery, PropertyPredicate, RelationshipPredicate, SortField
    from .repositories import SQLiteRepository


_BUILTIN_FIELDS = {"id", "type", "name", "version", "created_at", "updated_at"}


class SQLiteObjectQueryBackend:
    """SQL pushdown for current-state CEPIO object queries.

    Pushdown is intentionally conservative: it may admit extra candidates that the
    QueryEngine later rejects, but it must never remove a candidate that CEPIO's
    canonical semantic evaluator would accept. Actor visibility, property filtering,
    cursor validation, budgets and temporal semantics remain in QueryEngine.
    """

    def __init__(self, repository: "SQLiteRepository") -> None:
        self.repository = repository

    def iter_candidates(
        self,
        query: "ObjectQuery",
        *,
        allowed_types: set[str] | None = None,
        property_keys: dict[str, tuple[str, ...]] | None = None,
    ) -> Iterator[OntologyObject]:
        sql, params = self._compile(
            query,
            allowed_types=allowed_types,
            property_keys=property_keys or {},
        )
        cursor = self.repository._conn.execute(sql, params)  # reference backend boundary
        for row in cursor:
            yield OntologyObject.model_validate_json(row["payload"])

    def _compile(
        self,
        query: "ObjectQuery",
        *,
        allowed_types: set[str] | None,
        property_keys: dict[str, tuple[str, ...]],
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if allowed_types:
            placeholders = ",".join("?" for _ in allowed_types)
            clauses.append(f"o.type IN ({placeholders})")
            params.extend(sorted(allowed_types))
        elif query.object_type:
            clauses.append("o.type = ?")
            params.append(query.object_type)

        for predicate in query.predicates:
            keys = property_keys.get(predicate.property, (predicate.property,))
            clause, values = self._property_clause(predicate, keys)
            clauses.append(clause)
            params.extend(values)

        for index, predicate in enumerate(query.relationships):
            clause, values = self._relationship_clause(predicate, index)
            clauses.append(clause)
            params.extend(values)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        order_sql, order_params = self._order_by(query.sort, property_keys)
        params.extend(order_params)
        return f"SELECT o.payload FROM objects o{where}{order_sql}", params

    @staticmethod
    def _json_path(property_name: str) -> str:
        escaped = property_name.replace('"', '\\"')
        return f'$.properties."{escaped}"'

    def _property_expression(self, keys: tuple[str, ...]) -> tuple[str, list[Any]]:
        """Return an exact-precedence CEPIO property expression.

        QueryEngine resolves an exact stored key before registry aliases. The CASE
        expression mirrors that rule, including explicit JSON null values: an explicit
        null is considered present and therefore stops alias fallback.
        """
        cases: list[str] = []
        params: list[Any] = []
        for key in keys:
            path = self._json_path(key)
            cases.append("WHEN json_type(o.payload, ?) IS NOT NULL THEN json_extract(o.payload, ?)")
            params.extend([path, path])
        return "CASE " + " ".join(cases) + " ELSE NULL END", params

    def _property_exists_clause(self, keys: tuple[str, ...], exists: bool) -> tuple[str, list[Any]]:
        checks: list[str] = []
        params: list[Any] = []
        for key in keys:
            checks.append("json_type(o.payload, ?) IS NOT NULL")
            params.append(self._json_path(key))
        joined = " OR ".join(checks) if checks else "0"
        return (f"({joined})" if exists else f"NOT ({joined})"), params

    def _property_clause(
        self,
        predicate: "PropertyPredicate",
        keys: tuple[str, ...],
    ) -> tuple[str, list[Any]]:
        field = predicate.property
        op = predicate.operator.value
        value = predicate.value

        if field in _BUILTIN_FIELDS:
            expression = f"o.{field}"
            expression_params: list[Any] = []
            if op == "exists":
                return ("1=1" if value is not False else "1=0"), []
        else:
            if op == "exists":
                return self._property_exists_clause(keys, value is not False)
            expression, expression_params = self._property_expression(keys)

        if op == "in":
            values = list(value or [])
            if not values:
                return "1=0", []
            placeholders = ",".join("?" for _ in values)
            return f"{expression} IN ({placeholders})", expression_params + values
        if op == "contains":
            return f"instr(CAST({expression} AS TEXT), CAST(? AS TEXT)) > 0", expression_params + [value]
        operators = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        if op not in operators:
            raise ValueError(f"Unsupported pushdown query operator: {op}")
        return f"{expression} {operators[op]} ?", expression_params + [value]

    def _relationship_clause(self, predicate: "RelationshipPredicate", index: int) -> tuple[str, list[Any]]:
        """Push down only constraints that are exact under all CEPIO aliases/subtypes.

        Relationship type and other-type matching are ontology-aware in QueryEngine.
        Exact SQL comparisons could false-negative an alias or subtype, so SQL only
        narrows by graph direction and stable object identity. QueryEngine performs the
        complete relationship semantic check afterward.
        """
        alias = f"r{index}"
        other = f"other{index}"
        if predicate.direction == "out":
            endpoint = f"{alias}.source_id = o.id"
            other_join = f"{other}.id = {alias}.target_id"
        else:
            endpoint = f"{alias}.target_id = o.id"
            other_join = f"{other}.id = {alias}.source_id"
        conditions = [endpoint]
        params: list[Any] = []
        if predicate.other_id:
            conditions.append(f"{other}.id = ?")
            params.append(predicate.other_id)
        joined = " AND ".join(conditions)
        return (
            f"EXISTS (SELECT 1 FROM relationships {alias} JOIN objects {other} ON {other_join} WHERE {joined})",
            params,
        )

    def _order_by(
        self,
        fields: list["SortField"],
        property_keys: dict[str, tuple[str, ...]],
    ) -> tuple[str, list[Any]]:
        parts: list[str] = []
        params: list[Any] = []
        for spec in fields:
            direction = "DESC" if spec.direction == "desc" else "ASC"
            if spec.field in _BUILTIN_FIELDS:
                expression = f"o.{spec.field}"
                parts.append(f"({expression} IS NULL) ASC")
                parts.append(f"{expression} {direction}")
                continue

            keys = property_keys.get(spec.field, (spec.field,))
            null_expression, null_params = self._property_expression(keys)
            sort_expression, sort_params = self._property_expression(keys)
            parts.append(f"({null_expression} IS NULL) ASC")
            parts.append(f"{sort_expression} {direction}")
            params.extend(null_params)
            params.extend(sort_params)

        parts.append("o.id ASC")
        return " ORDER BY " + ", ".join(parts), params


def sqlite_query_backend(repository: object) -> SQLiteObjectQueryBackend | None:
    # Import lazily to avoid repositories <-> query import cycles.
    from .repositories import SQLiteRepository

    return SQLiteObjectQueryBackend(repository) if isinstance(repository, SQLiteRepository) else None
