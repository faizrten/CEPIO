#!/usr/bin/env python3
"""Run CEPIO Petrophysics through the v1.1 provider-neutral evidence boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cepio.integrations.microsoft.petrophysics_fabric import (
    FabricPetrophysicsEvidenceProvider,
    InMemoryFabricTableReader,
)
from cepio.petrophysics_evidence import (
    PetrophysicsOperationalRuntime,
    SyntheticPetrophysicsEvidenceProvider,
)


ROOT = Path(__file__).parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["synthetic", "fabric"], required=True)
    parser.add_argument("--journey", default="PET-02")
    parser.add_argument("--well", default="A-17")
    parser.add_argument("--interval", default="Zone-B")
    args = parser.parse_args()

    if args.provider == "synthetic":
        provider = SyntheticPetrophysicsEvidenceProvider(ROOT)
    else:
        fixture = (
            ROOT / "generalization" / "benchmarks" / "subsurface-petrophysics-v1-fabric-tables.yaml"
        )
        binding = (
            ROOT / "integrations" / "microsoft" / "fabric_iq" / "petrophysics-v1.evidence.yaml"
        )
        provider = FabricPetrophysicsEvidenceProvider(
            InMemoryFabricTableReader.from_yaml(fixture), binding
        )

    result = PetrophysicsOperationalRuntime(provider, resource_root=ROOT).execute(
        args.journey,
        well=args.well,
        interval=args.interval,
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0 if result.status == "ANSWERED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
