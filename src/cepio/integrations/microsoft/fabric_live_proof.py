"""Live Microsoft Fabric portability proof for Drilling NPT Industry IQ."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ...drilling_npt_binding import (
    DrillingNPTBindingQualification,
    DrillingNPTContextEvidence,
    qualify_drilling_npt_binding,
)
from ...platform_bindings import (
    BINDING_CONTRACT_VERSION,
    BindingRegistration,
    register_evidence_binding,
)
from ..synthetic.drilling_npt import SyntheticDrillingNPTBinding
from .drilling_npt_fabric import FabricDrillingNPTBinding, FabricDrillingNPTTableReader


class FabricLiveProofError(RuntimeError):
    """Raised when live Fabric evidence is not semantically equivalent to the control."""


class FabricDrillingNPTLiveProofResult(BaseModel):
    """Minimal proof evidence safe for CI summaries and management reporting."""

    model_config = ConfigDict(frozen=True)

    binding_contract_version: str
    binding_id: str
    provider_id: str
    capability_id: str
    context_id: str
    dataset_id: str | None = None
    semantic_signature: str
    total_npt_hours: float
    nonproductive_activity_ids: tuple[str, ...]
    evidence_reference_count: int
    synthetic_source_system: str
    fabric_source_system: str


def load_reference_context(path: Path) -> DrillingNPTContextEvidence:
    """Load the synthetic semantic control used for provider parity."""

    return DrillingNPTContextEvidence.model_validate_json(path.read_text(encoding="utf-8"))


def _assert_semantic_parity(
    synthetic: DrillingNPTBindingQualification,
    fabric: DrillingNPTBindingQualification,
) -> None:
    if synthetic.semantic_signature != fabric.semantic_signature:
        raise FabricLiveProofError(
            "Fabric evidence is not semantically equivalent to the synthetic control: "
            f"{fabric.semantic_signature} != {synthetic.semantic_signature}"
        )
    if synthetic.assessment != fabric.assessment:
        raise FabricLiveProofError(
            "Fabric Drilling NPT assessment differs from the synthetic control"
        )


def run_fabric_drilling_npt_live_proof(
    reader: FabricDrillingNPTTableReader,
    *,
    reference_context: DrillingNPTContextEvidence,
    dataset_id: str | None = None,
) -> FabricDrillingNPTLiveProofResult:
    """Run identical Drilling NPT Industry IQ against Synthetic and live Fabric evidence."""

    synthetic_binding = SyntheticDrillingNPTBinding(
        {reference_context.context_id: reference_context}
    )
    fabric_binding = FabricDrillingNPTBinding(reader, dataset_id=dataset_id)
    registration: BindingRegistration = register_evidence_binding(
        fabric_binding,
        capability_id="drilling-npt-context",
    )

    synthetic = qualify_drilling_npt_binding(
        synthetic_binding,
        external_id=reference_context.context_id,
    )
    fabric = qualify_drilling_npt_binding(
        fabric_binding,
        external_id=reference_context.context_id,
    )
    _assert_semantic_parity(synthetic, fabric)

    return FabricDrillingNPTLiveProofResult(
        binding_contract_version=BINDING_CONTRACT_VERSION,
        binding_id=registration.manifest.binding_id,
        provider_id=registration.manifest.provider_id,
        capability_id=registration.capability_id,
        context_id=reference_context.context_id,
        dataset_id=dataset_id,
        semantic_signature=fabric.semantic_signature,
        total_npt_hours=fabric.assessment.total_npt_hours,
        nonproductive_activity_ids=tuple(fabric.assessment.nonproductive_activity_ids),
        evidence_reference_count=len(fabric.evidence_references),
        synthetic_source_system=synthetic.source_system,
        fabric_source_system=fabric.source_system,
    )
