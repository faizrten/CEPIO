from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject
from cepio.query import ObjectQuery, PropertyPredicate, QueryOperator, SortField


def seed_current_objects(runtime, count: int) -> None:
    repository = runtime.object_repository
    connection = getattr(repository, "_conn", None)
    if connection is None:
        raise RuntimeError("Query load baseline requires the SQLite reference backend")

    rows = []
    for index in range(count):
        obj = OntologyObject(
            id=f"LOAD-{index:06d}",
            type="Compressor",
            name=f"Load Compressor {index}",
            properties={
                "criticality": "high" if index % 10 == 0 else "medium",
                "riskScore": float(count - index),
            },
            version=1,
        )
        rows.append(
            (
                obj.id,
                obj.type,
                obj.name,
                obj.model_dump_json(),
                obj.version,
                obj.created_at.isoformat(),
                obj.updated_at.isoformat(),
            )
        )

    connection.executemany(
        "INSERT INTO objects(id,type,name,payload,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        rows,
    )
    connection.commit()


def run_baseline(objects: int, max_ms: float) -> dict[str, float | int | bool]:
    with tempfile.TemporaryDirectory(prefix="cepio-query-baseline-") as directory:
        runtime = build_runtime(sqlite_path=Path(directory) / "baseline.db")
        seed_current_objects(runtime, objects)

        def forbidden_list(*args, **kwargs):
            raise AssertionError("Load baseline query fell back to runtime.list_objects()")

        runtime.list_objects = forbidden_list  # type: ignore[method-assign]
        query = ObjectQuery(
            object_type="Compressor",
            predicates=[
                PropertyPredicate(
                    property="criticality",
                    operator=QueryOperator.eq,
                    value="high",
                )
            ],
            sort=[SortField(field="riskScore", direction="desc")],
            limit=100,
            include_total=False,
        )

        started = time.perf_counter()
        result = runtime.query_objects(query)
        elapsed_ms = (time.perf_counter() - started) * 1000
        passed = elapsed_ms <= max_ms and len(result.items) == min(100, (objects + 9) // 10)
        return {
            "objects": objects,
            "matched_page": len(result.items),
            "elapsed_ms": round(elapsed_ms, 3),
            "max_ms": max_ms,
            "passed": passed,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="CEPIO SQLite typed-query load baseline")
    parser.add_argument("--objects", type=int, default=10000)
    parser.add_argument("--max-ms", type=float, default=5000.0)
    args = parser.parse_args()

    result = run_baseline(args.objects, args.max_ms)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
