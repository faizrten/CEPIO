"""Provider-neutral evidence boundary for CEPIO Petrophysics v1.1.

Qualified Petrophysics reasoning consumes logical evidence packages. Providers
resolve those packages from source systems; reasoning and authority semantics do
not depend on the provider implementation.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from .bootstrap import build_runtime
from .formation_evaluation import FormationEvaluationAssuranceRuntime, Pet02ExecutionResult
from .petrophysics_v1 import PetrophysicsJourneyResult, PetrophysicsV1Runtime
from .runtime import CEPIORuntime


class EvidenceProviderCapabilityError(RuntimeError):
    """Raised when a provider cannot resolve the requested Petrophysics journey."""


@runtime_checkable
class PetrophysicsEvidenceProvider(Protocol):
    """Logical source boundary consumed by Petrophysics reasoning."""

    @property
    def provider_id(self) -> str: ...

    @property
    def supported_journeys(self) -> frozenset[str]: ...

    def resolve_pet02(self, *, well: str, interval: str) -> dict[str, Any]: ...

    def resolve_v1_portfolio(self) -> dict[str, Any]: ...


class SyntheticPetrophysicsEvidenceProvider:
    """Resolve the qualified public synthetic fixtures through the provider API."""

    def __init__(self, resource_root: str | Path) -> None:
        self.resource_root = Path(resource_root).resolve()

    @property
    def provider_id(self) -> str:
        return "cepio.synthetic.petrophysics-v1"

    @property
    def supported_journeys(self) -> frozenset[str]:
        return frozenset(f"PET-{number:02d}" for number in range(1, 9))

    def resolve_pet02(self, *, well: str, interval: str) -> dict[str, Any]:
        path = (
            self.resource_root
            / "generalization"
            / "benchmarks"
            / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
        )
        payload = _load_yaml_mapping(path)
        if payload.get("well") != well or payload.get("interval") != interval:
            raise EvidenceProviderCapabilityError(
                f"Synthetic PET-02 fixture does not contain {well}/{interval}."
            )
        return payload

    def resolve_v1_portfolio(self) -> dict[str, Any]:
        path = (
            self.resource_root
            / "generalization"
            / "benchmarks"
            / "subsurface-petrophysics-v1-portfolio.yaml"
        )
        return _load_yaml_mapping(path)


class PetrophysicsOperationalRuntime:
    """Execute qualified Petrophysics reasoning against a selected provider."""

    def __init__(
        self,
        provider: PetrophysicsEvidenceProvider,
        *,
        resource_root: str | Path,
    ) -> None:
        self.provider = provider
        self.resource_root = Path(resource_root).resolve()

    def execute(
        self,
        journey_id: str,
        *,
        runtime: CEPIORuntime | None = None,
        actor_id: str = "petrophysicist",
        actor_roles: set[str] | None = None,
        well: str = "A-17",
        interval: str = "Zone-B",
    ) -> Pet02ExecutionResult | PetrophysicsJourneyResult:
        journey_id = journey_id.upper()
        if journey_id not in self.provider.supported_journeys:
            raise EvidenceProviderCapabilityError(
                f"Provider {self.provider.provider_id} does not support {journey_id}."
            )
        roles = set(actor_roles or {"petrophysicist"})
        cepio_runtime = runtime or build_runtime(resource_root=self.resource_root)
        if journey_id == "PET-02":
            package = self.provider.resolve_pet02(well=well, interval=interval)
            return FormationEvaluationAssuranceRuntime(package).execute(
                well=well,
                interval=interval,
                cepio_runtime=cepio_runtime,
                actor_id=actor_id,
                actor_roles=roles,
            )
        portfolio = self.provider.resolve_v1_portfolio()
        return PetrophysicsV1Runtime(portfolio, resource_root=self.resource_root).execute(
            journey_id,
            runtime=cepio_runtime,
            actor_id=actor_id,
            actor_roles=roles,
        )

    def execute_supported(
        self,
        *,
        runtime: CEPIORuntime | None = None,
        actor_id: str = "petrophysicist",
        actor_roles: set[str] | None = None,
    ) -> dict[str, Pet02ExecutionResult | PetrophysicsJourneyResult]:
        cepio_runtime = runtime or build_runtime(resource_root=self.resource_root)
        return {
            journey_id: self.execute(
                journey_id,
                runtime=cepio_runtime,
                actor_id=actor_id,
                actor_roles=actor_roles,
            )
            for journey_id in sorted(self.provider.supported_journeys)
        }


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping at {path}")
    return deepcopy(payload)
