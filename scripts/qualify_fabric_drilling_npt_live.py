#!/usr/bin/env python
"""Run the CEPIO Synthetic -> Fabric portability proof against a live Fabric SQL endpoint."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cepio.integrations.microsoft.fabric_live_proof import (
    load_reference_context,
    run_fabric_drilling_npt_live_proof,
)
from cepio.integrations.microsoft.fabric_sql import FabricSqlSettings, FabricSqlTableReader


DEFAULT_REFERENCE = Path("examples/fabric/drilling-npt/reference-context.json")
TABLES = (
    "cepio_drilling_npt_context",
    "cepio_drilling_activity_interval",
    "cepio_drilling_activity_classification",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run identical CEPIO Drilling NPT Industry IQ against the synthetic control "
            "and a live Microsoft Fabric SQL source."
        )
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="Synthetic semantic control JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--dataset-id",
        default=os.getenv("CEPIO_FABRIC_DATASET_ID"),
        help="Non-secret Fabric dataset/item label recorded in CEPIO provenance",
    )
    args = parser.parse_args()

    settings = FabricSqlSettings.from_env()
    reader = FabricSqlTableReader(settings, allowed_tables=TABLES)
    reference = load_reference_context(args.reference)
    result = run_fabric_drilling_npt_live_proof(
        reader,
        reference_context=reference,
        dataset_id=args.dataset_id,
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
