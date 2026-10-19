from __future__ import annotations

from cepio.integrations.microsoft.drilling_npt_fabric import FabricDrillingNPTBinding
from cepio.integrations.synthetic.drilling_npt import SyntheticDrillingNPTBinding
from cepio.management_contract import BindingDescriptor
from cepio.platform_bindings import register_evidence_binding


class EmptyFabricReader:
    def read_rows(self, table_name: str, *, context_id: str) -> list[dict[str, object]]:
        return []


def test_synthetic_and_fabric_register_under_same_binding_contract():
    synthetic = register_evidence_binding(
        SyntheticDrillingNPTBinding({}),
        capability_id="drilling-npt-context",
    )
    fabric = register_evidence_binding(
        FabricDrillingNPTBinding(EmptyFabricReader()),
        capability_id="drilling-npt-context",
    )

    assert synthetic.contract_version == fabric.contract_version == "0.1"
    assert synthetic.capability_id == fabric.capability_id == "drilling-npt-context"
    assert synthetic.access_mode == fabric.access_mode == "read"
    assert synthetic.authority == fabric.authority == "observation-only"
    assert (
        synthetic.declared_capabilities
        == fabric.declared_capabilities
        == (
            "resolve-evidence",
            "versioned-identity",
        )
    )

    synthetic_descriptor = BindingDescriptor.from_registration(synthetic)
    fabric_descriptor = BindingDescriptor.from_registration(fabric)

    assert synthetic_descriptor.capability == fabric_descriptor.capability
    assert synthetic_descriptor.mode == fabric_descriptor.mode == "read"
    assert synthetic_descriptor.authority == fabric_descriptor.authority == "observation-only"
    assert synthetic_descriptor.provider == "synthetic"
    assert fabric_descriptor.provider == "microsoft-fabric"
