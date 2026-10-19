from __future__ import annotations

from pathlib import Path
from runpy import run_path

import pytest
import yaml

from cepio.platform_bindings import BindingCapability, BindingMode, PlatformBindingManifest


SCAFFOLD = run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "scaffold_binding.py"))
build_manifest = SCAFFOLD["build_manifest"]
class_name = SCAFFOLD["class_name"]
default_capabilities = SCAFFOLD["default_capabilities"]
render_manifest = SCAFFOLD["render_manifest"]
render_manifest_python = SCAFFOLD["render_manifest_python"]
render_python = SCAFFOLD["render_python"]
render_readme = SCAFFOLD["render_readme"]
scaffold_binding = SCAFFOLD["scaffold_binding"]


def test_class_name_normalizes_binding_identity():
    assert class_name("fabric-observation") == "FabricObservation"
    assert class_name("123-source") == "Binding123Source"
    with pytest.raises(ValueError, match="alphanumeric"):
        class_name("---")


def test_default_capabilities_are_mode_specific():
    assert default_capabilities(BindingMode.evidence) == frozenset(
        {BindingCapability.resolve_evidence, BindingCapability.versioned_identity}
    )
    assert default_capabilities(BindingMode.governed_action) == frozenset(
        {
            BindingCapability.governed_write,
            BindingCapability.verify,
            BindingCapability.reconcile,
        }
    )


def test_evidence_scaffold_is_source_neutral_and_side_effect_free(tmp_path):
    manifest = build_manifest(
        binding_id="fabric-observation",
        provider_id="microsoft.fabric",
        source_system="fabric",
        mode=BindingMode.evidence,
    )
    output = tmp_path / "fabric-observation"

    scaffold_binding(output, manifest)

    generated = (output / "binding.py").read_text(encoding="utf-8")
    compile(generated, str(output / "binding.py"), "exec")
    assert "resolve_evidence" in generated
    assert "write_governed" not in generated
    assert "IndustryIQ" not in generated

    payload = yaml.safe_load((output / "binding.yaml").read_text(encoding="utf-8"))
    parsed = PlatformBindingManifest.model_validate(payload)
    assert parsed == manifest
    assert parsed.mode == BindingMode.evidence
    assert "microsoft.fabric" in render_manifest(manifest)
    assert "BindingCapability.resolve_evidence" in render_manifest_python(manifest)
    assert "CEPIO Core" in render_readme(manifest)
    assert "EvidenceBinding" in render_python(manifest)


def test_governed_action_scaffold_reuses_cepio_write_contract(tmp_path):
    manifest = build_manifest(
        binding_id="sap-work-management",
        provider_id="sap.s4hana",
        source_system="sap_s4hana_eam",
        mode=BindingMode.governed_action,
    )
    output = tmp_path / "sap-work-management"

    scaffold_binding(output, manifest)

    generated = (output / "binding.py").read_text(encoding="utf-8")
    compile(generated, str(output / "binding.py"), "exec")
    assert "GovernedWriteRequest" in generated
    assert "verify_write" in generated
    assert "reconcile_write" in generated
    assert "Action Runtime" in generated
    assert "IndustryIQ" not in generated
    assert "GovernedActionBinding" in render_python(manifest)


def test_scaffold_refuses_to_overwrite_existing_binding(tmp_path):
    manifest = build_manifest(
        binding_id="cognite-evidence",
        provider_id="cognite.cdf",
        source_system="cognite",
        mode=BindingMode.evidence,
    )
    output = tmp_path / "cognite-evidence"
    scaffold_binding(output, manifest)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        scaffold_binding(output, manifest)
