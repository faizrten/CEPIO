"""Reference structured and lexical retrieval backends."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from pydantic import BaseModel

from .capability_routing import tokens
from .memory import MemoryQuery, MemoryRecord, MemoryStore
from .retrieval_contracts import (
    BackendHit,
    MemorySearchIndex,
    RetrievalStep,
    RetrievalStrategy,
)


class StructuredMemoryBackend:
    strategy = RetrievalStrategy.STRUCTURED

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def search(self, step: RetrievalStep) -> list[BackendHit]:
        records = self.store.query(
            MemoryQuery(
                tenant_id=step.tenant_id,
                kinds=step.kinds,
                capability_ids=step.capability_ids,
                tags=step.tags,
                limit=step.limit,
                at=step.at,
            )
        )
        return [
            BackendHit(
                record=record,
                strategy=self.strategy,
                score=1.0,
                rank=index,
                reasons=["structured memory query"],
            )
            for index, record in enumerate(records, start=1)
        ]


class LexicalIndexDocument(BaseModel):
    record: MemoryRecord
    term_frequency: dict[str, int]


class InMemoryLexicalIndex(MemorySearchIndex):
    """Rebuildable reference index; authoritative state remains in MemoryStore."""

    def __init__(self) -> None:
        self._documents: dict[str, LexicalIndexDocument] = {}
        self._postings: dict[str, set[str]] = defaultdict(set)

    @staticmethod
    def _document_terms(record: MemoryRecord) -> Counter[str]:
        values = [
            record.summary,
            *record.tags,
            record.reference.source_system if record.reference else "",
            record.reference.resource_type if record.reference else "",
        ]
        counter: Counter[str] = Counter()
        for value in values:
            counter.update(tokens(value))
        return counter

    def upsert(self, record: MemoryRecord) -> None:
        self.remove(record.id)
        term_frequency = dict(self._document_terms(record))
        document = LexicalIndexDocument(
            record=record.model_copy(deep=True),
            term_frequency=term_frequency,
        )
        self._documents[record.id] = document
        for term in term_frequency:
            self._postings[term].add(record.id)

    def remove(self, memory_id: str) -> bool:
        existing = self._documents.pop(memory_id, None)
        if existing is None:
            return False
        for term in existing.term_frequency:
            posting = self._postings.get(term)
            if posting is None:
                continue
            posting.discard(memory_id)
            if not posting:
                del self._postings[term]
        return True

    def __len__(self) -> int:
        return len(self._documents)

    def search(self, step: RetrievalStep) -> list[BackendHit]:
        query_terms = tokens(step.query_text)
        if not query_terms:
            return []
        candidate_ids: set[str] = set()
        for term in query_terms:
            candidate_ids.update(self._postings.get(term, set()))

        scored: list[tuple[float, str, MemoryRecord, list[str]]] = []
        for memory_id in candidate_ids:
            document = self._documents[memory_id]
            record = document.record
            if not record.visible_to(step.tenant_id) or record.expired_at(step.at):
                continue
            if step.kinds and record.kind not in step.kinds:
                continue
            if step.tags and record.tags.isdisjoint(step.tags):
                continue
            if step.capability_ids and record.capability_ids.isdisjoint(step.capability_ids):
                continue

            matched = query_terms & document.term_frequency.keys()
            if not matched:
                continue
            coverage = len(matched) / len(query_terms)
            frequency = sum(document.term_frequency[item] for item in matched)
            saturation = 1.0 - math.exp(-frequency / max(1, len(matched)))
            score = min(1.0, 0.8 * coverage + 0.2 * saturation)
            scored.append(
                (
                    score,
                    memory_id,
                    record.model_copy(deep=True),
                    ["lexical match: " + ", ".join(sorted(matched))],
                )
            )

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [
            BackendHit(
                record=record,
                strategy=RetrievalStrategy.LEXICAL,
                score=round(score, 6),
                rank=rank,
                reasons=reasons,
            )
            for rank, (score, _memory_id, record, reasons) in enumerate(
                scored[: step.limit], start=1
            )
        ]


class LexicalIndexBackend:
    strategy = RetrievalStrategy.LEXICAL

    def __init__(self, index: MemorySearchIndex) -> None:
        self.index = index

    def search(self, step: RetrievalStep) -> list[BackendHit]:
        return self.index.search(step)
