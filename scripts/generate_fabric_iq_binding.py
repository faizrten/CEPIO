from __future__ import annotations

import argparse
from pathlib import Path

from cepio.integrations.microsoft.fabric_iq import (
    FabricIQBindingGenerator,
    load_fabric_binding_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CEPIO -> Microsoft Fabric IQ ontology binding artifacts")
    parser.add_argument(
        "--modules",
        default="asset,work_management",
        help="Comma-separated CEPIO module ids; dependencies are included automatically",
    )
    parser.add_argument(
        "--bindings",
        default=str(ROOT / "integrations/microsoft/fabric_iq/asset-work.bindings.yaml"),
        help="Fabric source-binding profile YAML",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "build/fabric-iq/asset-work"),
        help="Output directory",
    )
    args = parser.parse_args()

    modules = [value.strip() for value in args.modules.split(",") if value.strip()]
    profile = load_fabric_binding_profile(args.bindings) if args.bindings else None
    manifest = FabricIQBindingGenerator(ROOT).write_bundle(
        args.output,
        modules,
        source_bindings=profile,
    )
    print(f"Wrote Fabric IQ ontology binding to {args.output}")
    print(f"Resolved modules: {', '.join(manifest.resolved_modules)}")
    print(f"Entity types: {len(manifest.entity_types)}")
    print(f"Relationship types: {len(manifest.relationship_types)}")
    print(f"Datatype properties: {len(manifest.datatype_properties)}")
    print(f"Canonical contract SHA256: {manifest.canonical_contract_sha256}")


if __name__ == "__main__":
    main()
