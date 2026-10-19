from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.petrophysics_v1 import PetrophysicsV1Runtime

ROOT = Path(__file__).parents[1]
DEFAULT_BENCHMARK = (
    ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-v1-portfolio.yaml"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO Petrophysics v1 persona coverage")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--journey", choices=[f"PET-0{i}" for i in range(1, 9)])
    parser.add_argument("--actor-id", default="petrophysicist")
    parser.add_argument("--actor-role", action="append", default=["petrophysicist"])
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()
    runtime = PetrophysicsV1Runtime.from_yaml(args.benchmark)
    roles = set(args.actor_role)
    if args.journey:
        result = runtime.execute(args.journey, actor_id=args.actor_id, actor_roles=roles)
        print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
        return 1 if args.fail_on_blocked and result.status != "ANSWERED" else 0
    coverage = runtime.execute_all(actor_id=args.actor_id, actor_roles=roles)
    print(json.dumps(coverage.model_dump(mode="json"), indent=2, sort_keys=True))
    return 1 if args.fail_on_blocked and not coverage.complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
