from __future__ import annotations

from collections.abc import Mapping

from ...drilling_npt_binding import DrillingNPTContextEvidence
from ...platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
)


class SyntheticDrillingNPTBinding:
    """Deterministic control provider for drilling NPT CONNECT qualification."""

    manifest = PlatformBindingManifest(
        binding_id="cepio.binding.synthetic.drilling-npt",
        provider_id="synthetic",
        source_system="synthetic-drilling",
        mode=BindingMode.evidence,
        capabilities=frozenset(
            {
                BindingCapability.resolve_evidence,
                BindingCapability.versioned_identity,
            }
        ),
    )

    def __init__(self, contexts: Mapping[str, DrillingNPTContextEvidence]) -> None:
        self._contexts = dict(contexts)

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        try:
            context = self._contexts[external_id]
        except KeyError as exc:
            raise KeyError(f"Unknown synthetic drilling NPT context: {external_id}") from exc
        if context.context_id != external_id:
            raise ValueError("Synthetic drilling NPT context key does not match context_id")
        return EvidenceEnvelope(
            reference=context.context_reference,
            evidence=context.model_dump(mode="json"),
        )
