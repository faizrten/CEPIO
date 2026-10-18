#!/usr/bin/env python3
"""Execute the deterministic PET-02 Formation Evaluation Assurance reference journey."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio import run_pet02_formation_evaluation


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = (
    ROOT
    / "generalization"
    / "benchmarks"
    / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CEPIO PET-02 Formation Evaluation Assurance against a resolved benchmark."
    )
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--well", default="A-17")
    parser.add_argument("--interval", default="Zone-B")
    parser.add_argument(
        "--fail-on-non-answer",
        action="store_true",
        help="Return a non-zero exit code unless PET-02 produces ANSWERED.",
    )
    args = parser.parse_args()

    result = run_pet02_formation_evaluation(
        args.benchmark,
        well=args.well,
        interval=args.interval,
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    if args.fail_on_non_answer and result.status != "ANSWERED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
