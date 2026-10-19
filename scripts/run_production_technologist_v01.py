#!/usr/bin/env python3
"""Run CEPIO Production Technologist v0.1 synthetic qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.production_technology import run_production_technologist_v01


ROOT = Path(__file__).parents[1]
DEFAULT_BENCHMARK = ROOT / "generalization" / "benchmarks" / "production-technologist-p118-v0.1.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--journey", choices=["PROD-01", "PROD-02", "PROD-06"])
    parser.add_argument("--fail-on-non-answer", action="store_true")
    args = parser.parse_args()

    result = run_production_technologist_v01(args.benchmark, journey_id=args.journey)
    payload = result.model_dump(mode="json")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.fail_on_non_answer:
        if args.journey:
            return 0 if payload.get("status") == "ANSWERED" else 1
        return 0 if payload.get("blocked") == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
