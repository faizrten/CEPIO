from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.cross_customer_qualification import run_cross_customer_qualification


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "generalization/customers/drilling-contractor-cross-customer-v0.5.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEPIO deterministic cross-customer qualification")
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()

    pack_path = args.pack if args.pack.is_absolute() else ROOT / args.pack
    report = run_cross_customer_qualification(ROOT, pack_path)

    print(f"CEPIO Cross-Customer Qualification v{report['cross_customer_qualification_version']}")
    print(f"mode: {report['mode']}")
    print(f"archetype: {report['archetype_id']}")
    print(f"pack: {report['pack_id']}")
    print(f"customers: {report['customer_count']}")
    print(f"questions/customer: {report['question_count_per_customer']}")
    print(f"executions: {report['total_question_executions']}")
    print(f"semantic extensions: {report['semantic_extension_count']}")
    print(f"runtime coverage: {report['cross_customer_runtime_coverage_rate']:.1%}")
    print(f"status: {report['status']}")
    for customer in report["customers"]:
        print(
            f"{customer['customer_id']} {customer['status']} "
            f"{customer['status_counts']['PASS']}/{customer['question_count']} "
            f"semantic_extension={not customer['no_semantic_extension']} "
            f"evidence_gate={customer['operator_evidence_gate_pass']}"
        )

    if args.json_out:
        output_path = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
        output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.fail_on_gap and report["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
