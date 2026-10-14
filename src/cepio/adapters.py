from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AdapterResult:
    system: str
    operation: str
    dry_run: bool = True
    accepted: bool = True
    payload: dict[str, Any] = field(default_factory=dict)


class EnterpriseAdapter(Protocol):
    system_name: str

    def read(self, external_id: str) -> dict[str, Any]: ...
    def write(self, operation: str, payload: dict[str, Any]) -> AdapterResult: ...


class DryRunAdapter:
    system_name = "generic"

    def read(self, external_id: str) -> dict[str, Any]:
        return {"external_id": external_id, "system": self.system_name, "status": "stub"}

    def write(self, operation: str, payload: dict[str, Any]) -> AdapterResult:
        return AdapterResult(system=self.system_name, operation=operation, dry_run=True, payload=payload)


class SAPS4HANAAdapter(DryRunAdapter):
    system_name = "sap_s4hana_eam"


class AVEVAPIAdapter(DryRunAdapter):
    system_name = "aveva_pi"


class OSDUAdapter(DryRunAdapter):
    system_name = "osdu"


class PrimaveraP6Adapter(DryRunAdapter):
    system_name = "primavera_p6"


class FabricOneLakeAdapter(DryRunAdapter):
    system_name = "fabric_onelake"
