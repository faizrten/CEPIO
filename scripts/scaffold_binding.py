"""Generate a thin internal CEPIO platform-binding skeleton."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import yaml

from cepio.platform_bindings import BindingCapability, BindingMode, PlatformBindingManifest


FILES = ("binding.yaml", "binding.py", "README.md")


def class_name(binding_id: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", binding_id) if part]
    if not parts:
        raise ValueError("binding_id must contain at least one alphanumeric character")
    result = "".join(part[:1].upper() + part[1:] for part in parts)
    return f"Binding{result}" if result[0].isdigit() else result


def default_capabilities(mode: BindingMode) -> frozenset[BindingCapability]:
    if mode == BindingMode.evidence:
        return frozenset(
            {
                BindingCapability.resolve_evidence,
                BindingCapability.versioned_identity,
            }
        )
    return frozenset(
        {
            BindingCapability.governed_write,
            BindingCapability.verify,
            BindingCapability.reconcile,
        }
    )


def build_manifest(
    *,
    binding_id: str,
    provider_id: str,
    source_system: str,
    mode: BindingMode,
) -> PlatformBindingManifest:
    return PlatformBindingManifest(
        binding_id=binding_id,
        provider_id=provider_id,
        source_system=source_system,
        mode=mode,
        capabilities=default_capabilities(mode),
    )


def render_manifest(manifest: PlatformBindingManifest) -> str:
    payload = {
        "schema_version": manifest.schema_version,
        "binding_id": manifest.binding_id,
        "provider_id": manifest.provider_id,
        "source_system": manifest.source_system,
        "mode": manifest.mode.value,
        "capabilities": sorted(capability.value for capability in manifest.capabilities),
    }
    return yaml.safe_dump(payload, sort_keys=False)


def render_manifest_python(manifest: PlatformBindingManifest) -> str:
    capability_lines = "\n".join(
        f"            BindingCapability.{capability.name},"
        for capability in sorted(manifest.capabilities, key=lambda item: item.value)
    )
    return f"""PlatformBindingManifest(
    binding_id={manifest.binding_id!r},
    provider_id={manifest.provider_id!r},
    source_system={manifest.source_system!r},
    mode=BindingMode.{manifest.mode.name},
    capabilities=frozenset(
        {{
{capability_lines}
        }}
    ),
)"""


def render_python(manifest: PlatformBindingManifest) -> str:
    name = class_name(manifest.binding_id)
    manifest_block = render_manifest_python(manifest)

    if manifest.mode == BindingMode.evidence:
        return f'''"""Generated CEPIO evidence binding skeleton.

Keep provider transport/mapping here. Domain interpretation belongs in Industry IQ.
"""

from cepio.platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
)


MANIFEST = {manifest_block}


class {name}EvidenceBinding:
    manifest = MANIFEST

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        raise NotImplementedError(
            "Implement provider transport and return normalized evidence with "
            "ExternalRecordReference provenance"
        )
'''

    return f'''"""Generated CEPIO governed-action binding skeleton.

External side effects must remain behind the CEPIO Action Runtime.
"""

from cepio.adapters import (
    GovernedVerificationRequest,
    GovernedVerificationResult,
    GovernedWriteReceipt,
    GovernedWriteRequest,
)
from cepio.platform_bindings import BindingCapability, BindingMode, PlatformBindingManifest


MANIFEST = {manifest_block}


class {name}GovernedActionBinding:
    system_name = {manifest.source_system!r}
    manifest = MANIFEST

    def write_governed(self, request: GovernedWriteRequest) -> GovernedWriteReceipt:
        raise NotImplementedError("Implement source-authoritative write behind Action Runtime")

    def verify_write(
        self, request: GovernedVerificationRequest
    ) -> GovernedVerificationResult:
        raise NotImplementedError("Implement explicit source verification")

    def reconcile_write(
        self, request: GovernedVerificationRequest
    ) -> GovernedVerificationResult:
        raise NotImplementedError("Implement explicit source reconciliation")
'''


def render_readme(manifest: PlatformBindingManifest) -> str:
    return f"""# {manifest.binding_id}

Internal CEPIO **{manifest.mode.value}** platform-binding scaffold for
`{manifest.provider_id}` (`source_system={manifest.source_system}`).

## Boundary

- **CEPIO Core** owns identity, provenance, policy, decisions and governed action contracts.
- **Industry IQ** owns industrial reasoning, failure modes, decision patterns and Skills.
- **This binding** owns provider transport and translation into the existing CEPIO contract.

Do not copy provider schemas into Core. Do not put industrial reasoning in this binding.
Do not add a second write runtime. Evidence bindings must remain side-effect free; governed
writes must be invoked through CEPIO Action Runtime and explicitly verified/reconciled.

## Next steps

1. Implement provider transport/mapping in `binding.py`.
2. Preserve source record identity and version provenance.
3. Add provider-specific fixtures outside Core semantics.
4. Run CEPIO binding conformance tests and local preflight.
5. Document any provider limitation rather than silently no-oping an unsupported capability.
"""


def scaffold_binding(output: Path, manifest: PlatformBindingManifest) -> None:
    output = output.resolve()
    existing = [name for name in FILES if (output / name).exists()]
    if existing:
        names = ", ".join(existing)
        raise FileExistsError(f"Refusing to overwrite existing binding files: {names}")

    output.mkdir(parents=True, exist_ok=True)
    (output / "binding.yaml").write_text(render_manifest(manifest), encoding="utf-8")
    (output / "binding.py").write_text(render_python(manifest), encoding="utf-8")
    (output / "README.md").write_text(render_readme(manifest), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding-id", required=True)
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--source-system", required=True)
    parser.add_argument("--mode", choices=[mode.value for mode in BindingMode], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = build_manifest(
        binding_id=args.binding_id,
        provider_id=args.provider_id,
        source_system=args.source_system,
        mode=BindingMode(args.mode),
    )
    scaffold_binding(args.output, manifest)
    print(f"Created {manifest.mode.value} binding scaffold at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
