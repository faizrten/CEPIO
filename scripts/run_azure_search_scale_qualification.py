#!/usr/bin/env python3
"""Live Azure AI Search scale qualification for CEPIO Phase 3.1.

This script is intentionally synthetic. It never uploads customer data.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
)

from cepio.azure_search import AzureSearchConfig, AzureSearchMemoryBackend
from cepio.memory import MemoryKind, MemoryProvenance, MemoryRecord, MemoryScope
from cepio.retrieval_contracts import RetrievalStep, RetrievalStrategy


TARGET_CAPABILITY = "industrial.reliability.condition-work-context"
DEFAULT_ENDPOINT = "https://cepio-search-dev-31d48.search.windows.net"
DEFAULT_INDEX = "cepio-memory-v1"


def _index(name: str) -> SearchIndex:
    strings = SearchFieldDataType.String
    collection = SearchFieldDataType.Collection(strings)
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="id", type=strings, key=True, filterable=True),
            SearchableField(name="summary", type=strings),
            SimpleField(name="tenant_id", type=strings, filterable=True),
            SimpleField(name="scope", type=strings, filterable=True),
            SimpleField(name="kind", type=strings, filterable=True),
            SearchField(name="capability_ids", type=collection, filterable=True),
            SearchField(name="tags", type=collection, searchable=True, filterable=True),
            SearchField(name="source_system", type=strings, searchable=True, filterable=True),
            SearchField(name="resource_type", type=strings, searchable=True, filterable=True),
            SimpleField(
                name="created_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="expires_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
            ),
            SimpleField(name="record_json", type=strings, retrievable=True),
        ],
    )


def _memory(
    memory_id: str,
    *,
    tenant_id: str | None,
    scope: MemoryScope,
    summary: str,
    capability_id: str,
    tags: set[str],
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind=MemoryKind.SEMANTIC,
        scope=scope,
        tenant_id=tenant_id,
        summary=summary,
        provenance=MemoryProvenance(source_kind="synthetic-scale-qualification"),
        capability_ids={capability_id},
        tags=tags,
    )


def _targets() -> list[MemoryRecord]:
    return [
        _memory(
            "target-global",
            tenant_id=None,
            scope=MemoryScope.GLOBAL,
            summary="compressor vibration condition evidence",
            capability_id=TARGET_CAPABILITY,
            tags={"compressor", "condition"},
        ),
        _memory(
            "target-tenant-a",
            tenant_id="tenant-a",
            scope=MemoryScope.TENANT,
            summary="compressor vibration maintenance work context",
            capability_id=TARGET_CAPABILITY,
            tags={"compressor", "maintenance"},
        ),
        _memory(
            "target-foreign",
            tenant_id="tenant-b",
            scope=MemoryScope.TENANT,
            summary="compressor vibration foreign tenant evidence",
            capability_id=TARGET_CAPABILITY,
            tags={"compressor", "condition"},
        ),
    ]


def _noise(start: int, stop: int) -> list[MemoryRecord]:
    return [
        _memory(
            f"noise-{index:07d}",
            tenant_id="tenant-a",
            scope=MemoryScope.TENANT,
            summary=f"synthetic unrelated inspection evidence {index}",
            capability_id="industrial.synthetic.noise",
            tags={"synthetic", "noise"},
        )
        for index in range(start, stop)
    ]


def _ensure_index(index_client: SearchIndexClient, *, index_name: str, reset: bool) -> None:
    if reset:
        try:
            index_client.delete_index(index_name)
        except ResourceNotFoundError:
            pass
    index_client.create_or_update_index(_index(index_name))


def _query(backend: AzureSearchMemoryBackend, *, corpus_size: int) -> dict[str, object]:
    step = RetrievalStep(
        id="azure-search-lexical",
        strategy=RetrievalStrategy.LEXICAL,
        query_text="compressor vibration",
        tenant_id="tenant-a",
        capability_ids={TARGET_CAPABILITY},
        limit=10,
        at=datetime.now(timezone.utc),
    )
    started = time.perf_counter()
    hits = backend.search(step)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    ids = [item.record.id for item in hits]
    if "target-global" not in ids or "target-tenant-a" not in ids:
        raise RuntimeError(f"target evidence missing at corpus size {corpus_size}: {ids}")
    if "target-foreign" in ids:
        raise RuntimeError("cross-tenant evidence leaked into Azure AI Search results")
    return {
        "corpus_size": corpus_size,
        "latency_ms": elapsed_ms,
        "hit_count": len(hits),
        "hit_ids": ids,
        "cross_tenant_leakage": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--sizes", nargs="+", type=int, default=[5_000, 50_000])
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--batch-delay-seconds", type=float, default=0.5)
    parser.add_argument("--max-corpus-size", type=int, default=50_000)
    parser.add_argument("--reset-index", action="store_true")
    parser.add_argument("--output", default="evidence/azure-search-scale-qualification.json")
    args = parser.parse_args()

    sizes = sorted(set(args.sizes))
    if not sizes or sizes[0] < 3 or sizes[-1] > args.max_corpus_size:
        raise ValueError("corpus sizes must be between 3 and the configured maximum")
    if args.batch_size < 1 or args.batch_size > 1000:
        raise ValueError("batch-size must be between 1 and 1000")
    if args.batch_delay_seconds < 0 or args.batch_delay_seconds > 10:
        raise ValueError("batch-delay-seconds must be between 0 and 10")

    started = time.perf_counter()
    report: dict[str, object] = {
        "status": "FAIL",
        "endpoint": args.endpoint,
        "index": args.index,
        "synthetic_only": True,
        "sizes_requested": sizes,
        "batch_size": args.batch_size,
        "batch_delay_seconds": args.batch_delay_seconds,
        "results": [],
        "uploaded_documents": 0,
        "upload_batches": 0,
        "upload_retries": 0,
    }
    backend: AzureSearchMemoryBackend | None = None
    try:
        config = AzureSearchConfig(endpoint=args.endpoint, index_name=args.index)
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        index_client = SearchIndexClient(config.endpoint, credential)
        _ensure_index(index_client, index_name=config.index_name, reset=args.reset_index)

        search_client = SearchClient(config.endpoint, config.index_name, credential)
        backend = AzureSearchMemoryBackend(search_client, config)
        backend.upload_many(_targets())
        report["uploaded_documents"] = 3
        report["upload_batches"] = 1
        uploaded_noise = 0
        for requested_size in sizes:
            target_noise = requested_size - 3
            while uploaded_noise < target_noise:
                stop = min(target_noise, uploaded_noise + args.batch_size)
                backend.upload_many(_noise(uploaded_noise, stop))
                uploaded_noise = stop
                report["uploaded_documents"] = uploaded_noise + 3
                report["upload_batches"] = int(report["upload_batches"]) + 1
                if uploaded_noise % 1_000 < args.batch_size:
                    print(
                        f"indexed {uploaded_noise + 3:,} / {sizes[-1]:,} synthetic records "
                        f"(retries={backend.total_upload_retries})",
                        flush=True,
                    )
                if uploaded_noise < target_noise and args.batch_delay_seconds:
                    time.sleep(args.batch_delay_seconds)
            report["results"].append(_query(backend, corpus_size=requested_size))
            print(f"retrieval validated at corpus size {requested_size:,}", flush=True)
        report["status"] = "PASS"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:400]
        print(f"qualification failed: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
    finally:
        if backend is not None:
            report["upload_retries"] = backend.total_upload_retries
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
