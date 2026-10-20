#!/usr/bin/env python3
"""Deterministic canary for CEPIO capability-routed Retrieval & Indexing v0.1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from cepio.capability_registry import load_capability_registry
from cepio.memory import (
    ContextBudget,
    InMemoryMemoryStore,
    MemoryProvenance,
    MemoryRecord,
    MemoryReference,
    MemoryScope,
)
from cepio.retrieval import (
    CapabilityRouter,
    InMemoryLexicalIndex,
    LexicalIndexBackend,
    RegistryCapabilityGraph,
    RetrievalContextPipeline,
    RetrievalEngine,
    RetrievalIntent,
    RetrievalPlanner,
    RetrievalStatus,
    StructuredMemoryBackend,
)

TARGET_CAPABILITY = "industrial.reliability.condition-work-context"
NOW = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)


def _memory(
    memory_id: str,
    summary: str,
    *,
    capability_ids: set[str] | None = None,
    tags: set[str] | None = None,
    scope: MemoryScope = MemoryScope.GLOBAL,
    tenant_id: str | None = None,
    customer_specific: bool = False,
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        kind="SEMANTIC",
        scope=scope,
        tenant_id=tenant_id,
        summary=summary,
        provenance=MemoryProvenance(
            source_kind="synthetic-retrieval-canary",
            source_ids=[memory_id],
            customer_specific=customer_specific,
        ),
        reference=MemoryReference(
            source_system="SyntheticFabric",
            resource_type="work-order-context",
            resource_id=memory_id,
            observed_at=NOW,
        ),
        created_at=NOW,
        capability_ids=capability_ids or set(),
        tags=tags or set(),
    )


def run_reference(repo_root: Path) -> dict[str, object]:
    registry = load_capability_registry(
        repo_root / "generalization/capabilities/registry-v0.1.yaml"
    )
    if registry.get(TARGET_CAPABILITY) is None:
        raise RuntimeError(f"reference capability is missing: {TARGET_CAPABILITY}")

    store = InMemoryMemoryStore()
    index = InMemoryLexicalIndex()

    records = [
        _memory(
            "global-condition-work",
            "condition signal on equipment linked to work order readiness",
            capability_ids={TARGET_CAPABILITY},
            tags={"reliability", "work"},
        ),
        _memory(
            "tenant-a-condition-work",
            "pump vibration condition evidence linked to an active work order",
            capability_ids={TARGET_CAPABILITY},
            tags={"reliability", "vibration"},
            scope=MemoryScope.TENANT,
            tenant_id="tenant-a",
            customer_specific=True,
        ),
        _memory(
            "tenant-b-condition-work",
            "pump vibration condition evidence linked to another tenant work order",
            capability_ids={TARGET_CAPABILITY},
            tags={"reliability", "vibration"},
            scope=MemoryScope.TENANT,
            tenant_id="tenant-b",
            customer_specific=True,
        ),
    ]
    records.extend(
        _memory(
            f"noise-{index:03d}",
            "financial margin planning unrelated synthetic memory",
            tags={"finance", "noise"},
        )
        for index in range(500)
    )

    for record in records:
        store.put(record)
        index.upsert(record)

    engine = RetrievalEngine(
        CapabilityRouter(registry),
        RetrievalPlanner(RegistryCapabilityGraph(registry)),
        [StructuredMemoryBackend(store), LexicalIndexBackend(index)],
    )
    intent = RetrievalIntent(
        query_text="condition signal pump vibration work order",
        tenant_id="tenant-a",
        capability_hints={TARGET_CAPABILITY},
        required_capability_ids={TARGET_CAPABILITY},
        max_candidates=8,
        at=NOW,
    )
    result = RetrievalContextPipeline(engine).execute(
        intent,
        budget=ContextBudget(
            max_tokens=500,
            max_capabilities=5,
            max_semantic_nodes=50,
            max_evidence_items=10,
            max_episodes=5,
        ),
    )

    if result.status != RetrievalStatus.READY or result.context is None:
        raise RuntimeError("retrieval reference canary did not reach READY")

    candidate_ids = [item.record.id for item in result.retrieval.candidates]
    selected_ids = [item.record.id for item in result.context.selected]
    route_ids = [item.capability_id for item in result.retrieval.routing.routes]

    if not route_ids or route_ids[0] != TARGET_CAPABILITY:
        raise RuntimeError("capability router did not rank the target capability first")
    if "tenant-b-condition-work" in candidate_ids:
        raise RuntimeError("cross-tenant memory leaked into retrieval candidates")
    if "tenant-a-condition-work" not in candidate_ids:
        raise RuntimeError("tenant evidence was not retrieved")
    if "global-condition-work" not in candidate_ids:
        raise RuntimeError("global reusable evidence was not retrieved")
    if len(candidate_ids) > intent.max_candidates:
        raise RuntimeError("retrieval exceeded the configured candidate budget")

    return {
        "version": "0.1",
        "status": result.status.value,
        "target_capability": TARGET_CAPABILITY,
        "route_ids": route_ids,
        "candidate_ids": candidate_ids,
        "selected_context_ids": selected_ids,
        "corpus_size": len(index),
        "candidate_budget": intent.max_candidates,
        "context_usage": result.context.usage.model_dump(mode="json"),
        "retrieval_metrics": result.retrieval.metrics.model_dump(mode="json"),
        "warnings": result.retrieval.warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = run_reference(args.repo_root.resolve())
    payload = json.dumps(report, indent=2, sort_keys=True)
    print("CEPIO Retrieval & Indexing v0.1")
    print(payload)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
