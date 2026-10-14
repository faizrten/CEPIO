from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.compatibility import check_repository_contract, write_report
from cepio.modules import ModuleCatalogue, compare_snapshots


def _legacy_snapshot_mode(args: argparse.Namespace) -> int:
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
    for item in changes["additive"]:
        print(f"ADD: {item}")
    for item in changes["breaking"]:
        print(f"BREAKING: {item}")
    return 1 if changes["breaking"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check CEPIO ontology contract compatibility and declared migrations"
    )
    parser.add_argument("--manifest", default="ontology-modules.yaml")
    parser.add_argument(
        "--baseline-config",
        default="compatibility/baseline.yaml",
        help="Pinned accepted CEPIO contract baseline",
    )
    parser.add_argument("--migrations-dir", default=None)
    parser.add_argument("--json-report", default=None)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    if args.baseline or args.write_baseline:
        if not args.baseline:
            parser.error("--write-baseline requires --baseline")
        return _legacy_snapshot_mode(args)

    repo_root = Path(args.manifest).resolve().parent
    report = check_repository_contract(
        repo_root,
        baseline_config_path=args.baseline_config,
        manifest_path=Path(args.manifest).name,
        migrations_dir=args.migrations_dir,
    )
    print(f"BASELINE: {report.baseline_label} ({report.baseline_ref})")
    for change in report.additive:
        print(f"ADD: {change.key} — {change.message}")
    for change in report.declared_breaking:
        print(f"DECLARED BREAKING: {change.key} — {change.message}")
    for change in report.undeclared_breaking:
        print(f"BREAKING: {change.key} — {change.message}")
    for item in report.stale_declarations:
        print(f"STALE MIGRATION: {item}")
    for item in report.errors:
        print(f"ERROR: {item}")

    if args.json_report:
        write_report(report, args.json_report)
        print(f"Wrote compatibility report: {args.json_report}")
    return 0 if report.compatible else 1


if __name__ == "__main__":
    raise SystemExit(main())
