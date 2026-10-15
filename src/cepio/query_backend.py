from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .model import OntologyObject

if TYPE_CHECKING:
    from .query import ObjectQuery, PropertyPredicate, RelationshipPredicate, SortField
    from .repositories import SQLiteRepository


class SQLiteObjectQueryBackend:
    """SQL pushdown for current-state CEPIO object queries.

    The backend deliberately owns only source-neutral query execution. Actor visibility,
    property filtering, cursor validation, budgets and temporal fallbacks remain in the
    QueryEngine so security semantics are identical across repositories.
    """

    def __init__(self, repository: "SQLiteRepository") -> None:
        self.repository = repository

    def iter_candidates(
        self,
        query: "ObjectQuery",
        *,
        allowed_types: set[str] | None = None,
    ) -> Iterator[OntologyObject]:
        sql, params = self._compile(query, allowed_types=allowed_types)
        cursor = self.repository._conn.execute(sql, params)  # reference backend boundary
        for row in cursor:
            yield OntologyObject.model_validate_json(row["payload"])

    def _compile(self, query: "ObjectQuery", *, allowed_types: set[str] | None) -> tuple[str, list[Any]]:
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
            clause, values = self._property_clause(predicate)
            clauses.append(clause)
            params.extend(values)

        for index, predicate in enumerate(query.relationships):
            clause, values = self._relationship_clause(predicate, index)
            clauses.append(clause)
            params.extend(values)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        order_sql, order_params = self._order_by(query.sort)
        params.extend(order_params)
        return f"SELECT o.payload FROM objects o{where}{order_sql}", params

    @staticmethod
    def _json_path(property_name: str) -> str:
        escaped = property_name.replace('"', '\\"')
        return f'$.properties."{escaped}"'

    def _property_clause(self, predicate: "PropertyPredicate") -> tuple[str, list[Any]]:
        field = predicate.property
        if field in {"id", "type", "name", "version", "created_at", "updated_at"}:
            expression = f"o.{field}"
            path_params: list[Any] = []
        else:
            expression = "json_extract(o.payload, ?)"
            path_params = [self._json_path(field)]

        op = predicate.operator.value
        value = predicate.value
        if op == "exists":
            if field in {"id", "type", "name", "version", "created_at", "updated_at"}:
                return ("1=1" if value is not False else "1=0"), []
            expected = 0 if value is False else 1
            return "json_type(o.payload, ?) IS " + ("NULL" if expected == 0 else "NOT NULL"), path_params
        if op == "in":
            values = list(value or [])
            if not values:
                return "1=0", []
            placeholders = ",".join("?" for _ in values)
            return f"{expression} IN ({placeholders})", path_params + values
        if op == "contains":
            return f"instr(CAST({expression} AS TEXT), CAST(? AS TEXT)) > 0", path_params + [value]
        operators = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        if op not in operators:
            raise ValueError(f"Unsupported pushdown query operator: {op}")
        return f"{expression} {operators[op]} ?", path_params + [value]

    def _relationship_clause(self, predicate: "RelationshipPredicate", index: int) -> tuple[str, list[Any]]:
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
        if predicate.relationship_type:
            conditions.append(f"{alias}.type = ?")
            params.append(predicate.relationship_type)
        if predicate.other_id:
            conditions.append(f"{other}.id = ?")
            params.append(predicate.other_id)
        if predicate.other_type:
            conditions.append(f"{other}.type = ?")
            params.append(predicate.other_type)
        joined = " AND ".join(conditions)
        return (
            f"EXISTS (SELECT 1 FROM relationships {alias} JOIN objects {other} ON {other_join} WHERE {joined})",
            params,
        )

    def _order_by(self, fields: list["SortField"]) -> tuple[str, list[Any]]:
        parts: list[str] = []
        params: list[Any] = []
        for spec in fields:
            if spec.field in {"id", "type", "name", "version", "created_at", "updated_at"}:
                expression = f"o.{spec.field}"
            else:
                expression = "json_extract(o.payload, ?)"
                params.append(self._json_path(spec.field))
            direction = "DESC" if spec.direction == "desc" else "ASC"
            parts.append(f"({expression} IS NULL) ASC")
            parts.append(f"{expression} {direction}")
        parts.append("o.id ASC")
        return " ORDER BY " + ", ".join(parts), params


def sqlite_query_backend(repository: object) -> SQLiteObjectQueryBackend | None:
    # Import lazily to avoid repositories <-> query import cycles.
    from .repositories import SQLiteRepository

    return SQLiteObjectQueryBackend(repository) if isinstance(repository, SQLiteRepository) else None
