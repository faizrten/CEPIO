#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.production_technology_v02 import ProductionTechnologistV02Runtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO Production Technologist v0.2 coverage")
    parser.add_argument(
        "--benchmark",
        default="generalization/benchmarks/production-technologist-p118-v0.2.yaml",
    )
    parser.add_argument("--journey", choices=["PROD-01", "PROD-02", "PROD-03", "PROD-04", "PROD-05", "PROD-06"])
    parser.add_argument("--fail-on-non-answer", action="store_true")
    args = parser.parse_args()

    runtime = ProductionTechnologistV02Runtime.from_yaml(Path(args.benchmark))
    result = runtime.execute(args.journey) if args.journey else runtime.execute_all()
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))

    if args.fail_on_non_answer:
        if hasattr(result, "complete"):
            return 0 if result.complete else 1
        return 0 if result.status == "ANSWERED" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
