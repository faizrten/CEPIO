"""Deterministic lexical retrieval helpers, independent of challenge questions."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def tokens(value: Any) -> tuple[str, ...]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value))
    return tuple(
        str(int(token)) if token.isdigit() else token.lower()
        for token in re.findall(r"[A-Za-z]+|[0-9]+", text)
    )


def contains(sequence: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    return bool(phrase) and any(
        sequence[index : index + len(phrase)] == phrase
        for index in range(len(sequence) - len(phrase) + 1)
    )


def leaves(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [text for key, item in value.items() for text in [str(key), *leaves(item)]]
    if isinstance(value, (list, tuple, set)):
        return [text for item in value for text in leaves(item)]
    return [str(value)]


def search(
    objects: Iterable[Any], query: str, object_type: str | None, limit: int
) -> list[Any]:
    objects = list(objects)
    types = sorted({obj.type for obj in objects})
    if object_type and object_type not in types:
        raise ValueError(
            f"Unknown object type {object_type!r}; available types: {', '.join(types)}"
        )
    query_sequence = tokens(query)
    query_tokens = set(query_sequence)
    identifiers = {
        tokens(value)
        for obj in objects
        for value in [
            obj.id,
            *(
                item
                for key, item in obj.properties.items()
                if key.endswith("_id") and isinstance(item, str)
            ),
        ]
    }
    anchors = {
        phrase
        for phrase in identifiers
        if any(token.isdigit() for token in phrase) and contains(query_sequence, phrase)
    }
    anchors = {
        anchor
        for anchor in anchors
        if not any(anchor != other and contains(other, anchor) for other in anchors)
    }
    ranked = []
    for obj in objects:
        if object_type and obj.type != object_type:
            continue
        properties = {
            key: value
            for key, value in obj.properties.items()
            if key not in {"source_uri", "geospatial_source_uri"}
        }
        fields = [
            tokens(value)
            for value in [obj.id, obj.name, obj.type, *leaves(properties)]
        ]
        if anchors and not all(
            any(contains(field, anchor) for field in fields) for anchor in anchors
        ):
            continue
        haystack = {token for field in fields for token in field}
        identity = set(tokens(obj.id)) | set(tokens(obj.name))
        overlap = query_tokens & haystack
        if query_tokens and not overlap:
            continue
        exact_identity = any(query_sequence == tokens(value) for value in (obj.id, obj.name))
        complete = query_tokens <= haystack
        score = len(overlap) + 2 * len(query_tokens & identity)
        ranked.append((not exact_identity, not complete, -score, obj.id, obj))
    ranked.sort(key=lambda entry: entry[:-1])
    return [entry[-1] for entry in ranked[: max(1, min(int(limit), 50))]]


def resolve(objects: Iterable[Any], alias: str) -> Any | None:
    objects = list(objects)
    target = alias.strip().casefold()
    exact = []
    normalized = []
    for obj in objects:
        aliases = obj.properties.get("aliases", {})
        candidates = [
            obj.id,
            obj.properties.get("canonical_iri"),
            obj.properties.get("source_tag"),
        ]
        candidates.extend(
            aliases.values()
            if isinstance(aliases, dict)
            else aliases
            if isinstance(aliases, list)
            else []
        )
        if target in {str(value).strip().casefold() for value in candidates if value}:
            exact.append(obj)
        if tokens(alias) in {
            tokens(value) for value in [*candidates, obj.name] if value
        }:
            normalized.append(obj)
    matches = exact or normalized
    if len(matches) > 1:
        candidates = ", ".join(sorted(obj.id for obj in matches))
        raise ValueError(f"Ambiguous identity {alias!r}; candidates: {candidates}")
    return matches[0] if matches else None
