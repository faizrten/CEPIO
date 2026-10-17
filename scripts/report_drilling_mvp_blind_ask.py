from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_benchmark_module():
    path = ROOT / "scripts/run_drilling_mvp_blind_ask.py"
    spec = importlib.util.spec_from_file_location("run_drilling_mvp_blind_ask", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load blind benchmark: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Print compact Ask CEPIO blind benchmark result")
    parser.add_argument("--output", type=Path, default=Path(".generated/drilling-v0.2-blind-ask"))
    parser.add_argument("--telemetry-points", type=int, default=600)
    parser.add_argument("--waveform-samples", type=int, default=512)
    parser.add_argument("--seed", type=int, default=1701)
    args = parser.parse_args()

    module = _load_benchmark_module()
    report = module.run_blind_benchmark(
        args.output,
        telemetry_points=args.telemetry_points,
        waveform_samples=args.waveform_samples,
        seed=args.seed,
    )
    failures = [detail["id"] for detail in report["details"] if not detail["passed"]]
    unresolved = [detail["id"] for detail in report["details"] if detail["intent"] == "unresolved"]
    print(
        "BLIND_ASK_SUMMARY "
        f"passed={report['passed']}/{report['total']} "
        f"accuracy={report['accuracy']:.6f} "
        f"evidence={report['evidence_coverage']:.6f} "
        f"unresolved={report['unresolved']} "
        f"failures={','.join(failures) if failures else 'none'} "
        f"unresolved_ids={','.join(unresolved) if unresolved else 'none'}"
    )
    if not report["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
