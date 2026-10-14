from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.modules import ModuleCatalogue, compare_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CEPIO ontology module contract compatibility")
    parser.add_argument("--manifest", default="ontology-modules.yaml")
    parser.add_argument("--baseline", default="ontology-contract-snapshot.json")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()
    root = Path(args.manifest).resolve().parent
    catalogue = ModuleCatalogue.load(args.manifest)
    current = catalogue.snapshot(root)
    baseline_path = Path(args.baseline)
    if args.write_baseline or not baseline_path.exists():
        baseline_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(f"Wrote {baseline_path}")
        return 0
    previous = json.loads(baseline_path.read_text())
    changes = compare_snapshots(previous, current)
    for item in changes["additive"]: print(f"ADD: {item}")
    for item in changes["breaking"]: print(f"BREAKING: {item}")
    return 1 if changes["breaking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
