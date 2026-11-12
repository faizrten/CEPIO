"""Offline synthetic K-201 chart envelopes. No customer data, network or model calls.

Run: PYTHONPATH=src python examples/flint_k201_offline.py --out-dir /tmp/k201-charts
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from cepio.auth import ActorContext
from cepio.visualization_contract import (
    ChartSeries,
    EvidenceReference,
    NumericalObservation,
    build_readonly_visualization,
)


def make_examples() -> list[dict]:
    fixture = json.loads(Path(__file__).with_name("flint_k201_synthetic.json").read_text())
    tenant = fixture["tenant_id"]
    results = []
    for signal in fixture["signals"]:
        observations = []
        for index, (timestamp, value) in enumerate(
            zip(fixture["timestamps"], signal["values"], strict=True)
        ):
            evidence_blob = {
                "source_system": fixture["source_system"],
                "signal": signal["signal_id"],
                "observed_at": timestamp,
                "value": value,
                "version": fixture["record_version"],
            }
            digest = hashlib.sha256(
                json.dumps(evidence_blob, sort_keys=True).encode("utf-8")
            ).hexdigest()
            observations.append(
                NumericalObservation(
                    measured_at=datetime.fromisoformat(timestamp),
                    value=value,
                    evidence=EvidenceReference(
                        source_system=fixture["source_system"],
                        record_id=f"{signal['signal_id']}-row-{index}",
                        record_version=fixture["record_version"],
                        evidence_sha256=digest,
                    ),
                )
            )
        envelope = build_readonly_visualization(
            case_id=fixture["case_id"],
            tenant_id=tenant,
            series=ChartSeries(
                signal_id=signal["signal_id"],
                title=signal["title"],
                unit=signal["unit"],
                semantic_type=signal["semantic_type"],
                observations=observations,
            ),
            principal=lambda: ActorContext("offline-demo-actor", {"engineer"}, tenant),
            authorize=lambda actor, case, ref: (
                actor.tenant_id == tenant
                and case == fixture["case_id"]
                and ref.source_system == fixture["source_system"]
            ),
        )
        results.append(envelope.model_dump(mode="json"))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = make_examples()
    for envelope in results:
        name = envelope["signal_id"].replace(".", "-") + ".json"
        (args.out_dir / name).write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"Produced {len(results)} synthetic, read-only visualization envelopes")


if __name__ == "__main__":
    main()
